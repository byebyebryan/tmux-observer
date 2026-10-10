import json,subprocess,shlex,importlib.machinery,importlib.util,argparse,hashlib,sys,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument("--host",required=True,choices=["snap","starship"]);a=p.parse_args()
root=Path("/tmp/tmux-local-lp5-managed-checkout")
loader=importlib.machinery.SourceFileLoader("ops",str(root/"scripts/tmux-observer-operations"));spec=importlib.util.spec_from_loader(loader.name,loader);ops=importlib.util.module_from_spec(spec);loader.exec_module(ops)
env=ops.environment()
def native(host):
 args=["env","-u","TMUX","-u","TMUX_PANE","-u","TMUX_TMPDIR","/usr/bin/tmux","-L","default","display-message","-p","#{start_time}|#{pid}|#{socket_path}",";","list-sessions","-F","#{session_id}|#{session_created}"]
 if host!=a.host:args=["ssh","-o","BatchMode=yes","-o","ConnectTimeout=5",host,shlex.join(args)]
 text=ops.run(args,env=env).stdout;identity,_,rows=text.partition("\n");start,pid,path=identity.strip().split("|",2)
 return "tmux-v1:"+start+":"+pid+":"+path,{tuple(line.split("|")) for line in rows.splitlines()}
def refs(host):return {(x["sessionId"],str(x["createdAt"])) for x in host["sessions"]}
for attempt in range(5):
 frame=ops.fleet_ready(a.host,local_attachments=True,local_bindings=True)
 fresh=json.loads(ops.run([str(Path.home()/".local/bin/rofi-tmux-plus"),"inventory","--json"],env=env).stdout)
 cached={x["hostId"]:x for x in frame["snapshot"]["hosts"]};direct={x["hostId"]:x for x in fresh["hosts"]}
 assert set(cached)==set(direct)=={"snap","starship"}
 summary=[];good=True
 for host in ["snap","starship"]:
  generation,rows=native(host);c=cached[host];f=direct[host]
  good=good and refs(c)==refs(f)==rows and c["owner"]["serverGeneration"]==generation and all(x["serverGeneration"]==generation for x in f["sessions"])
  summary.append({"hostId":host,"nativeSessions":len(rows),"preparedSessions":len(c["sessions"]),"freshSessions":len(f["sessions"]),"fullReferencesAndGenerationMatch":refs(c)==refs(f)==rows and c["owner"]["serverGeneration"]==generation})
 if good:break
 time.sleep(1)
assert good,"native/fresh/prepared reference parity did not converge"
result={"schemaVersion":1,"result":"passed","endpoint":a.host,"selectionSha256":hashlib.sha256(ops.TUPLE.read_bytes()).hexdigest(),"readerId":frame["readerId"],"desktopState":frame["snapshot"]["desktop"]["state"],"hosts":summary,"foregroundInput":False,"nativeActions":False}
Path("/tmp/tmux-local-lp5-live-parity-"+a.host+".json").write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result))
