import subprocess,hashlib,json,argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument("--host",required=True);a=p.parse_args();root=Path.home()/".local/share/chezmoi"
def git(*args,check=True):
 r=subprocess.run(["git","-C",str(root),*args],capture_output=True,text=True,check=check);return r.stdout.strip()
before=git("rev-parse","HEAD");dirty=set(git("diff","--name-only").splitlines())|set(git("diff","--cached","--name-only").splitlines());hashes={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in dirty}
status=git("status","--short");git("fetch","origin");selected=git("rev-parse","origin/main");output=git("merge","--no-edit","origin/main")
assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==v for n,v in hashes.items()),"unrelated source edit changed"
git("merge-base","--is-ancestor",before,"HEAD");git("merge-base","--is-ancestor",selected,"HEAD")
result={"host":a.host,"result":"passed","previousHead":before,"publishedSelection":selected,"mergedHead":git("rev-parse","HEAD"),"divergence":git("rev-list","--left-right","--count","origin/main...HEAD"),"statusBefore":status,"statusAfter":git("status","--short"),"unrelatedTrackedEditHashes":hashes,"privateCommitsPreserved":True,"privateCommitsPushed":False}
Path("/tmp/tmux-fleet-fp4-source-merge-"+a.host+".json").write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result))
