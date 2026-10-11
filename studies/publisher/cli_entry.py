"""Copy the released CLI and apply only a proposed trusted Python injection hook.

The resulting module is an isolated research input, not an installed SDK change.
"""

import importlib.util
import re
import sys
import tempfile
from pathlib import Path

import mesh_plus.cli


def cli_candidate():
    original = Path(mesh_plus.cli.__file__).read_text()
    start = original.index("def configured_adapter(path, source):")
    end = original.index("\n\nasync def stdio_channel", start)
    factory = """def configured_adapter(path, source, *, publisher_factories=None):
    host, domain, socket = configured_descriptor(path, source)
    if publisher_factories is not None and domain in publisher_factories:
        from .api import descriptor
        from .protocol import check
        adapter = publisher_factories[domain](host, source, socket)
        check(adapter.host == host and adapter.source == source and
              adapter.profile == descriptor(domain).profile_id, "factory_binding")
        check(set(adapter.capabilities) <= {"snapshot", "proof", "subscribe"} and
              all(callable(getattr(adapter, name, None)) for name in
                  ("validate", "snapshot", "proof", "watch")), "factory_interface")
        return adapter
    from .observer import ObserverAdapter
    return ObserverAdapter(domain, host, source, socket)
"""
    changed = original[:start] + factory + original[end:]
    substitutions = {
        "async def run(args):": "async def run(args, *, publisher_factories=None):",
        "adapter = configured_adapter(args.config, args.source)": "adapter = configured_adapter(args.config, args.source, publisher_factories=publisher_factories)",
        "def main():": """def main(*, publisher_factories=None):
    if publisher_factories is not None:
        publisher_factories = dict(publisher_factories)
        if not set(publisher_factories) <= {"tmux", "agent"} or not all(
                callable(value) for value in publisher_factories.values()):
            raise ValueError("publisher_factory_mapping")""",
        "asyncio.run(run(args))": "asyncio.run(run(args, publisher_factories=publisher_factories))",
    }
    for before, after in substitutions.items():
        assert changed.count(before) == 1, before
        changed = changed.replace(before, after)
    return original, changed


def load_cli():
    original, changed = cli_candidate()
    with tempfile.TemporaryDirectory(prefix="tmux-publisher-cli-") as temporary:
        path = Path(temporary) / "candidate.py"
        path.write_text(changed)
        specification = importlib.util.spec_from_file_location(
            "mesh_plus._publisher_cli_study", path
        )
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)
    module.original_source = original
    module.candidate_source = changed
    return module


def main():
    # -I excludes ambient paths. This one explicit study path is caller-owned.
    sys.path.insert(0, str(Path(__file__).resolve().parent))

    class Fence:
        def find_spec(self, fullname, path=None, target=None):
            if re.match(
                r"^(mesh_plus\.observer|tmux_observer\.(collector|owner)|"
                r"tmux_observer_actions|tmux_observer_client)(\.|$)",
                fullname,
            ):
                raise ImportError("study publisher attempted a forbidden implementation import")

    sys.meta_path.insert(0, Fence())

    def make_tmux_publisher(host, source, socket):
        # Preserve the CLI's lightweight Host Mesh authority fast path.
        from native_source import make_tmux_publisher as factory

        return factory(host, source, socket)

    return load_cli().main(publisher_factories={"tmux": make_tmux_publisher})


if __name__ == "__main__":
    raise SystemExit(main())
