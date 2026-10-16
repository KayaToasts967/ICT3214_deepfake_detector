# Local model files

Place detector checkpoints, processor/tokenizer configuration, and any speech
recognition model files here. This directory is mounted read-only at
`/app/models` in Docker. Native setup uses `MODEL_DIR=models` by default.

The release ZIP includes this README, but excludes weights and other files in
this directory. Share agreed model artifacts separately. Docker disables
Hugging Face automatic network downloads; adapters should load from local paths.
