#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys


def run(cmd, timeout=30):
    cp = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout, check=False)
    return {'ok': cp.returncode == 0, 'returncode': cp.returncode, 'stdout': cp.stdout.strip(), 'stderr': cp.stderr.strip(), 'cmd': ' '.join(cmd)}


def lines(args):
    r = run(['nmcli'] + args, timeout=20)
    return [x for x in r.get('stdout','').splitlines() if x.strip()]


def split(line):
    out=[]; cur=''; esc=False
    for ch in line:
        if esc: cur+=ch; esc=False
        elif ch=='\\': esc=True
        elif ch==':': out.append(cur); cur=''
        else: cur+=ch
    out.append(cur)
    return out


def status():
    devs = lines(['-t','-f','DEVICE,TYPE,STATE,CONNECTION','device','status'])
    conns = lines(['-t','-f','NAME,TYPE,DEVICE,AUTOCONNECT','connection','show'])
    ip = run(['hostname','-I'])['stdout']
    route = run(['sh','-c','ip route | sed -n 1p'])['stdout']
    wifi = ''
    for l in devs:
        p=split(l)+['','','','']
        if p[1]=='wifi' and p[0] != 'p2p-dev-wlan0': wifi=p[0]
    return {'ok': True, 'hostname': run(['hostname'])['stdout'], 'ip_addresses': ip.split(), 'default_route': route, 'wifi_device': wifi, 'devices': devs, 'connections': conns}


def scan():
    dev = status().get('wifi_device') or 'wlan0'
    run(['nmcli','device','wifi','rescan','ifname',dev], timeout=20)
    nets=[]
    for l in lines(['-t','-f','SSID,SIGNAL,SECURITY','device','wifi','list','ifname',dev]):
        p=split(l)+['','','']
        if p[0]: nets.append({'ssid': p[0], 'signal': p[1], 'security': p[2]})
    return {'ok': True, 'networks': nets}


def connect(ssid, psk):
    if not ssid: return {'ok': False, 'error': 'SSID is required'}
    dev = status().get('wifi_device') or 'wlan0'
    cmd = ['nmcli','device','wifi','connect',ssid,'ifname',dev]
    if psk: cmd += ['password', psk]
    r = run(cmd, timeout=60)
    r['ip_addresses'] = status().get('ip_addresses', [])
    return r


def main():
    data=json.loads(sys.stdin.read() or '{}')
    action=data.get('action')
    if action=='status': print(json.dumps(status()))
    elif action=='scan': print(json.dumps(scan()))
    elif action=='connect': print(json.dumps(connect(data.get('ssid',''), data.get('psk',''))))
    else: print(json.dumps({'ok': False, 'error': 'unknown action'}))

if __name__ == '__main__': main()
