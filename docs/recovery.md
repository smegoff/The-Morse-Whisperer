# Recovery Guide

## Local recovery archives

Known-good recovery archives are stored outside the repo:

```text
/home/decoder/mw-recovery-backups/
```

These are intentionally excluded from Git.

## Restore from extracted archive

From the extracted archive root:

```bash
sudo systemctl stop morse-whisperer.service morse-whisperer-buttons.service 2>/dev/null || true

sudo rsync -aHAX opt/morse-whisperer-pi/ /opt/morse-whisperer-pi/

sudo cp -a etc/systemd/system/morse-whisperer.service /etc/systemd/system/ 2>/dev/null || true

sudo rm -rf /etc/systemd/system/morse-whisperer.service.d
sudo cp -a etc/systemd/system/morse-whisperer.service.d /etc/systemd/system/ 2>/dev/null || true

sudo cp -a etc/systemd/system/morse-whisperer-buttons.service /etc/systemd/system/ 2>/dev/null || true

sudo systemctl daemon-reload
sudo systemctl restart morse-whisperer.service
sudo systemctl restart morse-whisperer-buttons.service 2>/dev/null || true
```

## Verify after restore

```bash
systemctl is-active morse-whisperer.service
curl -sS http://127.0.0.1:8080/api/snapshot | python3 -m json.tool
```

Run the Clean CW self-test:

```bash
curl -sS -X POST http://127.0.0.1:8080/api/cw/selftest \
  -H 'Content-Type: application/json' \
  -d '{"text":"CQ CQ DE ZL1SXG ZL1SXG K","tone_hz":700,"wpm":18.75,"farnsworth_wpm":18.75,"key_profile":"computer","start_delay_ms":250,"end_gap_ms":1000,"volume_percent":50}' \
  | python3 -m json.tool
```

Expected:

```text
status: PASS
```
