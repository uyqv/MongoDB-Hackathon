# Attribution

## Dataset

**EEG Motor Movement/Imagery Dataset (eegmmidb), v1.0.0**, PhysioNet.
DOI: [10.13026/C28G6P](https://doi.org/10.13026/C28G6P) · https://physionet.org/content/eegmmidb/1.0.0/
License: Open Data Commons Attribution License v1.0.

Recorded with the BCI2000 system. Please cite:

> Schalk, G., McFarland, D.J., Hinterberger, T., Birbaumer, N., Wolpaw, J.R. BCI2000: A General-Purpose Brain-Computer Interface (BCI) System. *IEEE Transactions on Biomedical Engineering* 51(6):1034–1043, 2004.

and the standard PhysioNet citation:

> Goldberger, A., Amaral, L., Glass, L., Hausdorff, J., Ivanov, P.C., Mark, R., Mietus, J.E., Moody, G.B., Peng, C.K., Stanley, H.E. PhysioBank, PhysioToolkit, and PhysioNet: Components of a new research resource for complex physiologic signals. *Circulation* 101(23):e215–e220, 2000.

We use runs 6, 10 and 14 (imagined both fists, T1, vs imagined both feet, T2) for subjects 1–5. The data is downloaded at run time through MNE-Python and is not redistributed in this repository, except a 6-second, 3-channel (C3/Cz/C4) filtered display trace from subject 1 run 6 embedded in `deck/src/snapshot/campaign.json` for the video scenes.

## Software and services

| Component | Use here | License / terms |
|---|---|---|
| [MNE-Python](https://mne.tools) (Gramfort et al., *Frontiers in Neuroscience* 7:267, 2013) | EDF loading, channel standardization, filtering, CSP, Welch PSD | BSD-3-Clause |
| [scikit-learn](https://scikit-learn.org) (Pedregosa et al., *JMLR* 12:2825–2830, 2011) | LDA, logistic regression, metrics | BSD-3-Clause |
| NumPy, SciPy | numerics | BSD-3-Clause |
| [FastAPI](https://fastapi.tiangolo.com) + Uvicorn | HTTP API and static dashboard | MIT / BSD-3-Clause |
| [Chart.js](https://www.chartjs.org) (via jsDelivr CDN) | dashboard charts | MIT |
| [PyMongo](https://pymongo.readthedocs.io) | Atlas access | Apache-2.0 |
| [MongoDB Atlas](https://www.mongodb.com/atlas) (hackathon Sandbox cluster) | all durable state; Atlas Vector Search for memory retrieval | MongoDB terms of service |
| [Voyage AI](https://www.voyageai.com) `voyage-3.5` | memory and query embeddings | Voyage AI terms of service |
| [OpenRouter](https://openrouter.ai) | planner model access (`anthropic/claude-sonnet-5`), usage and cost reporting | OpenRouter terms of service |
| Anthropic Claude (through OpenRouter) | chooses the next experiment and cites evidence; never computes or reports metrics | Anthropic usage policies |
| OpenAI Python SDK | OpenAI-compatible client pointed at OpenRouter | Apache-2.0 |
| [three.js](https://threejs.org), [React Three Fiber](https://github.com/pmndrs/react-three-fiber), [drei](https://github.com/pmndrs/drei), React, Vite | 3D video scenes in `deck/` | MIT |
| **RobotExpressive** 3D model by Tomás Laulhé (modified by Don McCurdy), from the three.js examples | the animated agent in `deck/` scenes | CC0 1.0 |
| [FFmpeg](https://ffmpeg.org) | local video cut (`deck/scripts/cut.sh`), not redistributed | LGPL/GPL |

## What is original work from today

Only the harness (campaign state machine, leased job store, context builder, planner validation and fallback, memory layer, operator controls), the adapter integration with the libraries and services above, the tests, the ablation fixtures, the dashboard UI, and the 3D video scenes in `deck/` (code only; the robot model is CC0 third-party work) were written during the hackathon on September 26, 2026. The EEG dataset, the signal-processing and machine-learning methods (CSP, band power, LDA, logistic regression), and every library and service listed above are the work of their respective authors.
