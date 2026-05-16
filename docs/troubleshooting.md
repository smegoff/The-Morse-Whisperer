# Troubleshooting

## Service status

```bash
sudo systemctl status morse-whisperer --no-pager -l
sudo journalctl -u morse-whisperer -n 200 --no-pager
```

## Web UI

```bash
curl -i http://127.0.0.1:8080/ | sed -n '1,20p'
```

## Display

```bash
for fb in /sys/class/graphics/fb*; do
  echo "--- $fb ---"
  cat "$fb/name" 2>/dev/null || true
  cat "$fb/virtual_size" 2>/dev/null || true
  cat "$fb/bits_per_pixel" 2>/dev/null || true
done
```

## Audio

```bash
arecord -l
aplay -l
pgrep -a arecord
speaker-test -D plughw:2,0 -t sine -f 700 -c 1 -l 1
```

## Network

```bash
nmcli device status
ip -br addr
```
