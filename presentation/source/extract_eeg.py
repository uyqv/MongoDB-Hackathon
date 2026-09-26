"""Extract a real, unfiltered training-recording excerpt for the presentation."""
import hashlib
import json
from pathlib import Path
import mne
from mne.datasets import eegbci

ROOT = Path(__file__).resolve().parents[2]
path = ROOT / "data/eeg/MNE-eegbci-data/files/eegmmidb/1.0.0/S001/S001R06.edf"
raw = mne.io.read_raw_edf(path, preload=False, verbose=False)
eegbci.standardize(raw)
cue = next(a for a in raw.annotations if a["description"] == "T1")
start = int(cue["onset"] * raw.info["sfreq"])
signal = raw.get_data(picks=["C3"], start=start, stop=start + 320)[0] * 1e6
result = {
    "source": "PhysioNet EEG Motor Movement/Imagery v1.0.0",
    "url": "https://physionet.org/content/eegmmidb/1.0.0/",
    "file": path.relative_to(ROOT).as_posix(),
    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    "subject": 1, "run": 6, "channel": "C3", "task": "Imagined both fists",
    "onset_seconds": float(cue["onset"]), "sampling_hz": 160,
    "units": "microvolts", "processing": "Raw, unfiltered, first 2 seconds of the first T1 task cue",
    "times": [round(i/160, 5) for i in range(len(signal))],
    "values": [round(float(v), 4) for v in signal],
}
(ROOT / "presentation/source/eeg.json").write_text(json.dumps(result, indent=2))
print({k:v for k,v in result.items() if k not in ["values", "times"]})
