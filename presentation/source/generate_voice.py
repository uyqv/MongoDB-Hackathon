"""Use the existing ElevenLabs integration without changing the demo pipeline."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("second_shift_existing_tts", ROOT / "scripts/video/tts_elevenlabs.py")
tts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tts)
tts.SCENES = json.loads((ROOT / "presentation/source/narration.json").read_text())
tts.OUT = ROOT / "presentation/.build/voice"
tts.main()
