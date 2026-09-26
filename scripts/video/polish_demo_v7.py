"""Narration-led camera and a soft instrumental bed for the 90-second real demo.

    python scripts/video/polish_demo_v7.py video|audio|mux

Camera transforms use floating-point cubic resampling and quintic easing.
The real shots, their speed, and the existing voice performance are preserved.
"""
import argparse
import json
import math
import re
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile

ROOT = Path('run/video-v7')
OUT = ROOT / 'export'
BASE = Path('run/video-v6')
FPS, WIDTH, HEIGHT, DURATION = 25, 1920, 1080, 90
EDL = json.loads((BASE / 'export/edit-decisions.json').read_text())
# Seconds, zoom, source-frame center x/y, subject. Repeated poses are calm holds.
CAMERA = [
    (0, 1, 960, 540, 'Overview'),
    (2.8, 1, 960, 540, 'Overview'),
    (8, 1.75, 1330, 550, 'Recorded EEG and electrodes'),
    (11.4, 1.75, 1330, 550, 'Recorded EEG and electrodes'),
    (16.4, 1.70, 960, 545, 'Decide: experiment planning'),
    (18.8, 1.70, 960, 545, 'Decide: experiment planning'),
    (23.8, 1.42, 1215, 696, 'Measured accuracy and results'),
    (25.2, 1.42, 1215, 696, 'Measured accuracy and results'),
    (30.2, 1.18, 960, 620, 'MongoDB Atlas durable memory'),
    (33.0, 1.18, 960, 620, 'MongoDB Atlas durable memory'),
    (38.2, 1.85, 560, 550, 'Remember: retrieved notes and compact evidence'),
    (48.8, 1.85, 560, 550, 'Remember: retrieved notes and compact evidence'),
    (54, 1, 960, 540, 'Full loop and real stop control'),
    (60.4, 1, 960, 540, 'Full loop and real restart control'),
    (64.8, 1.20, 960, 625, 'Recovery, saved results, and attempt two'),
    (65.8, 1.20, 960, 625, 'Recovery, saved results, and attempt two'),
    (70.8, 1.40, 1220, 690, 'Electrode grid and constraint control'),
    (73.2, 1.40, 1220, 690, 'Electrode grid and constraint control'),
    (78.4, 1.18, 960, 620, 'Evidence and continued EEG optimization'),
    (81.8, 1, 960, 540, 'Overview before the repository code'),
    (90, 1, 960, 540, 'Actual code, then the complete research loop'),
]


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def smoothstep(x):
    return x*x*x*(x*(6*x-15)+10)


def pose(time):
    for a, b in zip(CAMERA, CAMERA[1:]):
        if time <= b[0]:
            q = smoothstep(np.clip((time-a[0])/(b[0]-a[0]), 0, 1))
            return np.array(a[1:4]) + (np.array(b[1:4])-np.array(a[1:4]))*q
    return np.array(CAMERA[-1][1:4])


def expression(column):
    result = str(CAMERA[-1][column])
    for a, b in reversed(list(zip(CAMERA, CAMERA[1:]))):
        first, last = round(a[0]*FPS), round(b[0]*FPS)
        if a[column] == b[column]:
            value = str(a[column])
        else:
            q = f'((in-{first})/{last-first})'
            ease = f'({q}*{q}*{q}*({q}*(6*{q}-15)+10))'
            value = f'({a[column]}+({b[column]-a[column]})*{ease})'
        result = f'if(lt(in,{last}),{value},{result})'
    return result


def video():
    OUT.mkdir(parents=True, exist_ok=True)
    frames = np.array([pose(n/FPS) for n in range(FPS*DURATION)])
    z, x, y = frames.T
    bounds = np.stack([x-WIDTH/(2*z), y-HEIGHT/(2*z), x+WIDTH/(2*z), y+HEIGHT/(2*z)], axis=1)
    assert bounds[:, 0].min() >= -1e-6 and bounds[:, 1].min() >= -1e-6
    assert bounds[:, 2].max() <= WIDTH+1e-6 and bounds[:, 3].max() <= HEIGHT+1e-6
    filters = []
    for i, shot in enumerate(EDL['shots']):
        filters.append(f"[0:v]trim=start={shot['source_start']}:duration={shot['output_end']-shot['output_start']},setpts=PTS-STARTPTS[v{i}]")
    filters.append(''.join(f'[v{i}]' for i in range(len(EDL['shots'])))+f"concat=n={len(EDL['shots'])}:v=1:a=0[base]")
    zoom, cx, cy = [expression(i) for i in (1, 2, 3)]
    left, right = f'({cx})-W/(2*({zoom}))', f'({cx})+W/(2*({zoom}))'
    top, bottom = f'({cy})-H/(2*({zoom}))', f'({cy})+H/(2*({zoom}))'
    # Source rectangles map to the output corners without integer crop rounding.
    transform = ':'.join(f"{key}='{value}'" for key, value in [
        ('x0', left), ('y0', top), ('x1', right), ('y1', top),
        ('x2', left), ('y2', bottom), ('x3', right), ('y3', bottom)])
    filters.append(f'[base]perspective={transform}:sense=source:interpolation=cubic:eval=frame[outv]')
    graph = OUT / 'camera-filter.txt'
    graph.write_text(';'.join(filters))
    camera = {'easing': 'quintic smootherstep, zero velocity and acceleration at holds',
              'resampling': 'floating-point source rectangles, cubic interpolation',
              'max_zoom': float(z.max()), 'all_frames_inside_source': True,
              'keyframes': [dict(time=t, zoom=z, center=[x,y], subject=subject) for t,z,x,y,subject in CAMERA]}
    (OUT/'camera.json').write_text(json.dumps(camera, indent=2))
    (OUT/'edit-decisions.json').write_text(json.dumps({**EDL, 'camera':camera,
        'music': 'original instrumental generated with ElevenLabs music_v2_5; voice remains unchanged'}, indent=2))
    run('ffmpeg','-y','-v','error','-i',EDL['source'],'-filter_complex_script',str(graph),
        '-map','[outv]','-an','-c:v','libx264','-preset','medium','-crf','16','-pix_fmt','yuv420p',
        '-r',str(FPS),'-t',str(DURATION),'-movflags','+faststart',str(OUT/'camera.mp4'))
    print('Rendered camera with subpixel motion; all 2250 source rectangles stay in bounds.')


def levels(path):
    result = run('ffmpeg','-hide_banner','-i',str(path),'-af',
        'loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json','-f','null','-',capture_output=True,text=True)
    return json.loads(re.findall(r'\{[^{}]*\}', result.stderr)[-1])


def audio():
    OUT.mkdir(parents=True, exist_ok=True)
    music_file = ROOT/'music/soft-melody.mp3'
    music_levels = levels(music_file)
    gain_db = -29.5-float(music_levels['input_i'])
    run('ffmpeg','-y','-v','error','-i',str(music_file),'-af',f'volume={gain_db}dB,highpass=f=70,lowpass=f=7000',
        '-ar','48000','-ac','2','-t','90','-c:a','pcm_f32le',str(OUT/'music-normalized.wav'))
    sr, voice = wavfile.read(BASE/'export/narration-master.wav')
    msr, music = wavfile.read(OUT/'music-normalized.wav')
    assert sr == msr == 48000
    voice = voice.astype(np.float64)/32768
    count = DURATION*sr
    assert len(voice) == count
    music = np.pad(music[:count], ((0, max(0,count-len(music))), (0,0))).astype(np.float64)
    transcript = json.loads((BASE/'export/transcript-review.json').read_text())
    words = [w for w in transcript['words'] if w['type']=='word']
    phrases = []
    for word in words:
        if phrases and word['start']-phrases[-1][1]<.45:
            phrases[-1][1] = word['end']
        else:
            phrases.append([word['start'], word['end']])
    activity = np.zeros(count)
    for start, end in phrases:
        a, b = max(0,round((start-.25)*sr)), min(count,round((end+1.2)*sr))
        times = np.arange(a,b)/sr
        envelope = np.minimum(smoothstep(np.clip((times-start+.25)/.25,0,1)),
                              1-smoothstep(np.clip((times-end)/1.2,0,1)))
        activity[a:b] = np.maximum(activity[a:b],envelope)
    times = np.arange(count)/sr
    fade = smoothstep(np.clip(times/3.2,0,1))*(1-smoothstep(np.clip((times-85.5)/4.5,0,1)))
    music *= (fade*(1-.33*activity))[:,None]
    mix = voice+music
    master_gain = min(1, 10**(-1.7/20)/np.max(np.abs(mix)))
    mix *= master_gain
    wavfile.write(OUT/'music-ducked.wav',sr,music.astype(np.float32))
    wavfile.write(OUT/'narration-and-melody.wav',sr,mix.astype(np.float32))
    speaking = activity>.95
    voice_rms = np.sqrt(np.mean(voice[speaking]**2))
    music_rms = np.sqrt(np.mean(music[speaking]**2))
    metadata = {'music_original_levels':music_levels,'music_normalization_db':gain_db,
        'music_nominal_lufs':-29.5, 'speech_duck_db':round(20*math.log10(.67),2),
        'voice_above_music_rms_during_speech_db':round(20*math.log10(voice_rms/music_rms),2),
        'master_gain_db':round(20*math.log10(master_gain),2),
        'fade_in_seconds':3.2,'fade_out_seconds':4.5,'voice_time_scaling':False}
    (OUT/'mix.json').write_text(json.dumps(metadata,indent=2))
    print(json.dumps(metadata,indent=2))


def mux():
    run('ffmpeg','-y','-v','error','-i',str(OUT/'camera.mp4'),'-i',str(OUT/'narration-and-melody.wav'),
        '-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','256k','-t','90',
        '-movflags','+faststart',str(OUT/'second-shift-demo.mp4'))
    print('Exported', OUT/'second-shift-demo.mp4')


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['video','audio','mux'])
    {'video':video,'audio':audio,'mux':mux}[parser.parse_args().stage]()
