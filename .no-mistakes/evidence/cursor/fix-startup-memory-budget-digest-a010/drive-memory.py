import os, pathlib, subprocess, tempfile, shutil, json
root=pathlib.Path.cwd()
ev=pathlib.Path('/home/ubuntu/.no-mistakes/evidence/01M3MNM846RQWAW16QPXK4T5YA')
cases=[
 ('below-threshold','100\n',{'learnings.md':b'x'*266+b'\n'},None),
 ('exact-threshold','100\n',{'learnings.md':b'x'*269+b'\n'},90),
 ('over-budget','100\n',{'learnings.md':b'x'*362+b'\n'},121),
 ('no-final-newline','100\n',{'learnings.md':b'x'*363},121),
 ('aggregate-utf8','100\n',{'captain.md':('é'*44+'\n').encode(),'captain-shared.md':b's'*88+b'\n','learnings.md':b'l'*88+b'\n'},90),
 ('invalid-budget','0\n',{'learnings.md':b'x'*363},None),
 ('absent-memory','100\n',{},None),
]
results=[]
for name,budget,files,total in cases:
 home=pathlib.Path(tempfile.mkdtemp(prefix='.memory-live-',dir=root))
 try:
  for d in ('state','data','config','projects','user'): (home/d).mkdir()
  # Real lock refusal keeps the full public digest read-only, without mocking tools.
  (home/'state/.lock').mkdir()
  (home/'config/startup-memory-budget').write_text(budget)
  (home/'config/backlog-backend').write_text('manual\n')
  for f,b in files.items(): (home/'data'/f).write_bytes(b)
  env={k:v for k,v in os.environ.items() if not k.startswith('FM_') and k not in ('TMUX','TMUX_PANE','HERDR_SESSION','HERDR_SOCKET')}
  env.update(FM_HOME=str(home),HOME=str(home/'user'),FM_SESSION_START_TIMEOUT='40')
  p=subprocess.run(['bash','bin/fm-session-start.sh'],env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=55)
  out=p.stdout
  (ev/(name+'.txt')).write_text(out)
  hints=[s for s in out.splitlines() if s.startswith('STARTUP_MEMORY_BUDGET:')]
  assert p.returncode==0 and '●  STARTUP TRUNCATED' not in out, 'digest failed/truncated'
  assert 'data/learnings.md' in out, 'context missing'
  if total is None: assert not hints, hints
  else:
   expected=f'STARTUP_MEMORY_BUDGET: {total} of 100 estimated tokens ({total}%) - run /stow'
   assert hints==[expected], hints
   assert out.index(expected)>out.index('data/learnings.md'), 'wrong placement'
   assert '\n'+expected+'\n' in out, 'not on own line'
  results.append({'scenario':name,'result':'pass','warning':hints})
 except Exception as e:
  results.append({'scenario':name,'result':'fail','error':str(e)})
 finally: shutil.rmtree(home)
(ev/'results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
