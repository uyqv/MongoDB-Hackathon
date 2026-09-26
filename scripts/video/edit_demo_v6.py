"""Ninety-second NeuroAI harness presentation with the requested voice. No overlays or generated dashboard frames.

The edit decision list maps every exported frame to the continuous raw take.
Silence is inserted between complete narration sentences; voice speed is intact.
"""
import json
import re
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile

ROOT = Path('run/video-v6')
CAPTURE = ROOT / 'take-1'
VOICE = ROOT / 'voice-final'
OUT = ROOT / 'export'
DURATION = 90.0
# Source seconds, duration, reason. Each is frame-aligned at the native 25 fps.
SHOTS = [
    (18.40, 59.48, 'EEG experiment loop, numerical feedback, growing memory, real interruption'),
    (79.52, 4.32, 'Restart through the working dashboard'),
    (91.44, 2.96, 'Interrupted EEG experiment commits as attempt two'),
    (94.80, 6.00, 'Clear context and reduce the electrode limit from 64 to nine'),
    (106.40, 9.24, 'Fresh evidence packet and another measured nine-electrode experiment'),
    (117.20, 2.60, 'Actual context-reconstruction code'),
    (123.00, 5.40, 'Return to the EEG campaign and its improved eligible result'),
]
# Cumulative pauses. The generated speech itself is never time-scaled.
OFFSETS = dict(intro=.3, position=.3, planning=.3, metrics=.3, memory=.3,
               scale=.3, kill=1.3, recover=2.2, goal=2.7, adapt=3.3, close=3.8)


def canonical_words(text):
    # ASR writes these spoken brand names as two words.
    text = re.sub(r'neuroai', 'neuro ai', text, flags=re.I)
    text = re.sub(r'openrouter', 'open router', text, flags=re.I)
    return re.findall(r'[a-z0-9]+', text.lower())


def narration_segments():
    scenes = json.loads((VOICE / 'narration.json').read_text())
    transcript = json.loads((VOICE / 'transcript-review.json').read_text())
    words = [dict(text=token, start=word['start'], end=word['end'])
             for word in transcript['words'] if word['type'] == 'word'
             for token in canonical_words(word['text'])]
    expected = canonical_words(' '.join(scene['text'] for scene in scenes))
    assert expected == [word['text'] for word in words], 'Transcription differs from narration'
    cursor, spans = 0, []
    for scene in scenes:
        count = len(canonical_words(scene['text']))
        spans.append(dict(scene=scene['id'], first=words[cursor]['start'], last=words[cursor+count-1]['end']))
        cursor += count
    total = json.loads((VOICE / 'timeline.json').read_text())['total']
    cuts = [0]
    for previous, following in zip(spans, spans[1:]):
        assert following['first'] - previous['last'] > .06, 'No safe sentence-boundary silence'
        cuts.append((previous['last']+following['first'])/2)
    cuts.append(total)
    return [(span, cuts[i], cuts[i+1]) for i, span in enumerate(spans)]


def run(*args):
    subprocess.run(args, check=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sr, source = wavfile.read(VOICE / 'narration.wav')
    audio = np.zeros((round(sr*DURATION), source.shape[1]), dtype=source.dtype)
    audio_cuts = []
    previous_end = 0
    for span, source_start, source_end in narration_segments():
        name = span['scene']
        segment = source[round(source_start*sr):round(source_end*sr)].copy()
        # ASR places these boundaries in silence, away from both spoken words.
        n = round(.003*sr)
        segment[:n] = (segment[:n]*np.linspace(0,1,n)[:,None]).astype(source.dtype)
        segment[-n:] = (segment[-n:]*np.linspace(1,0,n)[:,None]).astype(source.dtype)
        target_start = source_start + OFFSETS[name]
        offset = round(target_start*sr)
        assert offset >= previous_end and offset+len(segment) <= len(audio)
        audio[offset:offset+len(segment)] = segment
        previous_end = offset+len(segment)
        audio_cuts.append({'scene':name, 'source':[source_start, source_end],
                           'timeline':[target_start, target_start+len(segment)/sr],
                           'spoken_range':[span['first']+OFFSETS[name],span['last']+OFFSETS[name]]})
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
