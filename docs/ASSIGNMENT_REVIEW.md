# Assignment and proposal review

Reviewed source: `ICT3214 Security Analytics.docx`, including both the assignment-guideline section and the full team proposal, its references, and embedded pipeline diagram. Reviewed `member_split.jpg` for the role split. The DOCX is one OOXML document containing both sections in sequence; the exported content includes both of the sections described as tabs.

The assignment text is context for the coursework, not a separate request to perform all team tasks. This implementation follows the user's request for Member 5 and their selected web frontend + FastAPI stack. The proposal's initial Gradio suggestion is therefore superseded for this component.

## Assignment requirements

The coursework asks the team to identify a cybersecurity use case, compare existing AI approaches, implement a technically substantial proof of concept, and demonstrate novelty/improvement with evaluation. Deepfake detection is explicitly listed as a suitable use case. The emphasis is analysis and defence; generating attack samples alone is insufficient.

The proposal deadline is 21 September 2026 at 9:00 AM. The final deadline is **21 October 2026 at 11:59 PM**, according to the supplied guidelines. Final deliverables are a ZIP containing source/binaries and a comprehensive user manual; an IEEE conference-format report of at least six pages with evaluation; a 15–20-slide deck; and peer evaluation if requested. The final report needs at least ten references, with at least 70% from reputable journals/conferences. A short, accurate GenAI-use disclosure must accompany the final deliverables.

The guidelines assess literature-review depth, technical competence, innovation, complexity, correctness, and report/code quality. Interface polish is useful, but the project's research contribution must be supported by actual detector experiments. This interface cannot establish robustness or model performance by itself.

## Proposal design

The proposal is titled **Robust Deepfake Voice Detection and Scam Cue Analysis Using Self-Supervised Speech Models**. It names six team members. Its main research objective is improved robustness and generalization, using a pretrained speech encoder such as WavLM plus a lightweight classifier rather than training a large encoder from scratch.

The proposal describes two separate signals:

- Audio authenticity: likely authentic, synthetic, or inconclusive; overlapping windows provide suspicious timestamps and an aggregate score.
- Spoken content: Whisper transcription followed by contextual scam-cue analysis for urgency, authority impersonation, credential/OTP requests, suspicious payments, threats, and secrecy.

The embedded diagram forks after audio input. One branch preprocesses audio, generates windows, runs the WavLM detector, and outputs segment/overall scores. The other performs speech-to-text and scam-cue analysis, ending in a separate scam-risk assessment. This separation is preserved in the frontend and result schema.

Planned robustness augmentations include compression, resampling, background noise, volume changes, and telephone-band filtering. A clean-trained baseline and augmented robust detector share the same architecture so their differences can be attributed to the training setup. ASVspoof official train/development/held-out partitions are the primary dataset plan; WaveFake is an optional external dataset. Evaluation covers clean, degraded, bandwidth-limited, and unseen-generator/cross-dataset audio, with accuracy, precision, recall, F1, ROC-AUC, and EER. Augmentation ablations are optional. Scam-cue evaluation should include benign financial/security conversation to measure false positives.

The literature discussion motivates self-supervised representations using WavLM work, ASVspoof, cross-generator generalization research, and WaveFake. AASIST is the open-source comparator; Pindrop Pulse is a commercial comparator. These are the proposal's claims and intended comparisons, not externally verified empirical results from this implementation.

## Member 5 responsibilities

The supplied image assigns Member 1 to the voice detector, Member 2 to the scam classifier/LLM pipeline, Member 3 to audio preprocessing/Whisper/dataset preparation, Member 4 to feature extraction/classifier training, and Member 5 to **integration, frontend, API, dashboard, and end-to-end pipeline**.

The role image contains five role rows while the assignment and proposal describe six members. Confirm the sixth member's responsibility within the team. This does not prevent Member 5's implementation. Member 3 owns the canonical preprocessing contract; this API's normalization and segmentation are integration defaults to reconcile with that work before connecting the checkpoint.

## Requirements traceability

| Source requirement | Implementation / status |
| --- | --- |
| User: audio uploads | Browser file picker/drop zone and multipart API |
| User follow-up: localhost only and portable infrastructure | Same-origin local API, Dockerfile/Compose with loopback port, native setup scripts, source ZIP |
| User: video uploads | FFmpeg extracts first audio track; video imagery is not analyzed |
| Proposal: WAV/MP3 support | Implemented, plus M4A/FLAC/OGG/WEBM and common video containers |
| Proposal: standardized audio | 16 kHz mono PCM with float32 samples for model input |
| Proposal: overlapping windows | Default 4-second windows, 2-second hop, full tail coverage |
| User: run against member's model | Plugin factory loads once; `predict` contract and score validation |
| Proposal: authentic/synthetic/inconclusive | Provisional lower/upper thresholds; coverage check |
| User: detailed standout audio report | Window scores, merged elevated ranges, replay, waveform, model evidence |
| Proposal: overall score | Time-weighted aggregation of overlapping scores |
| Proposal: silence/short/quality checks | Minimum duration, RMS energy screen, clipping metrics; not full speech VAD |
| Proposal: transcription and scam cues | Result contract and UI implemented; actual content pipeline is teammate-owned |
| Proposal: separate scam/deepfake assessments | Separate dashboard cards and result fields |
| Proposal: microphone recording where feasible | Optional; deferred from this upload-focused implementation |
| Proposal: end-to-end error cases | Tests for corrupt/unsupported/short/silent media, missing track, model/content failure |
| Assignment: source/manual | Local source tree, README, integration contract, launch script |
| Assignment: quantitative performance comparison | Requires teammates' trained detectors and evaluation; no accuracy claims made |
| Assignment: final report/deck/disclosure | Review notes and disclosure draft provided; full team deliverables still required |

## Report interpretation

The requested “which parts stand out” can be supported by real segment scores and timestamps. A high-scoring window shows where the model responded strongly. It does not automatically establish exact manipulated boundaries or why the model responded. Acoustic explanations such as pitch instability, vocoder artifacts, or unnatural pauses should only be displayed when a validated explanation method supplies them. The API accepts optional model evidence and the frontend displays it without inventing explanations.

Scores should be called model scores until calibration has been measured. The current 0.35 / 0.65 thresholds are implementation defaults, not results justified by the supplied proposal. Low energy is a quality screen, not proof of insufficient speech. Music, noise, silence, poor transcription, and unseen generators should be tested with the real detector and appropriate speech gating.

## Proposal cleanup items before submission

The proposal has ten numbered references. By type, [1], [2], [3], [4], [5], [6], [7], and [8] appear to be journal/conference entries, while [9] is a repository and [10] a product page. This nominally meets 70% by count if their details and publication quality are confirmed; this review does not independently verify their bibliographic accuracy. Verify IEEE formatting, dates, URLs, and venue details against the original sources.

The document contains leftover standalone website/link labels such as “Pindrop”, “ISCA Archive”, and “GitHub”; the text “isolated keys” likely means “isolated keywords.” Clean these in the final report. The proposal states English audio as scope; document and evaluate any language limitation. Keep claims of robustness tied to measured baseline/robust comparisons rather than interface features.

## Remaining team work

Agree preprocessing and the synthetic-class convention with Members 1 and 3; provide/check the checkpoint adapter; calibrate thresholds; integrate Members 2–4's actual transcript and scam analysis; run benchmark and degraded/unseen-audio evaluations; measure end-to-end latency; verify the app with benign/scam-like transcripts; and prepare the final report, deck, and accurate disclosure.
