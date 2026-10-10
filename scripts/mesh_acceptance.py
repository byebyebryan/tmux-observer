"""Exact Mesh inputs and private bridge routing for installed acceptance tools."""

import hashlib
import json
from pathlib import Path


def stage_mesh(directory, source, evidence):
    """Check every frozen dependency against the reviewed tuple before copying."""
    tuple_path = (
        Path(__file__).resolve().parents[1] / "docs/evidence/2026-10-09-mesh-integration/tuple.json"
    )
    selected = json.loads(tuple_path.read_text())
    expected = [
        {"file": selected["mesh"]["wheel"], "sha256": selected["mesh"]["wheelSha256"]},
        *selected["runtimeDependencies"]["wheels"],
    ]
    assert {path.name for path in source.glob("*.whl")} == {row["file"] for row in expected}
    directory.mkdir(mode=0o700)
    for row in expected:
        raw = (source / row["file"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == row["sha256"], "Mesh input digest differs"
        (directory / row["file"]).write_bytes(raw)
    evidence["meshInputs"] = expected
    (directory / "manifest.json").write_text(json.dumps(expected) + "\n")


def mesh_wheels(directory):
    expected = json.loads((directory / "manifest.json").read_text())
    paths = [directory / row["file"] for row in expected]
    assert {path.name for path in directory.glob("*.whl")} == {path.name for path in paths}
    for row, path in zip(expected, paths, strict=True):
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
    return paths


def private_mesh_routes(root, python, *, socket, host, executable, sources=None):
    """Route only the fixture's bridge into its installed SDK and private config.

    The nonce/reached shell command and real SSH options remain unchanged.
    The trusted endpoint path is substituted in the locally owned SSH shim.
    """
    binary = root / "bin"
    binary.mkdir(mode=0o700, exist_ok=True)
    config = root / "mesh-sources.toml"
    if sources is None:
        sources = {"tmux_default": (host, socket)}
    # Each capacity host uses its own configured source, rather than routing a
    # wire host identity to an arbitrary socket.
    for source, (selected_host, selected_socket) in sources.items():
        path = config if len(sources) == 1 else root / (source + ".toml")
        path.write_text(
            "version = 1\nhost = "
            + json.dumps(selected_host)
            + "\n[sources."
            + source
            + ']\ndomain = "tmux"\nsocket = '
            + json.dumps(str(selected_socket))
            + "\n"
        )
        path.chmod(0o600)
    cli = Path(python).parent / "mesh-plus"
    wrapper = binary / "mesh-plus"
    wrapper.write_text(
        "#!"
        + str(python)
        + "\nimport os,sys,pathlib\n"
        + "root=pathlib.Path("
        + repr(str(root))
        + ")\n"
        + "args=sys.argv[1:]\n"
        + "if args and args[0]=='mesh':\n"
        + " with (root/'mesh-count').open('a') as out: out.write(args[1]+'\\n')\n"
        + "if args and args[0]=='bridge':\n"
        + " source=args[args.index('--source')+1]\n"
        + " (root/('bridge-pid-'+str(os.getpid()))).write_text(str(os.getpid()))\n"
        + " args+=['--config',str(root/'mesh-sources.toml') if source=='tmux_default' else str(root/(source+'.toml'))]\n"
        + "os.execv("
        + repr(str(cli))
        + ",['mesh-plus',*args])\n"
    )
    wrapper.chmod(0o700)
    ssh = binary / "mesh-ssh"
    ssh.write_text(
        "#!"
        + str(python)
        + "\nimport os,sys,shlex\n"
        + "args=sys.argv[1:]\n"
        + "last=shlex.split(args[-1])\n"
        + "with open("
        + repr(str(root / "mesh-ssh-starts"))
        + ", 'a') as out: out.write('start\\n')\n"
        + "if len(last)>=5 and last[-5:][:2]==['mesh-plus','bridge']:\n"
        + " last[-5]="
        + repr(str(wrapper))
        + "\n"
        + " args[-1]=shlex.join(last)\n"
        + "os.execvp("
        + repr(executable)
        + ",["
        + repr(executable)
        + ",*args])\n"
    )
    ssh.chmod(0o700)
    return ssh
