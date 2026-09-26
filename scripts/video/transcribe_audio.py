"""Independently transcribe narration for completeness and word-timing checks.

Usage: python scripts/video/transcribe_audio.py AUDIO OUTPUT_JSON
Only the requested audio is sent to ElevenLabs. Credentials are never logged.
"""
import json
import sys
from pathlib import Path

import httpx
from dotenv import dotenv_values


def main():
    source, destination = map(Path, sys.argv[1:3])
    key = dotenv_values('.env')['ELEVENLABS_API_KEY']
    with source.open('rb') as audio:
        response = httpx.post(
            'https://api.elevenlabs.io/v1/speech-to-text',
            headers={'xi-api-key': key},
            data={'model_id': 'scribe_v2', 'language_code': 'eng', 'tag_audio_events': 'true'},
            files={'file': (source.name, audio)},
            timeout=180,
        )
    if response.status_code != 200:
        raise SystemExit(f'Transcription failed: HTTP {response.status_code}')
    data = response.json()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(data, indent=2))
    words = [word for word in data.get('words', []) if word.get('type') == 'word']
    print(json.dumps({'words': len(words), 'speech_start': words[0]['start'] if words else None,
                      'speech_end': words[-1]['end'] if words else None,
                      'audio_events': [word.get('text') for word in data.get('words', [])
                                       if word.get('type') == 'audio_event']}))


if __name__ == '__main__':
    main()
