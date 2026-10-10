"""One owned Mesh replacement stream behind a prepared desktop service."""

import asyncio
import collections
import json
import tempfile
import threading
import uuid
from pathlib import Path

from mesh_plus import __version__
from mesh_plus.bridge import Bridge
from mesh_plus.catalog import MeshAuthority
from mesh_plus.configured_read import configured_reader
from mesh_plus.transport import IPCServer
from mesh_plus.view import ReadGuard

from tmux_observer._ipc import owner_socket
from tmux_observer.mesh import TmuxMeshAdapter

QUEUE_LIMIT = 16 * 1048576


class CatalogCapacityError(ValueError):
    def __init__(self, catalog):
        self.catalog = catalog
        super().__init__("prepared fleet supports at most 16 owners")


class CapturedAuthority:
    """Keep the exact initial catalog used by Mesh's configured reader."""

    def __init__(self, authority):
        self.authority = authority
        self.catalog = None

    async def load(self):
        catalog = await self.authority.load()
        if self.catalog is None:
            self.catalog = catalog
        if len(catalog.hosts) > 16:
            raise CatalogCapacityError(catalog)
        return catalog

    async def report_route(self, **kwargs):
        return await self.authority.report_route(**kwargs)


class MeshWorker:
    def __init__(self, host_id, *, owner_path=None, source="tmux_default", authority=None):
        if __version__ not in {"0.1.0a4", "0.1.0a5", "0.1.0a6", "0.1.0a7"}:
            raise ValueError(
                "Mesh backend requires a reviewed mesh-plus 0.1.0a4/a5/a6/a7 candidate"
            )
        self.host_id = host_id
        self.owner_path = owner_socket() if owner_path is None else owner_path
        self.source = source
        self.owns_authority = authority is None
        if authority is None and __version__ in {"0.1.0a6", "0.1.0a7"}:
            from mesh_plus.library_authority import LibraryMeshAuthority

            authority = LibraryMeshAuthority()
        self.authority = MeshAuthority() if authority is None else authority
        self.lock = threading.Lock()
        self.events = collections.deque()
        self.bytes = 0
        self.loop = self.task = self.root_task = None
        self.stopping = threading.Event()
        self.thread = threading.Thread(target=self.run, name="tmux-mesh-reader")

    def put(self, event):
        size = (
            len(json.dumps(event[1], separators=(",", ":")).encode()) if event[0] == "view" else 0
        )
        with self.lock:
            if event[0] == "error":
                self.events.clear()
                self.bytes = 0
            if len(self.events) >= 8 or self.bytes + size > QUEUE_LIMIT:
                self.events.clear()
                self.bytes = 0
                self.events.append(("error", "capacity"))
                raise ValueError("Mesh handoff queue exceeded its bound")
            self.events.append(event)
            self.bytes += size

    def take(self):
        with self.lock:
            values = list(self.events)
            self.events.clear()
            self.bytes = 0
            return values

    async def watch(self, bridge_path):
        authority = CapturedAuthority(self.authority)
        reader = await configured_reader(
            "tmux",
            source=self.source,
            socket=bridge_path,
            authority=authority,
            report_routes=True,
        )
        catalog = authority.catalog
        if catalog.local_host != self.host_id:
            raise ValueError("Mesh catalog local host differs from configured Observer")
        request_id = uuid.uuid4().hex
        guard = ReadGuard("tmux", request_id, host_ids=[host["id"] for host in catalog.hosts])
        iterator = reader.watch(request_id=request_id)
        try:
            async for frame in iterator:
                guard.accept(frame)
                if "mesh" not in frame:
                    self.put(("error", frame["error"]["code"]))
                    return
                kind = frame["mesh"]["kind"]
                if kind == "gap":
                    self.put(("error", "source_gap"))
                elif kind != "heartbeat":
                    self.put(("view", frame, catalog))
        finally:
            guard.disconnect()
            await iterator.aclose()

    async def main(self):
        self.loop = asyncio.get_running_loop()
        self.root_task = asyncio.current_task()
        with tempfile.TemporaryDirectory(prefix="tmux-mesh-") as temporary:
            adapter = TmuxMeshAdapter(self.host_id, self.owner_path, self.source)
            bridge = Bridge(adapter)
            path = Path(temporary) / "bridge.sock"
            server = await IPCServer(path, bridge.serve, max_clients=1).start()
            try:
                delay = 0.25
                while not self.stopping.is_set():
                    self.task = asyncio.create_task(self.watch(path))
                    try:
                        await self.task
                    except CatalogCapacityError as error:
                        if error.catalog.local_host == self.host_id:
                            self.put(("capacity", error.catalog.revision))
                        else:
                            self.put(("error", "scope_mismatch"))
                    except asyncio.CancelledError:
                        if self.stopping.is_set():
                            return
                    except Exception:  # noqa: BLE001 - revoke the whole owned stream on SDK failure
                        self.put(("error", "mesh_unavailable"))
                    finally:
                        self.task = None
                    await asyncio.sleep(delay)
                    delay = min(30, delay * 2)
            finally:
                await server.close()

    def run(self):
        try:
            asyncio.run(self.main())
        except asyncio.CancelledError:
            pass
        except Exception:  # noqa: BLE001 - report owned worker failure to the fleet scheduler
            self.put(("error", "mesh_unavailable"))

    def start(self):
        self.thread.start()

    def restart(self):
        if self.loop is not None and self.loop.is_running():

            def cancel():
                if self.task is not None:
                    self.task.cancel()

            self.loop.call_soon_threadsafe(cancel)

    def close(self):
        self.stopping.set()
        if self.loop is not None and self.loop.is_running():
            # Cancel the root task too, including its bounded retry delay.
            def cancel_all():
                if self.root_task is not None:
                    self.root_task.cancel()

            self.loop.call_soon_threadsafe(cancel_all)
        self.thread.join(timeout=8)
        if self.thread.is_alive():
            raise RuntimeError("owned Mesh reader did not terminate")
        if self.owns_authority and hasattr(self.authority, "close"):
            self.authority.close()
