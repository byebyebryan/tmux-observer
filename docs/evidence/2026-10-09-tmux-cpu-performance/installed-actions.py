import json,sys,tempfile,hashlib,importlib.machinery,importlib.util,argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument("--host",required=True,choices=["snap","starship"]);a=p.parse_args()
root=Path("/tmp/tmux-cpu-cp4-managed-checkout")
def load(name,path):
 loader=importlib.machinery.SourceFileLoader(name,str(path));spec=importlib.util.spec_from_loader(loader.name,loader);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;loader.exec_module(m);return m
ops=load("ops",root/"scripts/tmux-observer-operations");live=load("live",root/"scripts/check-rofi-plus-live")
env=ops.environment();before=live._history_snapshot();events=[]
with tempfile.TemporaryDirectory(prefix="tmux-installed-actions-") as private:
 env.update(XDG_STATE_HOME=private+"/state",XDG_CACHE_HOME=private+"/cache")
 hosts,local,revision=live._check_mesh(str(Path.home()/".local/bin/rofi-ssh-plus"),env);assert set(hosts)=={"snap","starship"} and local==a.host
 gate=live.LifecycleGate(str(Path.home()/".local/bin/rofi-tmux-plus"),env,emit=lambda item:events.append(item));gate.run(hosts,revision)
live._assert_history_unchanged(before,live._history_path())
result={"schemaVersion":1,"endpoint":a.host,"result":"passed","selectionSha256":hashlib.sha256(ops.TUPLE.read_bytes()).hexdigest(),"harnessSha256":hashlib.sha256((root/"scripts/check-rofi-plus-live").read_bytes()).hexdigest(),"hosts":hosts,"checks":["create","duplicate collision","rename full reference","stale-name kill rejected","guarded kill","ordinary references preserved","owned fixture removed","SSH usage history unchanged"],"foregroundInput":False,"terminalLaunches":False,"events":events}
Path("/tmp/tmux-cpu-cp4-installed-actions-"+a.host+".json").write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result))
