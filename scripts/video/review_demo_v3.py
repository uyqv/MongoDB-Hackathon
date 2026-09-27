"""Export checks, muted-review contact sheets, and cut-boundary frames."""
import json
import math
import os
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

ROOT=Path(os.environ.get('VIDEO_REVIEW_ROOT','run/video-v7'))
CAPTURE=Path(os.environ.get('VIDEO_EVIDENCE_DIR','run/video-v6/take-1'))
VIDEO=ROOT/'export/second-shift-demo.mp4'
OUT=ROOT/'review'


def frame(t,path,width=960):
    subprocess.run(['ffmpeg','-y','-v','error','-ss',str(t),'-i',str(VIDEO),'-frames:v','1',
                    '-vf',f'scale={width}:-1',str(path)],check=True)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(VIDEO)]))
    video=next(s for s in probe['streams'] if s['codec_type']=='video')
    assert (video['width'],video['height'])==(1920,1080)
    duration = float(probe['format']['duration'])
    assert duration <= float(os.environ.get('VIDEO_MAX_SECONDS', '90'))
    if os.environ.get('VIDEO_TARGET_SECONDS'):
        assert abs(duration-float(os.environ['VIDEO_TARGET_SECONDS'])) < .04
    assert [s['codec_type'] for s in probe['streams']]==['video','audio']
    (OUT/'media-probe.json').write_text(json.dumps(probe,indent=2))
    edl=json.loads((ROOT/'export/edit-decisions.json').read_text())
    events=json.loads((CAPTURE/'events.json').read_text())
    proof=json.loads((CAPTURE/'recovery-proof.json').read_text())
    experiments=json.loads((CAPTURE/'experiments.json').read_text())
    claims=[e for e in events if e['type']=='job_claimed' and e['payload']['experiment_id']==proof['interrupted_id']]
    assert [e['payload']['attempt'] for e in claims]==[1,2]
    killed=next(e for e in events if e['type']=='worker_killed')
    commit=next(e for e in events if e['type']=='job_committed' and e['payload']['experiment_id']==proof['interrupted_id'])
    assert claims[0]['ts']<killed['ts']<claims[1]['ts']<commit['ts']
    for old in proof['preserved_results']:
        current=next(e for e in experiments if e['_id']==old['id'])
        assert current['result']==old['result'] and current['attempt']==old['attempt']
    committed_before_kill = [e for e in events if e['type']=='job_committed' and e['ts']<killed['ts']]
    for event in committed_before_kill:
        experiment_id = event['payload']['experiment_id']
        current = next(e for e in experiments if e['_id']==experiment_id)
        assert current['status']=='done' and current['attempt']==1
        assert current['result']['val_balanced_accuracy']==event['payload']['val_balanced_accuracy']
        assert sum(e['type']=='job_committed' and e['payload'].get('experiment_id')==experiment_id
                   for e in events)==1
    packets=json.loads((CAPTURE/'packets.json').read_text())
    next_goal=sorted([p for p in packets if p['goal']['goal_version']==2 and p['context_epoch']==1],key=lambda p:p['ts'])
    assert next_goal
    first_incumbent = next_goal[0]['incumbent']
    if first_incumbent:
        eligible = next(e for e in experiments if e['_id'] == first_incumbent['experiment_id'])
        assert eligible['config']['channels'] == 'central9'
        assert eligible['result']['val_balanced_accuracy'] == first_incumbent['val_balanced_accuracy']
    for e in experiments:
        if e.get('proposed_by',{}).get('packet_id') in {p['_id'] for p in next_goal}:
            assert e['config']['channels']=='central9'
    checks={'dimensions':'1920 × 1080','duration_seconds':float(probe['format']['duration']),
        'frames_per_second':video['r_frame_rate'],'streams':['video','audio'],
        'native_speed_all_shots':all(s['playback_speed']==1 for s in edl['shots']),
        'interrupted_experiment':proof['interrupted_id'],'verified_attempts':[1,2],
        'previous_results_unchanged':len(proof['preserved_results']),
        'pre_crash_committed_results_verified':len(committed_before_kill),
        'new_goal_packet_count':len(next_goal),
        'first_new_goal_incumbent':first_incumbent['experiment_id'] if first_incumbent else None,
        'all_new_goal_proposals_use_nine_electrodes':True}
    (OUT/'verification.json').write_text(json.dumps(checks,indent=2))
    for group in range(math.ceil(duration/20)):
        sheet=Image.new('RGB',(1920,952),'#eeeeee')
        draw=ImageDraw.Draw(sheet)
        for i in range(20):
            t=group*20+i+.2
            if t >= duration:
                break
            f=OUT/f'second-{group*20+i:02d}.jpg';frame(t,f,384)
            x,y=(i%5)*384,(i//5)*238
            sheet.paste(Image.open(f),(x,y+22));draw.text((x+8,y+5),f'{t:05.1f}s',fill='black')
        sheet.save(OUT/f'muted-review-{group+1}.jpg',quality=95)
    boundaries=[s['output_start'] for s in edl['shots'][1:]]
    for i,t in enumerate(boundaries):
        sheet=Image.new('RGB',(1920,570),'#eeeeee');draw=ImageDraw.Draw(sheet)
        for j,delta in enumerate([-.04,.04]):
            f=OUT/f'cut-{i+1}-{j}.png';frame(t+delta,f)
            sheet.paste(Image.open(f),(j*960,30));draw.text((j*960+12,8),f'Cut {i+1}: {t+delta:.2f}s',fill='black')
        sheet.save(OUT/f'cut-{i+1}.jpg',quality=95)
    print(json.dumps(checks,indent=2))


if __name__=='__main__':
    main()
