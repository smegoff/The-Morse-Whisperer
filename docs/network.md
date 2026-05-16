# Network and Wi-Fi

The web UI can scan and join Wi-Fi using NetworkManager. A Polkit rule allows only the `morsewhisperer` service user to perform the required NetworkManager actions.

Safety note: changing Wi-Fi can disconnect your browser or SSH session. Plug in Ethernet before changing Wi-Fi when possible.

Useful commands:

```bash
nmcli device status
nmcli connection show
ip -br addr
```
