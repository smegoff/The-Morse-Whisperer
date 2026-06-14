# Installation and One-Shot Rebuild

## One-shot install

From a cloned or extracted repository:

```bash
sudo ./install.sh
```

Do not pipe only `install.sh` from GitHub into a shell. The installer requires
the rest of the repository beside it.

The installer:

- installs required apt packages
- creates the `morsewhisperer` service user if needed
- copies the application into `/opt/morse-whisperer-pi`
- creates a Python virtual environment
- installs Python dependencies
- installs systemd services
- installs NetworkManager polkit permissions for Wi-Fi setup
- installs profile-switch polkit permissions so the web UI can restart only `morse-whisperer.service`
- validates Python files
- enables and starts the main and button services
- preserves an existing `/opt/morse-whisperer-pi/config.json` during rebuilds

## Services

Main service:

```bash
sudo systemctl status morse-whisperer.service --no-pager -l
sudo systemctl restart morse-whisperer.service
```

Button sidecar:

```bash
sudo systemctl status morse-whisperer-buttons.service --no-pager -l
```

Optional fallback hotspot service:

```bash
sudo systemctl enable --now morse-whisperer-network-fallback.service
```

## Permissions

The application directory is owned by `root:morsewhisperer`.

`config.json` and the runtime profile backup directory are writable by the `morsewhisperer` group so the web profile switch can save profile changes.

The committed `config.json` is the clean baseline for a fresh appliance. A
working appliance normally has local changes in this file for its selected
profile, capture gain, callsign, and other machine settings.

## Network boundary

The Flask UI binds to `0.0.0.0:8080` by default and has no authentication.
Operate it on a trusted LAN only. Do not expose port 8080 directly to the
internet.

## Web profile restart permission

The installer creates:

```text
/etc/polkit-1/rules.d/49-morse-whisperer-profile-restart.rules
```

This permits the `morsewhisperer` group to manage only:

```text
morse-whisperer.service
```

Allowed verbs:

```text
restart
start
stop
```

This is required so the web UI profile switch can restart the decoder and reload the selected profile.
