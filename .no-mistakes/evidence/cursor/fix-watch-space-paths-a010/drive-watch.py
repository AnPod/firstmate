import os,pathlib,subprocess,time,shutil
root=pathlib.Path.cwd(); area=root/'.t'; area.mkdir(exist_ok=True)
socket=area/'s'; evidence=pathlib.Path('/home/box/.no-mistakes/evidence/01M431BPET6MZQ04VFTVTW1SV1/live-watch.txt')
log=[]; children=[]
def run(args,env=None):
 p=subprocess.run(args,env=env,text=True,capture_output=True); log.append('$ '+' '.join(map(str,args))+'\n'+p.stdout+p.stderr); assert p.returncode==0,(args,p.stderr); return p.stdout
base=os.environ.copy()
for k in list(base):
 if k.startswith('FM_') or k in ('NO_MISTAKES_GATE','TMUX'):base.pop(k)
base['TMUX']=str(socket)+',0,0'
def wait(pred):
 deadline=time.time()+25
 while time.time()<deadline:
  if pred():return
  time.sleep(.15)
 raise AssertionError('timed out')
def watch(home):
 env=base|{'FM_HOME':str(home),'FM_POLL':'1','FM_SIGNAL_GRACE':'1','FM_CHECK_INTERVAL':'999999','FM_HEARTBEAT':'999999','FM_SECONDMATE_LIVENESS_SECS':'99999999'}
 f=open(home/'watch.out','w'); err=open(home/'watch.err','w')
 p=subprocess.Popen([str(root/'bin/fm-watch.sh')],env=env,stdout=f,stderr=err);children.append(p);return p,env
try:
 run(['tmux','-S',str(socket),'new-session','-d','-s','fm-lab-watch','-n','fm-task','sleep 180'])
 for name in ['plain-home','spaced home']:
  home=area/name;run([str(root/'bin/fm-lab-home.sh'),'create',str(home)])
  state=home/'state'; wt=home/'projects'/'task';wt.mkdir()
  (state/'task.meta').write_text(f'kind=ship\nharness=pi\nbackend=tmux\nwindow=fm-lab-watch:fm-task\nworktree={wt}\n')
  run([str(root/'bin/fm-busy-event.sh'),'arm',str(state),'task'])
  env=base|{'FM_HOME':str(home)}
  verdict=run([str(root/'bin/fm-crew-state.sh'),'task'],env);assert 'state: working' in verdict,verdict
  (state/'task.status').write_text('working: compiling step 2\n');(state/'task.turn-ended').touch()
  p,env=watch(home)
  wait(lambda:(state/'.seen-task_status').exists() and (state/'.seen-task_turn-ended').exists())
  time.sleep(2)
  assert p.poll() is None and not (home/'watch.out').read_text()
  assert not (state/'.wake-queue').exists() or not (state/'.wake-queue').read_text()
  log.append(f'{name}: routine status and turn-end absorbed; watcher still running, both suppressors advanced, queue empty\n'+(state/'.watch-triage.log').read_text())
  (state/'other.status').write_text('needs-decision: choose A or B\n')
  with (state/'task.status').open('a') as f:f.write('working: compiling step 3\n')
  wait(lambda:p.poll() is not None);assert p.returncode==0
  out=(home/'watch.out').read_text(); log.append('Watcher output:\n'+out);assert str(state/'other.status') in out
  drain=run([str(root/'bin/fm-wake-drain.sh')],env)
  assert str(state/'other.status') in drain and 'choose A or B' in drain
  assert (state/'.hb-surfaced-other').exists(), 'actionable file not classified intact'
 # Separate stopped worker boundary.
 home=area/'stopped home';run([str(root/'bin/fm-lab-home.sh'),'create',str(home)])
 (home/'state/task.turn-ended').touch();p,env=watch(home)
 wait(lambda:p.poll() is not None);assert p.returncode==0
 out=(home/'watch.out').read_text();log.append('Stopped worker output:\n'+out)
 assert str(home/'state/task.turn-ended') in out
 drain=run([str(root/'bin/fm-wake-drain.sh')],env);assert str(home/'state/task.turn-ended') in drain
 log.append('All live scenarios passed. No harness CLI or LLM was simulated; semantic lifecycle records were seeded through fm-busy-event and consumed by the real crew-state and watcher commands.')
finally:
 for p in children:
  if p.poll() is None:p.terminate();p.wait(timeout=15)
 subprocess.run(['tmux','-S',str(socket),'kill-server'],capture_output=True)
 evidence.write_text('\n'.join(log));shutil.rmtree(area)
