import hashlib,json,subprocess,sys
from pathlib import Path
h=Path.home();s=h/'.local/share/chezmoi'
def sha(p):
 if p.is_symlink(): return {'link':str(p.readlink())}
 if not p.exists(): return None
 return {'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'mode':p.stat().st_mode&0o777}
def tree(root):
 rows={str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
 return {'files':len(rows),'sha256':hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()}
agent=json.loads((s/'deployments/agent-observer.json').read_text());mesh=json.loads((s/'deployments/agent-observer-mesh.json').read_text())
roots=[agent[k] for k in ('prefix','writerPrefix','readerPrefix')]+[mesh['bridgeSelection']['readerPrefix'],'.local/share/mesh-plus/0.1.0a10/python']
files=['.config/niri/config.kdl','.config/niri/dms/binds.kdl','.config/kitty/kitty.conf','.config/mesh-plus/sources.toml','.local/bin/mesh-plus','.config/systemd/user/agent-observer.service','.local/bin/agent-observer-write','.config/agent-observer/workspace.json']
foreign=['dot_config/kitty/kitty.conf','dot_config/niri/config.kdl.tmpl']
units={}
for unit in ('agent-observer.service','mesh-plus-agent.service'):
 pid=int(subprocess.check_output(['systemctl','--user','show',unit,'-p','MainPID','--value']).strip() or b'0')
 units[unit]={'pid':pid,'birth':Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19] if pid else None}
result={'controls':{p:sha(h/p) for p in files},'packages':{p:tree(h/p) for p in roots},'units':units,'foreignSource':{p:sha(s/p) for p in foreign},'agentSelections':{p:sha(s/'deployments'/p) for p in ('agent-observer.json','agent-observer-mesh.json')},'preferences':tree(h/'.local/state/rofi-tmux-plus'),'sshHistory':tree(h/'.local/state/rofi-ssh-plus')}
Path(sys.argv[1]).write_text(json.dumps(result,indent=2)+'\n')
print('preservation snapshot saved')
