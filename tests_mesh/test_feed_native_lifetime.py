"""Actual disposable Tmux source with held feed output and sibling isolation."""

import asyncio
import gc
import unittest
from pathlib import Path

from mesh_plus.api import DeliveryError
from mesh_plus.transport import IPCServer, connect_ipc
from mesh_plus.view_feed import ViewFeedBridge, ViewFeedClient
from native_fixture import NativeFixture

from tmux_observer.mesh_profile import TmuxMeshProfile
from tmux_observer.mesh_publisher import make_publisher


class NativeFeedLifetimeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        previous_gc = gc.isenabled()
        gc.disable()
        self.addCleanup(lambda: gc.enable() if previous_gc else None)
        self.fixture = NativeFixture()
        self.addCleanup(self.fixture.close)
        self.fixture.native("local", "new-session", "-d", "-s", "held-output", "sleep 120")
        self.fixture.start_owner("local")
        self.profile = TmuxMeshProfile()
        self.path = Path(self.fixture.local) / "feed.sock"
        self.channels = []
        bridge = ViewFeedBridge(
            make_publisher("fixture-local", "tmux_default", self.fixture.local / "owner.sock"),
            profile=self.profile,
        )

        async def serve(channel):
            self.channels.append(channel)
            await bridge.serve(channel)

        self.server = await IPCServer(self.path, serve).start()
        self.addAsyncCleanup(self.server.close)

    async def client(self):
        client = await ViewFeedClient.connect(
            await connect_ipc(self.path),
            host="fixture-local",
            source="tmux_default",
            profile=self.profile,
        )
        self.addAsyncCleanup(client.close)
        return client

    async def data(self, subscription):
        while True:
            frame = await asyncio.wait_for(anext(subscription), 3)
            if frame["kind"] == "data":
                return frame

    async def test_native_borrow_survives_close_and_sibling_keeps_fresh_full_proofs(self):
        a, b = await self.client(), await self.client()
        sub = await a.subscribe()
        frame = await self.data(sub)
        rows = frame["payload"]["ownerFrame"]["snapshot"]["sessions"]
        self.assertEqual(rows[0]["name"], "held-output")
        await asyncio.gather(a.close(), a.close())
        self.assertGreater(a.budget.inspect()["heapBytes"], 0)
        self.assertEqual(rows[0]["sessionId"], "$0")
        for nonce in ("1" * 32, "2" * 32):
            proof = await b.request("proof", {"nonce": nonce})
            self.assertEqual(proof["nonce"], nonce)
            self.assertEqual(proof["ownerFrame"]["snapshot"]["sessions"], rows)
        del frame, rows, sub
        self.assertEqual(a.budget.inspect()["heapBytes"], 0)
        self.assertEqual(a.budget.inspect()["encodedBytes"], 0)
        self.assertFalse(b.closed)
        self.assertEqual(self.fixture.native("local", "list-clients"), b"")

    async def test_native_held_write_cleanup_keeps_credit_until_drain_unwinds(self):
        client = await self.client()
        channel = self.channels[0]
        original = channel.writer.drain
        entered, release = asyncio.Event(), asyncio.Event()
        calls = 0

        async def held_drain():
            nonlocal calls
            calls += 1
            if calls >= 2:
                entered.set()
                await release.wait()
            await original()

        channel.writer.drain = held_drain
        subscribe = asyncio.create_task(client.subscribe())
        closing = None
        try:
            await asyncio.wait_for(entered.wait(), 2)
            closing = asyncio.create_task(self.server.close())
            await asyncio.sleep(0.02)
            self.assertFalse(closing.done())
            self.assertGreater(channel.codec.budget.inspect()["encodedBytes"], 0)
            # Release within the unchanged two-second carrier deadline.
            release.set()
            await asyncio.wait_for(closing, 2)
            await asyncio.gather(subscribe, return_exceptions=True)
        finally:
            release.set()
            channel.writer.drain = original
            await client.close()
            if closing is not None:
                await closing
        self.assertEqual(channel.codec.budget.inspect()["heapBytes"], 0)
        self.assertEqual(channel.codec.budget.inspect()["encodedBytes"], 0)

    async def test_native_failed_write_and_repeated_cancel_preserve_other_client(self):
        a, b = await self.client(), await self.client()
        channel = self.channels[0]
        original = channel.writer.drain

        async def failed_drain():
            raise ConnectionResetError("owned failed output")

        channel.writer.drain = failed_drain
        try:
            with self.assertRaises(
                (EOFError, ConnectionError, ValueError, StopAsyncIteration, DeliveryError)
            ):
                failed = await a.subscribe()
                await asyncio.wait_for(anext(failed), 2)
        finally:
            channel.writer.drain = original
            await asyncio.gather(a.close(), a.close())
        sub = await b.subscribe()
        frame = await self.data(sub)
        del frame
        pending = asyncio.create_task(anext(sub))
        await asyncio.sleep(0)
        pending.cancel()
        pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)
        await asyncio.gather(sub.close(), sub.close())
        proof = await b.request("proof", {"nonce": "3" * 32})
        self.assertEqual(proof["ownerFrame"]["snapshot"]["sessions"][0]["name"], "held-output")
        self.assertEqual(self.fixture.native("local", "list-clients"), b"")
