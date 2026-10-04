import os,pathlib,subprocess,time,shutil
root=pathlib.Path.cwd(); area=root/'.t'; area.mkdir(exist_ok=True)
socket=area/'s'; evidence=pathlib.Path('/home/box/.no-mistakes/evidence/01M431BPET6MZQ04VFTVTW1SV1/live-churn.txt')
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
 run(['tmux','-S',str(socket),'new-session','-d','-s','fm-lab-watch','-n','fm-task',"python3 -u -c 'import time; i=0\nwhile True: print(i); i+=1; time.sleep(.2)'"])
 home=area/'churning spaced home';run([str(root/'bin/fm-lab-home.sh'),'create',str(home)])
 state=home/'state'; wt=home/'projects'/'task';wt.mkdir()
 (home/'config/turnend-churn-absorb').touch()
 (state/'task.meta').write_text(f'kind=ship\nharness=codex\nbackend=tmux\nwindow=fm-lab-watch:fm-task\nworktree={wt}\n')
 p,env=watch(home)
 wait(lambda:list(state.glob('.hash-*')))
 time.sleep(2)
 (state/'task.turn-ended').touch()
 wait(lambda:(state/'.seen-task_turn-ended').exists())
 time.sleep(2)
 assert p.poll() is None and not (home/'watch.out').read_text()
 assert not (state/'.wake-queue').exists() or not (state/'.wake-queue').read_text()
 log.append('Turn-end in spaced home absorbed using actual changing tmux pane, with authoritative crew proof unavailable.\n'+(state/'.watch-triage.log').read_text())
 (state/'task.status').write_text('needs-decision: stop despite pane churn\n')
 wait(lambda:p.poll() is not None);assert p.returncode==0
 log.append('Decision during churn:\n'+(home/'watch.out').read_text())
 drain=run([str(root/'bin/fm-wake-drain.sh')],env)
 assert 'stop despite pane churn' in drain and (state/'.hb-surfaced-task').exists()
 log.append('Churn scenario and actionable override passed.')
finally:
 for p in children:
  if p.poll() is None:p.terminate();p.wait(timeout=15)
 subprocess.run(['tmux','-S',str(socket),'kill-server'],capture_output=True)
 evidence.write_text('\n'.join(log));shutil.rmtree(area)
