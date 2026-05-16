# Backup and Recovery

Create a full recovery archive from a working Pi:

```bash
cd /opt
sudo tar -czf /home/decoder/morse-whisperer-known-good-$(date +%Y%m%d-%H%M%S).tar.gz \
  morse-whisperer-pi \
  /etc/systemd/system/morse-whisperer.service \
  /etc/systemd/system/morse-whisperer-buttons.service \
  /etc/polkit-1/rules.d/49-morse-whisperer-networkmanager.rules \
  /boot/firmware/config.txt
```

Copy it off the Pi:

```powershell
scp decoder@<pi-ip>:/home/decoder/morse-whisperer-known-good-*.tar.gz .
```

Do not publish NetworkManager connection profiles or Wi-Fi PSKs to a public repo.
