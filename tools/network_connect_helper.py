#!/usr/bin/env python3
import json
import subprocess
import sys
import time


def run(cmd, timeout=30):
    cp = subprocess.run(
        cmd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
    )
    return {
        "ok": cp.returncode == 0,
        "returncode": cp.returncode,
        "stdout": cp.stdout.strip(),
        "stderr": cp.stderr.strip(),
        "cmd": " ".join(cmd[:4]) + (" ..." if len(cmd) > 4 else ""),
    }


def nmcli_lines(args, timeout=15):
    res = run(["nmcli"] + args, timeout=timeout)
    if not res["ok"] and not res["stdout"]:
        return []
    return [line for line in res["stdout"].splitlines() if line.strip()]


def split_nmcli(line):
    parts = []
    cur = ""
    esc = False
    for ch in str(line):
        if esc:
            cur += ch
            esc = False
        elif ch == "\\":
            esc = True
        elif ch == ":":
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return parts


def first_wifi_device():
    for line in nmcli_lines(["-t", "-f", "DEVICE,TYPE", "device", "status"]):
        parts = split_nmcli(line)
        while len(parts) < 2:
            parts.append("")
        if parts[1] == "wifi" and parts[0] != "p2p-dev-wlan0":
            return parts[0]
    return ""


def active_wifi_connection(iface):
    for line in nmcli_lines(["-t", "-f", "NAME,DEVICE", "connection", "show", "--active"]):
        parts = split_nmcli(line)
        while len(parts) < 2:
            parts.append("")
        if parts[1] == iface:
            return parts[0]
    return ""


def connection_exists(name):
    for line in nmcli_lines(["-t", "-f", "NAME", "connection", "show"]):
        if split_nmcli(line)[0] == name:
            return True
    return False


def ip_addresses():
    res = run(["hostname", "-I"], timeout=8)
    return [x for x in (res["stdout"] or "").split() if x]


def has_default_route():
    return run(["sh", "-c", "ip route show default | grep -q '^default '"], timeout=8)["ok"]


def visible_ssids(iface):
    run(["nmcli", "device", "wifi", "rescan", "ifname", iface], timeout=20)
    time.sleep(5)

    ssids = []
    for line in nmcli_lines(["-t", "-f", "SSID,SIGNAL,SECURITY,CHAN", "device", "wifi", "list", "ifname", iface], timeout=20):
        parts = split_nmcli(line)
        while len(parts) < 4:
            parts.append("")
        ssids.append({
            "ssid": parts[0],
            "signal": parts[1],
            "security": parts[2] or "open",
            "channel": parts[3],
        })
    return ssids


def safe_connection_name(ssid):
    return ssid.strip() or "morse-whisperer-wifi"


def create_or_update_profile(iface, ssid, password):
    con_name = safe_connection_name(ssid)

    if not connection_exists(con_name):
        add = run([
            "nmcli", "connection", "add",
            "type", "wifi",
            "ifname", iface,
            "con-name", con_name,
            "ssid", ssid,
        ], timeout=20)

        if not add["ok"]:
            return con_name, add

    base = [
        "nmcli", "connection", "modify", con_name,
        "connection.autoconnect", "yes",
        "802-11-wireless.ssid", ssid,
        "802-11-wireless.mode", "infrastructure",
        "ipv4.method", "auto",
        "ipv6.method", "auto",
    ]

    if password:
        base.extend([
            "802-11-wireless-security.key-mgmt", "wpa-psk",
            "802-11-wireless-security.psk", password,
        ])
    else:
        base.extend([
            "802-11-wireless-security.key-mgmt", "",
            "802-11-wireless-security.psk", "",
        ])

    mod = run(base, timeout=20)
    return con_name, mod


def main():
    try:
        data = json.loads(sys.stdin.read() or "{}")
        ssid = str(data.get("ssid") or "").strip()
        password = str(data.get("password") or "")

        if not ssid:
            print(json.dumps({"ok": False, "error": "SSID is required"}))
            return 2

        iface = first_wifi_device()
        if not iface:
            print(json.dumps({"ok": False, "error": "No Wi-Fi device found"}))
            return 3

        old_conn = active_wifi_connection(iface)
        seen = visible_ssids(iface)
        matching = [x for x in seen if x.get("ssid") == ssid]

        con_name, profile = create_or_update_profile(iface, ssid, password)
        if not profile["ok"]:
            print(json.dumps({
                "ok": False,
                "error": profile.get("stderr") or profile.get("stdout") or "Failed to create/update Wi-Fi profile",
                "returncode": profile.get("returncode"),
                "ssid": ssid,
                "connection_name": con_name,
                "wifi_device": iface,
                "old_connection": old_conn,
                "seen_matching_ssids": matching,
                "visible_ssid_count": len(seen),
            }))
            return 4

        connect = run(["nmcli", "--wait", "40", "connection", "up", con_name], timeout=55)

        time.sleep(4)

        route_ok = has_default_route()
        ips = ip_addresses()

        if not connect["ok"] or not route_ok:
            rollback_attempted = False
            rollback_ok = False
            rollback_error = ""

            if old_conn:
                rollback_attempted = True
                rb = run(["nmcli", "--wait", "30", "connection", "up", old_conn], timeout=45)
                rollback_ok = bool(rb["ok"])
                rollback_error = rb.get("stderr") or rb.get("stdout") or ""

            print(json.dumps({
                "ok": False,
                "error": connect.get("stderr") or connect.get("stdout") or "Connection failed",
                "returncode": connect.get("returncode"),
                "ssid": ssid,
                "connection_name": con_name,
                "wifi_device": iface,
                "old_connection": old_conn,
                "rollback_attempted": rollback_attempted,
                "rollback_ok": rollback_ok,
                "rollback_error": rollback_error,
                "ip_addresses": ips,
                "seen_matching_ssids": matching,
                "visible_ssid_count": len(seen),
            }))
            return 10

        run(["nmcli", "device", "wifi", "rescan", "ifname", iface], timeout=20)

        print(json.dumps({
            "ok": True,
            "ssid": ssid,
            "connection_name": con_name,
            "wifi_device": iface,
            "old_connection": old_conn,
            "ip_addresses": ips,
            "stdout": connect.get("stdout"),
            "seen_matching_ssids": matching,
            "visible_ssid_count": len(seen),
        }))
        return 0

    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
