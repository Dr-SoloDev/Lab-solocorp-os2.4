# Local Piper Setup

This directory holds local-only Piper model files. The model files are ignored
by Git because they are large; `scripts/local_tts_piper.py` uses the bundled
model directory by default and invokes the locally installed Piper CLI.

Current local voice: `th_TH-tsync2-medium` (22.05 kHz). Its model card records
the `vaja-thai` dataset under CC BY-NC-SA 3.0, non-commercial. Treat generated
audio as an internal, rights-unverified draft. Do not use it in a commercial
or public release unless a separately cleared voice/model is configured.

The CLI is currently installed at `/data/venvs/tts/bin/piper`. Set
`PIPER_BIN` to another local executable when moving this checkout. The TTS
wrapper never downloads a model or calls a remote provider.
