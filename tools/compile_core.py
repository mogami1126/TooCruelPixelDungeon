from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import urllib.request, subprocess
root=Path(__file__).resolve().parent.parent
deps=root/'.research/build-deps'; deps.mkdir(exist_ok=True)
artifacts={
'gdx-1.10.0.jar':'com/badlogicgames/gdx/gdx/1.10.0/gdx-1.10.0.jar',
'gdx-freetype-1.10.0.jar':'com/badlogicgames/gdx/gdx-freetype/1.10.0/gdx-freetype-1.10.0.jar',
'json-20170516.jar':'org/json/json/20170516/json-20170516.jar'}
def fetch(entry):
 name,path=entry
 target=deps/name
 if not target.exists():
  with urllib.request.urlopen('https://repo.maven.apache.org/maven2/'+path,timeout=60) as r:
   target.write_bytes(r.read())
 return str(target)
with ThreadPoolExecutor(max_workers=3) as pool: jars=list(pool.map(fetch,artifacts.items()))
output=root/'.research/compiled-core'; output.mkdir(exist_ok=True)
sources=[]
for module in ['SPD-classes','services','core']:
 sources.extend((root/module/'src/main/java').rglob('*.java'))
args=['--release','8','-encoding','UTF-8','-classpath',';'.join(jars),'-d',str(output)]
args.extend(str(p) for p in sources)
argfile=deps/'javac.args'
argfile.write_text('\n'.join('"'+a.replace('\\','/')+'"' for a in args),encoding='utf-8')
r=subprocess.run(['javac','@'+str(argfile)],capture_output=True)
log=r.stdout+r.stderr
(output/'compile-output.txt').write_bytes(log)
print('Compiled source files:',len(sources),'exit code:',r.returncode)
print(log.decode('utf-8',errors='replace')[-6000:])
raise SystemExit(r.returncode)
