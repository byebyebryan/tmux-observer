"""Native cached-source admission and lifetime, independently of Mesh envelopes."""

import asyncio
import copy
import json
import os
import tempfile
import unittest
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch

import test_owner
from mesh_plus.api import CachedPublication

from tmux_observer._clock import boottime_ms, domain
from tmux_observer._mesh_source import NativeGuard, TmuxCachedSource
from tmux_observer.delivery import validate_service_frame
from tmux_observer.native import ValidationError, encode_document

ROOT = Path(__file__).resolve().parents[1]


def native(name="ready"):
    frame = json.loads((ROOT / f"contracts/service-v1/fixtures/{name}.json").read_text())
    shift = boottime_ms() - frame["encodedAt"] - 10
    timestamps = {
        "encodedAt",
        "startedAt",
        "finishedAt",
        "acceptedAt",
        "expiresAt",
        "lastAttemptAt",
    }

    def visit(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "clock":
                    value[key] = domain()
                elif key in timestamps and type(item) is int:
                    value[key] = item + shift
                else:
                    visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(frame)
    frame["source"]["uid"] = os.getuid()
    if frame["snapshot"] is not None:
        frame["snapshot"]["source"]["uid"] = os.getuid()
    validate_service_frame(frame)
    return frame


class GuardTests(unittest.TestCase):
    def test_native_scope_and_initial_request_admission(self):
        for field, code in (
            ("host", "native_host"),
            ("uid", "native_uid"),
            ("clock", "native_clock"),
            ("request", "native_request"),
            ("sequence", "native_initial_frame"),
            ("kind", "native_initial_frame"),
            ("gap", "native_gap_or_error"),
        ):
            frame = native()
            request = frame["requestId"]
            if field == "host":
                frame["source"]["hostId"] = frame["snapshot"]["source"]["hostId"] = "wrong"
                for row in frame["snapshot"]["sessions"]:
                    row["hostId"] = "wrong"
            elif field == "uid":
                frame["source"]["uid"] = frame["snapshot"]["source"]["uid"] = os.getuid() + 1
            elif field == "clock":
                frame["clock"]["timeNamespace"] = "time:999999999"
                frame["snapshot"]["clock"] = frame["clock"].copy()
            elif field == "request":
                frame["requestId"] = "wrong"
            elif field == "sequence":
                frame["sequence"] = 1
            else:
                frame["kind"] = "gap" if field == "gap" else "view"
            # Negative controls reach scope/order policy after pure admission.
            validate_service_frame(frame)
            with self.subTest(field=field), self.assertRaisesRegex(ValidationError, code):
                NativeGuard("fixture-local", request).accept(frame)

    def test_stream_receipt_order_and_failed_admission_atomicity(self):
        first = native()
        first["viewRevision"] = 2
        for field, code in (
            ("publisherId", "native_publisher_restart"),
            ("sequence", "native_stream_order"),
            ("viewRevision", "native_revision_regression"),
            ("encodedAt", "native_clock_regression"),
            ("accepted", "native_receipt_regression"),
            ("expiry", "native_lease_renewal"),
        ):
            guard = NativeGuard("fixture-local", first["requestId"])
            guard.accept(first)
            later = copy.deepcopy(first)
            later.update(sequence=1, requestId=None, kind="view")
            if field == "publisherId":
                later[field] = "99999999-9999-4999-8999-999999999999"
            elif field == "sequence":
                later[field] = 2
            elif field == "viewRevision":
                later[field] = 1
            elif field == "encodedAt":
                later[field] -= 1
                later["receipt"]["remainingMs"] += 1
            elif field == "accepted":
                later = native("warming")
                later.update(publisherId=first["publisherId"], sequence=1, viewRevision=2)
            else:
                later["encodedAt"] += 1
                for key in ("startedAt", "acceptedAt", "expiresAt", "lastAttemptAt"):
                    later["receipt"][key] += 1
                for key in ("startedAt", "finishedAt"):
                    later["snapshot"]["sample"][key] += 1
            validate_service_frame(later)
            with self.subTest(field=field), self.assertRaisesRegex(ValidationError, code):
                guard.accept(later)
            valid = copy.deepcopy(first)
            valid.update(sequence=1, requestId=None, kind="view")
            self.assertIs(guard.accept(valid), valid)


@asynccontextmanager
async def endpoint(handler):
    tasks = set()

    async def owned(reader, writer):
        task = asyncio.current_task()
        tasks.add(task)
        try:
            await handler(reader, writer)
        finally:
            writer.close()
            await writer.wait_closed()
            tasks.remove(task)

    with tempfile.TemporaryDirectory(prefix="tmux-cached-source-") as temporary:
        path = Path(temporary) / "owner.sock"
        server = await asyncio.start_unix_server(owned, path=path)
        path.chmod(0o600)
        try:
            yield path
        finally:
            server.close()
            await server.wait_closed()
            for task in list(tasks):
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)


class SourceTests(unittest.IsolatedAsyncioTestCase):
    async def test_cached_reads_and_watch_share_native_sample(self):
        with tempfile.TemporaryDirectory(prefix="tmux-source-owner-") as temporary:
            path = Path(temporary) / "owner.sock"
            owner, thread, collector = test_owner.OwnerTests().start(path)
            try:
                source = TmuxCachedSource("fixture-local", path)
                before = collector.calls
                for _ in range(5):
                    frame = await source.snapshot()
                    self.assertEqual(frame["receipt"]["accepted"], 1)
                watch = source.watch()
                publication = await anext(watch)
                self.assertIsInstance(publication, CachedPublication)
                self.assertEqual(publication.epoch, frame["publisherId"])
                self.assertEqual(publication.barrier, {"viewRevision": frame["viewRevision"]})
                await watch.aclose()
                self.assertEqual(collector.calls, before)
            finally:
                owner.stop()
                thread.join(3)
            self.assertFalse(thread.is_alive())

    async def test_watch_filters_heartbeat_without_losing_native_order(self):
        requests, closed = [], asyncio.Event()

        async def owner(reader, writer):
            request = json.loads(await reader.readline())
            requests.append(request)
            first = native()
            first["requestId"] = request["requestId"]
            first["kind"] = "resync"
            beat = {**first, "kind": "heartbeat", "sequence": 1, "requestId": None}
            view = {**first, "kind": "view", "sequence": 2, "requestId": None}
            writer.write(b"".join(encode_document(frame) for frame in (first, beat, view)))
            await writer.drain()
            await reader.read()
            closed.set()

        async with endpoint(owner) as path:
            watch = TmuxCachedSource("fixture-local", path).watch()
            first, second = await anext(watch), await anext(watch)
            self.assertEqual((first.frame["sequence"], second.frame["sequence"]), (0, 2))
            await watch.aclose()
            await asyncio.wait_for(closed.wait(), 1)
        self.assertEqual([r["operation"] for r in requests], ["watch"])
        self.assertTrue(
            all(
                set(r) == {"protocol", "schemaVersion", "operation", "requestId", "expectedHost"}
                for r in requests
            )
        )

    async def test_cancellation_after_admission_and_guard_failure_close_connection(self):
        for failure in ("cancel", "guard"):
            started, closed = asyncio.Event(), asyncio.Event()

            async def owner(reader, writer, failure=failure, started=started, closed=closed):
                if failure == "cancel":
                    await reader.readline()
                    started.set()
                await reader.read()
                closed.set()

            async with endpoint(owner) as path:
                source = TmuxCachedSource("fixture-local", path)
                if failure == "cancel":
                    task = asyncio.create_task(source.snapshot())
                    await started.wait()
                    task.cancel()
                    await asyncio.sleep(0)
                    task.cancel()
                    with self.assertRaises(asyncio.CancelledError):
                        await task
                else:
                    with (
                        patch(
                            "tmux_observer._mesh_source.NativeGuard",
                            side_effect=ValueError("clock unavailable"),
                        ),
                        self.assertRaisesRegex(ValueError, "clock unavailable"),
                    ):
                        await source.snapshot()
                await asyncio.wait_for(closed.wait(), 1)

    async def test_acquisition_cancellation_retires_late_admitted_channel(self):
        started, release = asyncio.Event(), asyncio.Event()

        class Channel:
            closes = 0

            async def close(self):
                self.closes += 1

        channel = Channel()

        async def connect(*_args, **_kwargs):
            started.set()
            await release.wait()
            return channel

        with patch("tmux_observer._mesh_source.connect_ipc", connect):
            task = asyncio.create_task(TmuxCachedSource("fixture-local", "/unused").snapshot())
            await started.wait()
            task.cancel()
            await asyncio.sleep(0)
            task.cancel()
            release.set()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertEqual(channel.closes, 1)

    async def test_started_frame_and_validation_completion_have_absolute_budget(self):
        for late in ("partial", "validation"):
            closed = asyncio.Event()

            async def owner(reader, writer, late=late, closed=closed):
                request = json.loads(await reader.readline())
                frame = native()
                frame["requestId"] = request["requestId"]
                writer.write(b"{" if late == "partial" else encode_document(frame))
                await writer.drain()
                await reader.read()
                closed.set()

            async with endpoint(owner) as path:
                source = TmuxCachedSource("fixture-local", path)
                if late == "partial":
                    with (
                        patch("tmux_observer._mesh_source.FRAME_MS", 25),
                        self.assertRaises(TimeoutError),
                    ):
                        await source.snapshot()
                else:
                    clock = [boottime_ms()]
                    original = NativeGuard.accept

                    def validate(guard, frame, original=original, clock=clock):
                        value = original(guard, frame)
                        clock[0] += 3000
                        return value

                    with (
                        patch(
                            "tmux_observer._mesh_source.boottime_ms", lambda clock=clock: clock[0]
                        ),
                        patch.object(NativeGuard, "accept", validate),
                        self.assertRaisesRegex(ValidationError, "native_frame_deadline"),
                    ):
                        await source.snapshot()
                await asyncio.wait_for(closed.wait(), 1)


if __name__ == "__main__":
    unittest.main()
