import argparse,hashlib,importlib.machinery,importlib.util,json,os,re,subprocess,sys,tomllib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument("phase",choices=["preflight","apply","reselect","preserve"]);p.add_argument("--host",required=True);p.add_argument("--root",required=True,type=Path);a=p.parse_args()
l=importlib.machinery.SourceFileLoader("ops",str(a.root/"scripts/tmux-observer-operations"));s=importlib.util.spec_from_loader(l.name,l);ops=importlib.util.module_from_spec(s);l.exec_module(ops)
home=Path.home();env=ops.environment();stem=Path("/tmp/tmux-fleet-fp4-"+a.host)
roots=[".local/share/tmux-observer/python",".local/share/rofi/extensions/tmux-plus"]
targets=[str(home/x) for x in roots+ops.control_paths(a.host)]
def execute(args,log=None,timeout=180):
 r=ops.run(args,env=env,check=False,timeout=timeout)
 if log:Path(log).write_text(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError("failed "+str(args[:5])+": "+r.stderr[-1200:])
 return r.stdout
def native():
 def tmux(*args):return execute(["/usr/bin/tmux","-L","default",*args])
 identity=tmux("display-message","-p","#{start_time}|#{pid}|#{socket_path}").strip()
 rows=sorted(tmux("list-sessions","-F","#{session_id}|#{session_created}").splitlines())
 sha=lambda text:hashlib.sha256(text.encode()).hexdigest()
 return {"generation":identity,"references":rows,"globalHooksSha256":sha(tmux("show-hooks","-g")),"sessionHooks":{r:sha(tmux("show-hooks","-t",r.split("|")[0])) for r in rows}}
def unrelated():
 paths=[".config/kitty/kitty.conf",".local/bin/rofi-agent-plus",".local/bin/rofi-agent-plus-rofi",".local/bin/agent-observer",".local/bin/agent-observer-client"]
 return {x:ops.node(home/x) for x in paths}
if a.phase=="preflight":
 baseline={"native":native(),"unrelatedControls":unrelated()};Path(str(stem)+"-preservation-before.json").write_text(json.dumps(baseline,indent=2)+"\n")
 text=execute(["chezmoi","--source",str(a.root),"execute-template","--file",str(a.root/".chezmoiexternal.toml")]);data=tomllib.loads(text);selection=json.loads(ops.TUPLE.read_text())
 for kind in ("core","frontend"):
  pick=selection[kind];v=data[pick["prefix"]];assert v["url"]==pick["url"] and v["checksum"]["sha256"]==pick["sha256"]
 for relative in (".config/niri/config.kdl",".config/niri/dms/binds.kdl"):
  desired=execute(["chezmoi","--source",str(a.root),"cat",str(home/relative)]).encode();assert desired==(home/relative).read_bytes(),"desktop configuration drift"
 execute(["chezmoi","--source",str(a.root),"diff",*targets],str(stem)+"-diff.log")
 execute(["chezmoi","--source",str(a.root),"--dry-run","apply","--verbose",*targets],str(stem)+"-dry-run.log")
 diff=Path(str(stem)+"-diff.log").read_text();dry=Path(str(stem)+"-dry-run.log").read_text();changed=re.findall(r"^diff --git a/(.*?) b/",dry,re.M)
 assert all(any(x==r or x.startswith(r+"/") for r in roots) or x in ops.control_paths(a.host) for x in changed)
 result={"phase":a.phase,"host":a.host,"result":"passed","renderedTuple":True,"niriControlsByteUnchanged":True,"scopedPaths":len(targets),"changedFileHeaders":len(changed),"diffSha256":hashlib.sha256(diff.encode()).hexdigest(),"dryRunSha256":hashlib.sha256(dry.encode()).hexdigest(),"selectionSha256":hashlib.sha256(ops.TUPLE.read_bytes()).hexdigest()}
elif a.phase in ("apply","reselect"):
 if a.phase=="reselect":
  baseline=json.loads(Path("/tmp/tmux-fleet-fp4-before-"+a.host+".json").read_text())
  for relative,value in baseline["controls"].items():assert ops.node(home/relative)==value,"rollback control drift: "+relative
  for saved in baseline["payloads"].values():
   for name,expected in saved["files"].items():
    path=home/saved["prefix"]/name;assert path.is_file() and not path.is_symlink();raw=path.read_bytes();assert len(raw)==expected["bytes"] and hashlib.sha256(raw).hexdigest()==expected["sha256"],"rollback payload drift"
 execute(["systemctl","--user","stop","tmux-observer-desktop.service",f"tmux-observer-owner@{a.host}.service"])
 execute(["chezmoi","--source",str(a.root),*( ["--force"] if a.phase=="reselect" else [] ),"apply","--verbose",*targets],str(stem)+"-"+a.phase+".log")
 execute(["systemctl","--user","daemon-reload"])
 execute(["systemctl","--user","start",f"tmux-observer-owner@{a.host}.service"])
 execute(["systemctl","--user","start","tmux-observer-desktop.service"])
 execute(["niri","validate","--config",str(home/".config/niri/config.kdl")],str(stem)+"-niri-validate.log")
 result={"phase":a.phase,"host":a.host,"result":"passed","scopedPaths":len(targets),"ownerStartedBeforeDesktop":True,"niriValidation":True,"selectionSha256":hashlib.sha256(ops.TUPLE.read_bytes()).hexdigest()}
else:
 before=json.loads(Path(str(stem)+"-preservation-before.json").read_text());after=native();b=before["native"]
 assert b["generation"]==after["generation"] and b["globalHooksSha256"]==after["globalHooksSha256"]
 assert set(b["references"])<=set(after["references"])
 assert all(after["sessionHooks"].get(k)==v for k,v in b["sessionHooks"].items())
 assert before["unrelatedControls"]==unrelated()
 result={"phase":a.phase,"host":a.host,"result":"passed","ordinaryReferencesPreserved":len(b["references"]),"currentReferences":len(after["references"]),"generationAndHooksPreserved":True,"unrelatedControlsPreserved":True,"foregroundInput":False}
Path(str(stem)+"-"+a.phase+".json").write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result))
