"""Neuroscience harness demo with the requested voice and a fresh real campaign. No overlays or generated dashboard frames.

The edit decision list maps every exported frame to the continuous raw take.
Silence is inserted between complete narration sentences; voice speed is intact.
"""
import json
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile

ROOT = Path('run/video-v5')
CAPTURE = ROOT / 'take-1'
VOICE = ROOT / 'voice-final'
OUT = ROOT / 'export'
DURATION = 59.6
# Source seconds, duration, reason. Each is frame-aligned at the native 25 fps.
SHOTS = [
    (9.60, 34.88, 'Neuroscience harness, real EEG measurements, crash, saved results, and restart'),
    (47.96, 6.12, 'Same interrupted experiment runs as attempt two'),
    (61.80, 6.00, 'Clear context, reduce the electrode limit, and recompute eligibility'),
    (68.20, 5.72, 'Rebuilt evidence guides the next nine-electrode experiment'),
    (75.44, 2.88, 'Actual context-reconstruction code'),
    (81.28, 4.00, 'Return to the running EEG campaign'),
]
# Preserve the entire generated delivery with a 300 ms opening pause.
VOICE_STARTS = {name: bounds[0] + .3 for name, bounds in
                json.loads((VOICE / 'timeline.json').read_text())['scenes'].items()}


def run(*args):
    subprocess.run(args, check=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sr, source = wavfile.read(VOICE / 'narration.wav')
    audio = np.zeros((round(sr*DURATION), source.shape[1]), dtype=source.dtype)
    timeline = json.loads((VOICE / 'timeline.json').read_text())
    audio_cuts = []
    for name, (start, end) in timeline['scenes'].items():
        # The preceding 120 ms lies in the sentence boundary's recorded silence.
        source_start = max(0, start-.12)
        source_end = end-.12 if end<timeline['total'] else end
        segment = source[round(source_start*sr):round(source_end*sr)].copy()
        # A 3 ms boundary taper is inaudible and prevents discontinuities in silence.
        n = round(.003*sr)
        segment[:n] = (segment[:n]*np.linspace(0,1,n)[:,None]).astype(source.dtype)
        segment[-n:] = (segment[-n:]*np.linspace(1,0,n)[:,None]).astype(source.dtype)
        target_start = VOICE_STARTS[name]-(start-source_start)
        offset = round(target_start*sr)
        assert offset>=0 and offset+len(segment)<=len(audio)
        audio[offset:offset+len(segment)] = segment
        audio_cuts.append({'scene':name,'source':[source_start,source_end],
                           'timeline':[target_start,target_start+len(segment)/sr],
                           'spoken_alignment_start':VOICE_STARTS[name]})
    wavfile.write(OUT/'narration-timed.wav',sr,audio)
    # Only loudness changes; sample rate, duration, and delivery speed stay fixed.
    run('ffmpeg','-y','-v','error','-i',str(OUT/'narration-timed.wav'),
        '-af','loudnorm=I=-16:TP=-1.5:LRA=11','-ar','48000','-c:a','pcm_s16le',str(OUT/'narration-master.wav'))
    filters, edl, at = [], [], 0
    for i,(start,duration,reason) in enumerate(SHOTS):
        filters.append(f'[0:v]trim=start={start}:duration={duration},setpts=PTS-STARTPTS[v{i}]')
        edl.append({'shot':i+1,'source_start':start,'source_end':round(start+duration,3),
                    'output_start':round(at,3),'output_end':round(at+duration,3),'playback_speed':1,'content':reason})
        at+=duration
    assert abs(at-DURATION)<.001
    filters.append(''.join(f'[v{i}]' for i in range(len(SHOTS)))+f'concat=n={len(SHOTS)}:v=1:a=0[outv]')
    run('ffmpeg','-y','-v','error','-i',str(CAPTURE/'raw-continuous.webm'),
        '-i',str(OUT/'narration-master.wav'),'-filter_complex',';'.join(filters),
        '-map','[outv]','-map','1:a:0','-c:v','libx264','-preset','slow','-crf','17',
        '-pix_fmt','yuv420p','-r','25','-c:a','aac','-b:a','192k','-t',str(DURATION),
        '-movflags','+faststart',str(OUT/'second-shift-demo.mp4'))
    (OUT/'edit-decisions.json').write_text(json.dumps({'duration':DURATION,'source':str(CAPTURE/'raw-continuous.webm'),
        'shots':edl,'narration':audio_cuts},indent=2))
    print('Exported',OUT/'second-shift-demo.mp4')


if __name__=='__main__':
    main()
