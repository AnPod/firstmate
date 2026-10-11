import os, pathlib, subprocess, tempfile, time, shutil, json
root=pathlib.Path.cwd(); results=[]
for mode in ['settled','arriving','missing','older','equal','absent','working','bare','fractional','joining','default-dedup']:
    lab=pathlib.Path(tempfile.mkdtemp(prefix='.watch-lab-',dir=root)); p=None
    try:
        subprocess.run(['bin/fm-lab-home.sh','create',str(lab)],check=True,capture_output=True)
        state=lab/'state'; (lab/'tmux').mkdir()
        env={k:v for k,v in os.environ.items() if not k.startswith('FM_')}
        env.update(FM_HOME=str(lab),FM_POLL='1',FM_CHECK_INTERVAL='999999',FM_HEARTBEAT='999999',FM_SECONDMATE_LIVENESS_SECS='99999999',TMUX_TMPDIR=str(lab/'tmux'),TMUX=str(lab/'tmux'/'isolated.sock')+',99999,0')
        grace=6 if mode in ['settled','arriving'] else 2.5 if mode=='fractional' else 30 if mode=='default-dedup' else 2
        if mode!='default-dedup': env['FM_SIGNAL_GRACE']=str(grace)
        base=int(time.time())-20
        def write(name,text='',stamp=base):
            f=state/name; f.write_text(text); os.utime(f,(stamp,stamp))
        if mode!='bare': write('one.status','working: progress\n' if mode=='working' else 'done: finished\n')
        if mode in ['settled','missing','older','equal']:
            write('two.status','paused: waiting for reset\n'); write('one.turn-ended',stamp=base+1)
            if mode!='missing':write('two.turn-ended',stamp=base+1 if mode=='settled' else base-1 if mode=='older' else base)
        if mode in ['working','fractional']:write('one.turn-ended',stamp=base+1)
        if mode=='bare':write('one.turn-ended')
        p=subprocess.Popen(['bin/fm-watch.sh'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        deadline=time.monotonic()+10
        while not (state/'.last-watcher-beat').exists() and p.poll() is None and time.monotonic()<deadline:time.sleep(.02)
        assert (state/'.last-watcher-beat').exists(), 'missing poll beacon'
        start=time.monotonic()
        if mode in ['arriving','joining']:
            time.sleep(.6)
            if mode=='joining':write('two.status','blocked: another task needs help\n')
            else:write('one.status','done: finished\ndone: final report updated\n')
            write('one.turn-ended',stamp=base+1)
        out,err=p.communicate(timeout=45); elapsed=time.monotonic()-start
        queue=(state/'.wake-queue').read_text(); rows=[r.split('\t') for r in queue.splitlines() if '\tsignal\t' in r]
        expected=sorted(f.name for f in state.iterdir() if f.suffix in ['.status','.turn-ended'])
        keys=sorted(r[3] for r in rows)
        assert keys==expected,(keys,expected)
        assert 'signal:' in out,out+err
        assert elapsed<4.5 if mode in ['settled','arriving'] else elapsed>=grace-.15,(mode,elapsed)
        markers={f.name:f.read_text() for f in state.glob('.seen-*')}
        if mode=='arriving':assert any(str((state/'one.status').stat().st_size)+'@' in v for k,v in markers.items() if k.endswith('_status')),markers
        result=dict(mode=mode,result='pass',elapsed_seconds=round(elapsed,3),grace=grace,stdout=out,stderr=err,queue=queue,markers=markers)
        results.append(result); print(json.dumps(result),flush=True)
    except Exception as e:
        results.append(dict(mode=mode,result='fail',error=str(e))); print(json.dumps(results[-1]),flush=True)
    finally:
        if p and p.poll() is None:p.terminate();p.communicate(timeout=10)
        # Summary publishing is asynchronous; let it finish before deleting its isolated home.
        time.sleep(.5);shutil.rmtree(lab)
path=pathlib.Path('/home/box/.no-mistakes/evidence/01M4MQ7GZ7MJ3J9X33CN0S6Q68/watch-results.json');path.write_text(json.dumps(results,indent=2))
assert all(r['result']=='pass' for r in results)
