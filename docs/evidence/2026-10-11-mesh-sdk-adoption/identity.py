import hashlib,json,os,socket,struct,subprocess,sys
from pathlib import Path
host,output=sys.argv[1:3];h=Path.home();unit='tmux-observer-owner@'+host+'.service';pid=int(subprocess.check_output(['systemctl','--user','show',unit,'-p','MainPID','--value']))
f=json.loads(subprocess.check_output([str(h/'.local/bin/tmux-observer'),'snapshot','--expected-host',host]));clock={'bootId':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'timeNamespace':os.readlink('/proc/self/ns/time').replace(':[',':').replace(']','')};assert f['clock']==clock
endpoint=Path('/run/user')/str(os.getuid())/'tmux-observer/owner.sock'
with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
 s.connect(str(endpoint));peer=struct.unpack('3i',s.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12));assert peer[:2]==(pid,os.getuid())
argv=Path(f'/proc/{pid}/cmdline').read_bytes().rstrip(b'\0').split(b'\0');assert argv[1:]==[os.fsencode(h/'.local/share/tmux-observer/bin/tmux-observer'),b'owner',b'--host-id',host.encode(),b'--local-attachments']
assert Path(f'/proc/{pid}/exe').resolve()==Path('/usr/bin/python3').resolve()
result={'state':'passed','host':host,'kernelPeerMatchesUnit':True,'uidMatches':True,'clockMatchesKernel':True,'exactOwnerCommand':True,'interpreter':'/usr/bin/python3','python':sys.version.split()[0],'currentOwnerPublisher':f['publisherId']}
Path(output).write_text(json.dumps(result,indent=2)+'\n');print('kernel identity accepted')
