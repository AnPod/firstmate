import os, pathlib, subprocess, tempfile, shutil, json
root=pathlib.Path.cwd()
evidence=pathlib.Path('/home/ubuntu/.no-mistakes/evidence/01M3MNM74DNRNQE28001Q9YR1C')
base=root/'bin/fm-watch-before-space-test.sh'
base.write_bytes(subprocess.check_output(['git','show','d5c2507ab4cac59b1103134140af4fe0934bd0da:bin/fm-watch.sh']))
results=[]
try:
 for version,script in [('before',base),('after',root/'bin/fm-watch.sh')]:
  for case in ['decision-batch','unknown-turnend','plain-home']:
   home=pathlib.Path(tempfile.mkdtemp(prefix='.watch live home ' if case!='plain-home' else '.watch-control-',dir=root))
   try:
    subprocess.run(['bash','bin/fm-lab-home.sh','create',str(home)],check=True,stdout=subprocess.DEVNULL)
    state=home/'state'
    if case=='unknown-turnend':
     (home/'config/turnend-churn-absorb').touch()
     (state/'stopped.turn-ended').write_text('turn ended\n')
    else:
     (state/'choice.status').write_text('needs-decision: choose release target\nworking: preparing options\n')
     (state/'ordinary.status').write_text('working: preparing report\n')
    env={k:v for k,v in os.environ.items() if not k.startswith('FM_')}
    env.update(FM_HOME=str(home),FM_BACKEND='tmux',TMUX=str(home/'no-server')+',0,0',FM_POLL='1',FM_SIGNAL_GRACE='1',FM_HEARTBEAT='999999',FM_CHECK_INTERVAL='999999',FM_SECONDMATE_LIVENESS_SECS='99999999')
    p=subprocess.run(['bash',str(script)],env=env,capture_output=True,text=True,timeout=35)
    queue=(state/'.wake-queue').read_text() if (state/'.wake-queue').exists() else ''
    markers={x.name:x.read_text() for x in state.glob('.seen*') if x.is_file()}
    row=dict(version=version,case=case,home=str(home),exit=p.returncode,stdout=p.stdout,stderr=p.stderr,queue=queue,markers=markers)
    if case=='unknown-turnend':
     row['passed']=p.returncode==0 and 'stopped.turn-ended' in queue
    else:
     rows=[x.split('\t') for x in queue.splitlines()]
     row['passed']=p.returncode==0 and len({tuple(r[2:]) for r in rows})==2 and any('choice.status' in x and 'needs-decision:' in x for x in queue.splitlines()) and any('ordinary.status' in x and '\tsignal:' in x for x in queue.splitlines()) and p.stdout.count(str(state/'choice.status'))==1
    results.append(row)
    print(json.dumps(row),flush=True)
   finally:
    shutil.rmtree(home)
finally:
 base.unlink()
 (evidence/'watch-live-results.json').write_text(json.dumps(results,indent=2)+'\n')
assert all(r['passed'] for r in results if r['version']=='after'), 'target scenario failed'
assert not next(r['passed'] for r in results if r['version']=='before' and r['case']=='decision-batch'), 'baseline did not reproduce'
