# Codex Handover — The Morse Whisperer

The Morse Whisperer is a Raspberry Pi based CW/Morse decoder appliance. The current working state has been pushed to GitHub and the appliance won the CW decoder challenge.

## Current status

Working features:

- Clean/generated CW decoding.
- Real radio/KiwiSDR CW decoding.
- Separate decoder profiles for clean CW and radio CW.
- CLI profile switcher.
- Web UI profile switcher.
- Service restart and runtime decoder clear after web profile switching.
- TFT profile indicator.
- Updated one-shot installer.
- Updated documentation.

Baseline commits before the 2026-06-14 maintenance review:

```text
bd358cd Update documentation and one-shot installer
31b26b5 Update appliance profiles, web switch, TFT labels, and docs
```

Always fetch before comparing the deployed revision with GitHub.

## Profiles

### Clean CW

Internal key: `clean`

Purpose:

- Clean generated CW.
- Built-in self-test.
- Challenge/demo use.
- Strict known-good acceptance gates.

Do not tune Clean CW to fix radio signal problems.

### Radio CW

Internal key: `kiwi`

Purpose:

- Real HF CW.
- KiwiSDR audio.
- Wider tone search up to 2000 Hz.
- More tolerant acceptance gates.

Tune this profile for receiver/radio behaviour.

## Important files

```text
morse_whisperer/        main Python package
profiles/              Clean CW and Radio CW profile JSON files
tools/                 helper scripts and diagnostics
docs/                  project documentation
assets/                display and web assets
config.json            runtime appliance config
install.sh             one-shot installer/rebuild script
```

## Commands for inspection

```bash
cd /opt/morse-whisperer-pi
git -c safe.directory=/opt/morse-whisperer-pi fetch origin
git -c safe.directory=/opt/morse-whisperer-pi status --short --branch
git -c safe.directory=/opt/morse-whisperer-pi log --oneline -5
systemctl is-active morse-whisperer.service
/opt/morse-whisperer-pi/tools/set_decoder_profile.py show
/opt/morse-whisperer-pi/tools/smoke_test.py
```

`config.json` is a runtime file as well as the clean install baseline. It is
normally modified on the appliance by profile selection and local settings.
Treat source-code or untracked-file drift separately from this expected change.

Useful API checks:

```bash
curl -sS http://127.0.0.1:8080/api/decoder/profile | python3 -m json.tool
curl -sS http://127.0.0.1:8080/api/snapshot | python3 -m json.tool | head -80
```

Clean CW self-test:

```bash
curl -sS -X POST http://127.0.0.1:8080/api/cw/selftest \
  -H 'Content-Type: application/json' \
  -d '{"text":"CQ CQ DE ZL1SXG ZL1SXG K","tone_hz":700,"wpm":18.75,"farnsworth_wpm":18.75,"key_profile":"computer","start_delay_ms":250,"end_gap_ms":1000,"volume_percent":50}' \
  | python3 -m json.tool
```

Expected:

```text
status: PASS
decoded: CQ CQ DE ZL1SXG ZL1SXG K
```

## Guardrails

- Keep Clean CW protected.
- Make backups before runtime-critical changes.
- Register Flask routes inside `create_app()` before `return app`.
- Avoid fragile nested shell quoting in Python source.
- If self-test passes but live CW fails, check the physical audio path before changing DSP.
- The web UI has no authentication; keep port 8080 on a trusted LAN.
- Do not force-push.

## Future roadmap

### Repo cleanup

- Audit repo contents and remove accidental runtime files if any are present.
- Keep `.gitignore` coverage for virtualenvs, patch backups, recovery archives, audio captures, logs, and secrets.
- Revisit whether the clean baseline should remain `config.json` long term.
- Keep `requirements.txt` aligned with imports.
- Extend the lightweight smoke test as APIs change.

### Safer profile switching

- Add smoke tests for profile API and reset API.
- Improve web UI error reporting if restart fails.

### Radio CW improvements

- Improve Radio CW tone locking across 400–2000 Hz while avoiding constant heterodynes or whistles.
- Prefer keyed envelope behaviour over raw tone power when selecting a candidate.
- Add tone-lock decay and relock strategy.
- Keep Clean CW behaviour unchanged.

### UI/TFT polish

- Improve the web profile selector visual integration.
- Add profile context to STATUS/SETTINGS pages if helpful.
- Add clearer Radio CW indicators when wide tone search is active.

### Installer hardening

- Test `install.sh` on a fresh Pi image.
- Ensure it is idempotent.
- Add optional dry-run or no-start mode.
- Add USB audio device detection/reporting.
- Add post-install self-test summary.

### Documentation cleanup

- Consolidate overlapping recovery notes.
- Add screenshots/photos of the TFT and web UI.
- Add a short project history note explaining how the challenge was won.
- Add an architecture diagram.
- Add a troubleshooting matrix.

## Suggested initial Codex prompt

```text
You are taking over development of The Morse Whisperer, a Raspberry Pi based CW/Morse decoder appliance.

Start by reading CODEX_HANDOVER.md, README.md, docs/installation.md, docs/operating-guide.md, docs/decoder-profiles.md, and install.sh.

Current priorities:
1. Clean up the repo without breaking the working appliance.
2. Preserve the known-good Clean CW profile.
3. Preserve the working Radio CW profile.
4. Keep profile switch, restart, and clear logic in dedicated tested helpers.
5. Expand smoke tests around state-changing APIs.
6. Keep install.sh idempotent and document assumptions.

Before editing, check git status and service health. Before changing runtime-critical files, create a local backup. Never force push. Prefer small commits and pull requests.
```

## Victory note

This project won the decoder challenge after recovery, tuning, testing, and profile separation. Treat the current behaviour as valuable. Refactor carefully, test often, and keep the Clean CW baseline sacred.
