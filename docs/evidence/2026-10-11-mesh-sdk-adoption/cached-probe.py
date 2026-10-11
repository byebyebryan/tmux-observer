import asyncio,json,os,sys,tempfile
from pathlib import Path
h=Path.home();selection=json.loads((h/'.local/share/chezmoi/deployments/tmux-observer.json').read_text())
roots=[selection['sharedMesh']['readerSdk']['prefix'],selection['core']['prefix']]+[x['prefix'] for x in selection['sharedMesh']['packages'] if x['name'] not in ('mesh-plus','tmux-reader-sdk')]
sys.path[:0]=[str(h/p) for p in roots]
from mesh_plus.api import Bridge,configured_reader,ReadGuard
from mesh_plus.transport import IPCServer,boottime_ms
from mesh_plus.library_authority import LibraryMeshAuthority
from tmux_observer.mesh import TmuxMeshAdapter,TmuxMeshProfile
import mesh_plus,tmux_observer
async def main(host):
 profile=TmuxMeshProfile();owner=Path(os.environ.get('XDG_RUNTIME_DIR','/run/user/'+str(os.getuid())))/'tmux-observer/owner.sock'
 with tempfile.TemporaryDirectory(prefix='tmux-sdk-cached-') as name:
  endpoint=Path(name)/'read.sock';adapter=TmuxMeshAdapter(host,owner);server=await IPCServer(endpoint,Bridge(adapter).serve,max_clients=2).start();stream=None
  try:
   reader=await configured_reader('tmux',source='tmux_default',socket=endpoint,scope='fleet',authority=LibraryMeshAuthority(),profile=profile)
   snap=await reader.snapshot();assert snap['mesh']['status']=='complete',snap['mesh']['status'];assert len(snap['mesh']['hosts'])==2
   guard=ReadGuard('tmux','b'*32,profile=profile);stream=reader.watch(request_id='b'*32,proof_interval=.1)
   for _ in range(30):
    frame=await asyncio.wait_for(anext(stream),5);guard.accept(frame)
    if len(guard.current(boottime_ms(),frame['mesh']['reader']['clock']))>=14:break
   rows=guard.current(boottime_ms(),frame['mesh']['reader']['clock']);assert len(rows)>=14
   guard.disconnect();await stream.aclose();stream=None;metrics=reader.inspect();assert metrics['activeConnections']==0 and metrics['cleanupFailures']==0
   result={'state':'passed','host':host,'readerSdk':mesh_plus.__version__,'observer':tmux_observer.__version__,'profile':'explicit TmuxMeshProfile','snapshotHosts':len(snap['mesh']['hosts']),'currentRows':len(rows),'snapshotAndWatch':True,'ownedRetirement':True,'limits':['Cached owner facts; no collection, refresh, action, graphical input or persistent service selected']}
  finally:
   if stream:await stream.aclose()
   await server.close()
  return result
Path(sys.argv[2]).write_text(json.dumps(asyncio.run(main(sys.argv[1])),indent=2)+'\n')
print('managed explicit-profile cached delivery passed')
