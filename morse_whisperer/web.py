from __future__ import annotations

import json
import math
import os
import subprocess
import tempfile
import time
import wave
from pathlib import Path
from typing import Dict

import numpy as np
from flask import Flask, jsonify, request, send_from_directory

from .config import DEFAULT_CONFIG_PATH, save_config

APP_DIR = Path('/opt/morse-whisperer-pi')

HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Morse Whisperer</title>
<style>
:root{--bg:#02070b;--card:#071824;--line:rgba(66,248,255,.26);--cyan:#42f8ff;--teal:#5eead4;--orange:#ffb02e;--text:#eefcff;--muted:#93aaba;--bad:#ff5f72;--green:#68ff9f;--radius:18px}*{box-sizing:border-box}body{margin:0;min-height:100vh;color:var(--text);background:radial-gradient(circle at 68% 0%,rgba(66,248,255,.13),transparent 24rem),radial-gradient(circle at 18% 20%,rgba(255,176,46,.08),transparent 24rem),linear-gradient(135deg,#02070b,#06121b 42%,#070c18);font-family:Inter,ui-sans-serif,system-ui,Segoe UI,Roboto,sans-serif}#wm{position:fixed;inset:0;z-index:0;pointer-events:none;background-image:radial-gradient(circle at 50% 54%,rgba(66,248,255,.18),transparent 38%),radial-gradient(circle at 52% 64%,rgba(255,176,46,.13),transparent 42%),url('/assets/horse_boot_splash.png');background-position:center 52%,center 58%,center 48%;background-repeat:no-repeat;background-size:min(106vw,1180px) min(79vw,885px),min(96vw,1040px) min(72vw,780px),min(88vw,940px) auto;opacity:.42;filter:saturate(1.45) contrast(1.14) brightness(1.12);mix-blend-mode:screen}#wm:after{content:"";position:absolute;inset:0;background:radial-gradient(circle at 50% 50%,rgba(2,7,11,.04),rgba(2,7,11,.36) 58%,rgba(2,7,11,.78) 100%),linear-gradient(90deg,rgba(2,7,11,.72),rgba(2,7,11,.10) 46%,rgba(2,7,11,.72))}.app{position:relative;z-index:2;width:min(1600px,100%);margin:0 auto;padding:24px}.top{display:flex;justify-content:space-between;gap:16px;align-items:center}.brand{display:flex;gap:14px;align-items:center}.logo{width:48px;height:48px;border-radius:16px;display:grid;place-items:center;background:linear-gradient(135deg,var(--teal),#35b7ff);color:#031017;font-weight:900;box-shadow:0 0 24px rgba(66,248,255,.35)}h1{font-size:clamp(30px,3vw,46px);margin:0;line-height:1;text-shadow:0 0 20px rgba(66,248,255,.38)}.sub,.hint,.muted,small{color:var(--muted)}.badges{display:flex;gap:8px;flex-wrap:wrap}.badge,.pill{background:rgba(2,10,16,.78);border:1px solid rgba(66,248,255,.24);border-radius:999px;padding:7px 11px;font-size:12px}.grid{display:grid;grid-template-columns:1fr 420px;gap:16px;margin-top:18px}.card{background:linear-gradient(180deg,rgba(10,28,42,.90),rgba(3,12,20,.94));border:1px solid var(--line);border-radius:var(--radius);box-shadow:0 20px 48px rgba(0,0,0,.34),0 0 28px rgba(66,248,255,.055);padding:18px;overflow:hidden}.copy{font-size:clamp(42px,6vw,76px);font-weight:900;color:#b9c7d8;min-height:110px;display:flex;align-items:center}.raw{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:18px;min-height:70px}.side{display:grid;gap:14px}.meters .row{display:grid;grid-template-columns:90px 1fr 70px;gap:8px;align-items:center;margin:9px 0}.bar{height:8px;background:#06111a;border:1px solid rgba(66,248,255,.18);border-radius:99px;overflow:hidden}.bar span{display:block;height:100%;background:linear-gradient(90deg,var(--teal),var(--orange));box-shadow:0 0 14px rgba(255,176,46,.2)}button{border:1px solid rgba(66,248,255,.25);border-radius:11px;background:linear-gradient(180deg,rgba(22,45,62,.92),rgba(6,20,31,.96));color:var(--text);padding:11px 14px;font-weight:800;cursor:pointer}button.primary,.tab.active{background:linear-gradient(135deg,#5eead4,#43d9ff,#189dff);color:#031017;border-color:rgba(160,255,255,.86)}button:disabled{opacity:.45;cursor:not-allowed}.tabs{display:flex;gap:8px;margin:12px 0 18px}.panel{display:none}.panel.active{display:block}.settings{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.setting{background:linear-gradient(180deg,rgba(5,17,27,.62),rgba(3,10,17,.70));border:1px solid rgba(66,248,255,.16);border-radius:16px;padding:14px}label{display:block;text-transform:uppercase;letter-spacing:.08em;color:#d8f9ff;font-size:12px;margin-bottom:8px}input,select,textarea{width:100%;background:#030c13;color:var(--text);border:1px solid rgba(66,248,255,.28);border-radius:10px;padding:11px}input[type=range]{accent-color:var(--teal)}.preview{width:210px;max-width:100%;border-radius:14px;border:1px solid rgba(66,248,255,.34);box-shadow:0 16px 34px rgba(0,0,0,.42),0 0 30px rgba(66,248,255,.12)}.two{display:grid;grid-template-columns:1fr 1fr;gap:16px}.log{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:12px;white-space:pre-wrap}.network-row{display:grid;grid-template-columns:1fr 1fr auto;gap:10px}.footergrid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px}@media(max-width:1000px){.grid,.two,.footergrid{grid-template-columns:1fr}.settings{grid-template-columns:1fr}.badges{justify-content:flex-start}}
</style>
</head><body><div id="wm"></div><div class="app"><div class="top"><div class="brand"><div class="logo">MW</div><div><h1>The Morse Whisperer</h1><div class="sub">CW decoder appliance · Raspberry Pi live receiver</div></div></div><div class="badges"><span class="badge" id="runBadge">● running</span><span class="badge" id="updated">Updated --</span><span class="badge" id="device">Device --</span><span class="badge" id="squelch">Squelch --</span></div></div><div class="grid"><main><section class="card"><b>Stable COPY</b><div class="copy" id="copy">Waiting for CW...</div></section><section class="card" style="margin-top:14px"><b>Stable RAW</b><div class="raw" id="raw">No accepted raw copy yet.</div></section></main><aside class="side"><section class="card"><b>Tone Lock</b><div style="font-size:50px;font-weight:900;margin-top:25px"><span id="tone">--</span> <small>Hz</small></div><small id="toneReason">none</small></section><section class="card meters"><b>Signal Quality</b><div class="row"><small>SNR</small><div class="bar"><span id="snrBar"></span></div><small id="snrVal">--</small></div><div class="row"><small>Confidence</small><div class="bar"><span id="confBar"></span></div><small id="confVal">--</small></div><div class="row"><small>RMS</small><div class="bar"><span id="rmsBar"></span></div><small id="rmsVal">--</small></div></section><section class="card"><b>Operator Controls</b><p><button class="primary" onclick="resetCopy()">Reset copy / buffer</button> <button onclick="copyTxt()">Copy TXT</button> <button onclick="fetch('/api/snapshot').then(r=>r.json()).then(j=>navigator.clipboard.writeText(JSON.stringify(j,null,2)))">Copy JSON</button></p></section></aside></div><section class="card" style="margin-top:18px"><b>Morse Controls</b><div class="tabs"><button class="tab active" onclick="tab('settings',this)">Settings</button><button class="tab" onclick="tab('trainer',this)">CW Generator / Trainer</button><button class="tab" onclick="tab('network',this)">Network Setup</button></div><div id="settings" class="panel active"><div class="settings"><div class="setting"><label>Decoder mode</label><select id="setToneMode"><option value="session_auto">Full auto — recommended</option><option value="fixed">Fixed tone</option></select><div class="hint">Full auto scans for CW tone at start of session.</div></div><div class="setting"><label>Tone Hz</label><input id="setTone" type="number"></div><div class="setting"><label>WPM hint</label><input id="setWpm" type="number" step="0.25"></div><div class="setting"><label>Input level %</label><input id="setInput" type="range" min="0" max="100"><div class="hint"><span id="setInputVal">--</span>% · ALSA capture attempt</div></div><div class="setting"><label>TFT brightness %</label><input id="setBright" type="range" min="10" max="100"><div class="hint"><span id="setBrightVal">--</span>% · software dimming</div></div><div class="setting"><label>TFT idle splash</label><select id="setIdle"><option value="true">Enabled</option><option value="false">Disabled</option></select><div class="hint">Shows splash after no CW or button activity.</div><img class="preview" src="/assets/horse_boot_splash.png"></div><div class="setting"><label>TFT idle timeout</label><input id="setIdleSec" type="number" min="15" max="3600" step="15"><div class="hint">300 = five minutes.</div></div><div class="setting"><label>USB speaker output</label><input id="setOut" placeholder="plughw:2,0"></div></div><p><button class="primary" onclick="saveSettings()">Save settings</button> <button onclick="loadSettings()">Reload</button></p></div><div id="trainer" class="panel"><div class="settings"><div class="setting"><label>Training text</label><textarea id="cwText" rows="5">VVV THE MORSE WHISPERER TEST 73</textarea></div><div class="setting"><label>Character speed WPM</label><input id="cwWpm" type="number" step="0.25"></div><div class="setting"><label>Pitch Hz</label><input id="cwTone" type="number"></div><div class="setting"><label>Volume %</label><input id="cwVol" type="range" min="5" max="95"><div class="hint"><span id="cwVolVal">--</span>% output level</div></div></div><p><button class="primary" onclick="playCw()">Play CW</button> <button onclick="stopCw()">Stop CW</button> <button onclick="selfTest()">Generate + Decode</button></p><pre class="log" id="selftest">Self-test decode has not been run yet.</pre></div><div id="network" class="panel"><div class="two"><div class="card"><b>Current network status</b><pre class="log" id="netStatus">Press refresh.</pre><button class="primary" onclick="netStatus()">Refresh status</button> <button onclick="wifiScan()">Scan Wi-Fi</button></div><div class="card"><b>Nearby Wi-Fi networks</b><pre class="log" id="wifiList">Press Scan Wi-Fi.</pre></div></div><div class="card" style="margin-top:12px"><b>Join Wi-Fi network</b><p class="hint">Changing Wi-Fi can disconnect this browser or SSH session. Plug in Ethernet first if possible.</p><div class="network-row"><input id="ssid" placeholder="SSID"><input id="psk" placeholder="Password / PSK"><button class="primary" onclick="wifiConnect()">Connect Wi-Fi</button></div><pre class="log" id="wifiResult"></pre></div></div></section><div class="footergrid"><section class="card"><b>Current Signal</b><pre class="log" id="current">--</pre></section><section class="card"><b>Tone Ranking</b><div id="ranking"></div></section><section class="card"><b>Decode History</b><pre class="log" id="history">--</pre></section><section class="card"><b>Status Log</b><pre class="log" id="status">--</pre></section></div></div><script>
function $(id){return document.getElementById(id)}
function pct(x,max){return Math.max(0,Math.min(100,100*(Number(x)||0)/max))+'%'}
function tab(id,b){document.querySelectorAll('.panel').forEach(x=>x.classList.remove('active'));document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));$(id).classList.add('active');b.classList.add('active')}
async function snap(){const s=await fetch('/api/snapshot?ts='+Date.now(),{cache:'no-store'}).then(r=>r.json());const q=s.quality||{},d=s.decode||{},a=s.audio||{};$('updated').textContent='Updated '+Math.max(0,((Date.now()/1000)-(s.updated_at||0))).toFixed(1)+'s ago';$('device').textContent='Device '+((s.config||{}).audio_device||'--');$('squelch').textContent='Squelch '+(q.snr_db>3?'open':'closed');$('copy').textContent=d.copy||'Waiting for CW...';$('raw').textContent=d.raw||'No accepted raw copy yet.';$('tone').textContent=q.selected_tone_hz||'--';$('toneReason').textContent=q.reason||'none';$('snrVal').textContent=(q.snr_db||0).toFixed(1)+' dB';$('confVal').textContent=(q.confidence||0).toFixed(2);$('rmsVal').textContent=(a.rms||0).toFixed(3);$('snrBar').style.width=pct(q.snr_db,30);$('confBar').style.width=pct(q.confidence,1);$('rmsBar').style.width=pct(a.rms,.05);$('current').textContent=`Selected tone      ${q.selected_tone_hz||'--'} Hz\nFallback target    ${q.target_tone_hz||'--'} Hz\nWPM estimate       ${(q.wpm||0).toFixed(1)}\nReason             ${q.reason||'--'}\nBuffer             ${((s.audio_buffer||{}).buffered_seconds||0).toFixed(1)}s`; $('status').textContent=(s.status_log||[]).join('\n'); $('history').textContent=(s.decode_history||[]).map(x=>new Date(x.ts*1000).toLocaleTimeString()+' '+x.copy).join('\n')||'No accepted decode history yet.'; $('ranking').innerHTML=(q.tone_ranking||[]).map(r=>`<div class="meters row"><b>${r.tone_hz} Hz</b><div class="bar"><span style="width:${pct(r.score,(q.tone_ranking||[{score:1}])[0].score||1)}"></span></div><small>${Number(r.score).toExponential(2)}</small></div>`).join('')}
async function loadSettings(){const j=await fetch('/api/settings').then(r=>r.json());const c=j.config||j;$('setToneMode').value=c.tone_mode||'session_auto';$('setTone').value=c.target_tone_hz||700;$('setWpm').value=c.initial_wpm||18.75;$('setInput').value=c.input_capture_percent??70;$('setInputVal').textContent=$('setInput').value;$('setBright').value=c.lcd_brightness_percent??100;$('setBrightVal').textContent=$('setBright').value;$('setIdle').value=String(c.tft_screen_timeout_enabled!==false);$('setIdleSec').value=c.tft_screen_timeout_sec||300;$('setOut').value=c.audio_output_device||'plughw:2,0';$('cwTone').value=c.cw_generator_tone_hz||700;$('cwWpm').value=c.cw_generator_wpm||18.75;$('cwVol').value=c.cw_generator_volume_percent??35;$('cwVolVal').textContent=$('cwVol').value}
['setInput','setBright','cwVol'].forEach(id=>document.addEventListener('input',e=>{if(e.target.id==id)$(id+(id=='cwVol'?'Val':id=='setInput'?'Val':'Val')).textContent=e.target.value}))
async function saveSettings(){const p={tone_mode:$('setToneMode').value,target_tone_hz:Number($('setTone').value),initial_wpm:Number($('setWpm').value),input_capture_percent:Number($('setInput').value),lcd_brightness_percent:Number($('setBright').value),tft_screen_timeout_enabled:$('setIdle').value==='true',tft_screen_timeout_sec:Number($('setIdleSec').value||300),audio_output_device:$('setOut').value,cw_generator_tone_hz:Number($('cwTone').value),cw_generator_wpm:Number($('cwWpm').value),cw_generator_volume_percent:Number($('cwVol').value)};alert(JSON.stringify(await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)}).then(r=>r.json())))}
async function resetCopy(){await fetch('/api/reset',{method:'POST'});snap()}function copyTxt(){navigator.clipboard.writeText($('copy').textContent)}async function playCw(){await fetch('/api/cw/play',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:$('cwText').value,tone_hz:Number($('cwTone').value),wpm:Number($('cwWpm').value),volume_percent:Number($('cwVol').value)})})}async function stopCw(){await fetch('/api/cw/stop',{method:'POST'})}async function selfTest(){const r=await fetch('/api/cw/selftest',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:$('cwText').value,tone_hz:Number($('cwTone').value),wpm:Number($('cwWpm').value)})}).then(r=>r.json());$('selftest').textContent=JSON.stringify(r,null,2)}async function netStatus(){$('netStatus').textContent=JSON.stringify(await fetch('/api/network/status').then(r=>r.json()),null,2)}async function wifiScan(){const r=await fetch('/api/network/scan').then(r=>r.json());$('wifiList').textContent=(r.networks||[]).map(n=>`${n.ssid}  ${n.signal}%  ${n.security}`).join('\n')||JSON.stringify(r,null,2)}async function wifiConnect(){const r=await fetch('/api/network/connect',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ssid:$('ssid').value,psk:$('psk').value})}).then(r=>r.json());$('wifiResult').textContent=JSON.stringify(r,null,2)}
loadSettings();netStatus();snap();setInterval(snap,1000);
</script></body></html>'''


def create_app(state, config: Dict) -> Flask:
    app = Flask(__name__)

    @app.route('/')
    def index():
        return HTML

    @app.route('/assets/<path:filename>')
    def assets(filename):
        return send_from_directory(str(APP_DIR / 'assets'), filename)

    @app.route('/api/snapshot')
    def snapshot():
        return jsonify(state.snapshot())

    @app.route('/api/settings', methods=['GET', 'POST'])
    def settings():
        if request.method == 'GET':
            return jsonify({'ok': True, 'config': config})
        data = request.get_json(force=True) or {}
        allow = {'tone_mode':str,'target_tone_hz':int,'initial_wpm':float,'input_capture_percent':int,'lcd_brightness_percent':int,'tft_screen_timeout_enabled':bool,'tft_screen_timeout_sec':int,'audio_output_device':str,'cw_generator_tone_hz':int,'cw_generator_wpm':float,'cw_generator_volume_percent':int}
        changed = {}
        for k, typ in allow.items():
            if k in data:
                try:
                    config[k] = typ(data[k])
                    changed[k] = config[k]
                except Exception:
                    pass
        save_config(config)
        state.merge(config=config)
        return jsonify({'ok': True, 'changed': changed})

    @app.route('/api/reset', methods=['POST'])
    def reset():
        state.merge(decode={}, decode_history=[])
        state.append_status('Manual copy/buffer reset')
        return jsonify({'ok': True})

    @app.route('/api/decode/history')
    def history():
        return jsonify({'ok': True, 'history': state.snapshot().get('decode_history', [])})

    @app.route('/api/cw/play', methods=['POST'])
    def cw_play():
        data = request.get_json(force=True) or {}
        text = str(data.get('text') or 'VVV THE MORSE WHISPERER TEST 73')
        tone = int(data.get('tone_hz') or config.get('cw_generator_tone_hz') or 700)
        wpm = float(data.get('wpm') or config.get('cw_generator_wpm') or 18.75)
        vol = int(data.get('volume_percent') or config.get('cw_generator_volume_percent') or 35)
        out = str(config.get('audio_output_device') or 'plughw:2,0')
        wav = _make_cw_wav(text, tone, wpm, vol)
        subprocess.Popen(['aplay','-q','-D',out,wav])
        return jsonify({'ok': True, 'device': out, 'text': text})

    @app.route('/api/cw/stop', methods=['POST'])
    def cw_stop():
        subprocess.run(['pkill','-f','aplay -q -D'], check=False)
        return jsonify({'ok': True})

    @app.route('/api/cw/selftest', methods=['POST'])
    def cw_selftest():
        data = request.get_json(force=True) or {}
        text = str(data.get('text') or 'VVV THE MORSE WHISPERER TEST 73')
        return jsonify({'ok': True, 'input': text, 'note': 'Self-test generation is available. Use Play CW to send audio through the configured USB output.'})

    @app.route('/api/network/status')
    def net_status():
        return jsonify(_run_helper({'action': 'status'}))

    @app.route('/api/network/scan')
    def net_scan():
        return jsonify(_run_helper({'action': 'scan'}))

    @app.route('/api/network/connect', methods=['POST'])
    def net_connect():
        data = request.get_json(force=True) or {}
        return jsonify(_run_helper({'action': 'connect', 'ssid': data.get('ssid',''), 'psk': data.get('psk','')}))

    return app


def _run_helper(payload: Dict) -> Dict:
    helper = APP_DIR / 'tools' / 'network_connect_helper.py'
    cp = subprocess.run([str(helper)], input=json.dumps(payload), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    try:
        return json.loads(cp.stdout or '{}')
    except Exception:
        return {'ok': False, 'stdout': cp.stdout, 'stderr': cp.stderr, 'returncode': cp.returncode}


def _make_cw_wav(text: str, tone: int, wpm: float, volume: int) -> str:
    table = {'A':'.-','B':'-...','C':'-.-.','D':'-..','E':'.','F':'..-.','G':'--.','H':'....','I':'..','J':'.---','K':'-.-','L':'.-..','M':'--','N':'-.','O':'---','P':'.--.','Q':'--.-','R':'.-.','S':'...','T':'-','U':'..-','V':'...-','W':'.--','X':'-..-','Y':'-.--','Z':'--..','1':'.----','2':'..---','3':'...--','4':'....-','5':'.....','6':'-....','7':'--...','8':'---..','9':'----.','0':'-----'}
    sr = 48000
    dot = 1.2 / max(wpm, 1.0)
    amp = max(0.01, min(0.95, volume / 100.0)) * 24000
    samples = []
    def add_t(sec, on):
        n = int(sr * sec)
        start = len(samples)
        for i in range(n):
            if on:
                # raised cosine edges
                edge = min(1.0, i/(sr*0.005+1), (n-i)/(sr*0.005+1))
                samples.append(int(math.sin(2*math.pi*tone*(start+i)/sr) * amp * edge))
            else:
                samples.append(0)
    for word in text.upper().split():
        for ch in word:
            code = table.get(ch)
            if not code: continue
            for sym in code:
                add_t(dot * (3 if sym == '-' else 1), True); add_t(dot, False)
            add_t(dot*2, False)
        add_t(dot*4, False)
    fd, path = tempfile.mkstemp(prefix='mw-cw-', suffix='.wav')
    os.close(fd)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(np.asarray(samples, dtype='<i2').tobytes())
    return path
