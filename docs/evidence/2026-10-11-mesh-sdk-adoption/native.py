import hashlib,json,os,subprocess,sys
from pathlib import Path
host,output=sys.argv[1:3];env=dict(os.environ)
for k in ('TMUX','TMUX_PANE','TMUX_TMPDIR','PYTHONPATH','PYTHONHOME'):env.pop(k,None)
f=json.loads(subprocess.check_output([str(Path.home()/'.local/bin/tmux-observer'),'collect','--host-id',host],env=env));assert f['sample']['coverage']=='complete'
refs=sorted([r[k] for k in ('hostId','serverGeneration','sessionId','createdAt')] for r in f['sessions'])
hooks=subprocess.check_output(['/usr/bin/tmux','show-hooks','-g'],env=env)
attached=subprocess.check_output(['/usr/bin/tmux','list-sessions','-F','#{session_id}:#{session_created}:#{session_attached}'],env=env).decode().splitlines()
Path(output).write_text(json.dumps({'generation':f['serverGeneration'],'references':refs,'hooksSha256':hashlib.sha256(hooks).hexdigest(),'attachments':sorted(attached)},indent=2)+'\n')
print('native baseline saved',len(refs))
