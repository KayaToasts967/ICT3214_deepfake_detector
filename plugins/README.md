# Team adapters

Put your real detector adapter here as `your_detector.py`. Set
`DETECTOR_PLUGIN=plugins.your_detector:create_detector` in `.env`.
Follow `docs/INTEGRATION.md` for the interface contract.

Put the optional transcription/scam adapter here as `your_content.py` and set
`CONTENT_PLUGIN=plugins.your_content:create_analyzer`.

Add their pinned Python dependencies to `requirements-model.txt`, rerun the
native setup or rebuild the container, and restart the app. Model loading stays
local; place checkpoints/tokenizer files in `models/` and use `MODEL_DIR` to
locate them. No trained model is supplied with this project.
