from __future__ import annotations

import json
import math
import os
import random
import struct
import subprocess
import tempfile
import time
import wave

import numpy as np
from pathlib import Path
from typing import Dict

from flask import Flask, Response, jsonify, request, send_from_directory
from .ai import install_ai_routes

from .config import DEFAULTS, save_config
from .dsp import analyse_samples

HTML = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="cache-control" content="no-store">
<title>The Morse Whisperer</title>
<style>
:root{
  --bg:#070b10;
  --panel:#101821;
  --panel2:#15202b;
  --panel3:#0d141c;
  --line:#263746;
  --line2:#3a4d60;
  --text:#edf4ff;
  --muted:#91a2b4;
  --muted2:#6f8091;
  --good:#54f28f;
  --warn:#ffd166;
  --bad:#ff6b6b;
  --blue:#70b7ff;
  --violet:#b69cff;
  --shadow:0 18px 50px rgba(0,0,0,.38);
  --radius:18px;
}
*{box-sizing:border-box}
body{
  margin:0;
  min-height:100vh;
  color:var(--text);
  background:
    radial-gradient(circle at 20% 0%, rgba(112,183,255,.12), transparent 35%),
    radial-gradient(circle at 90% 10%, rgba(182,156,255,.10), transparent 30%),
    linear-gradient(180deg,#071019 0%,#05080c 100%);
  font-family:Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
.app{
  width:min(1760px,100%);
  margin:0 auto;
  padding:22px;
}
.topbar{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:16px;
  margin-bottom:18px;
}
.brand{
  display:flex;
  align-items:center;
  gap:14px;
}
.logo{
  width:48px;
  height:48px;
  border-radius:16px;
  display:grid;
  place-items:center;
  color:#061018;
  font-weight:900;
  letter-spacing:-2px;
  background:linear-gradient(135deg,var(--good),var(--blue));
  box-shadow:0 0 28px rgba(84,242,143,.25);
}
.title h1{
  margin:0;
  font-size:clamp(28px,3vw,44px);
  letter-spacing:-.045em;
  line-height:1;
}
.title .sub{
  margin-top:7px;
  color:var(--muted);
  font-size:14px;
}
.statusPills{
  display:flex;
  flex-wrap:wrap;
  justify-content:flex-end;
  gap:8px;
}
.pill{
  display:inline-flex;
  align-items:center;
  gap:8px;
  border:1px solid var(--line);
  background:rgba(16,24,33,.78);
  border-radius:999px;
  padding:8px 12px;
  color:var(--muted);
  font-size:13px;
}
.dot{
  width:9px;
  height:9px;
  border-radius:999px;
  background:var(--muted2);
  box-shadow:0 0 0 rgba(0,0,0,0);
}
.dot.good{background:var(--good);box-shadow:0 0 18px rgba(84,242,143,.55)}
.dot.warn{background:var(--warn);box-shadow:0 0 18px rgba(255,209,102,.55)}
.dot.bad{background:var(--bad);box-shadow:0 0 18px rgba(255,107,107,.55)}
.grid{
  display:grid;
  grid-template-columns:1.35fr .65fr;
  gap:16px;
}
.card{
  background:linear-gradient(180deg,rgba(21,32,43,.96),rgba(13,20,28,.96));
  border:1px solid var(--line);
  border-radius:var(--radius);
  box-shadow:var(--shadow);
}
.cardHead{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:12px;
  padding:16px 18px 0;
}
.cardHead h2,.cardHead h3{
  margin:0;
  letter-spacing:-.02em;
}
.cardHead h2{font-size:18px}
.cardHead h3{font-size:16px}
.cardBody{padding:16px 18px 18px}
.copyBox{
  min-height:188px;
  display:flex;
  align-items:center;
}
.copyText{
  width:100%;
  font-size:clamp(36px,5.5vw,86px);
  line-height:1.08;
  letter-spacing:-.035em;
  font-weight:760;
  white-space:pre-wrap;
  word-break:break-word;
}
.copyText.empty{
  color:var(--muted2);
  font-weight:650;
}
.rawText{
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:clamp(15px,1.3vw,20px);
  color:#d9e7f5;
  min-height:70px;
  white-space:pre-wrap;
  word-break:break-word;
}
.sideGrid{
  display:grid;
  grid-template-columns:1fr;
  gap:16px;
}
.metricGrid{
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:10px;
}
.metric{
  background:rgba(7,11,16,.42);
  border:1px solid rgba(58,77,96,.65);
  border-radius:14px;
  padding:12px;
}
.metric .label{
  color:var(--muted);
  font-size:12px;
  text-transform:uppercase;
  letter-spacing:.08em;
}
.metric .value{
  margin-top:6px;
  font-size:22px;
  font-weight:800;
  letter-spacing:-.03em;
}
.value.good{color:var(--good)}
.value.warn{color:var(--warn)}
.value.bad{color:var(--bad)}
.bigMetric{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:10px;
}
.toneHero{
  display:flex;
  align-items:baseline;
  gap:10px;
}
.toneHero .tone{
  font-size:52px;
  font-weight:900;
  letter-spacing:-.06em;
}
.toneHero .hz{
  color:var(--muted);
  font-size:20px;
  font-weight:700;
}
.barGroup{display:grid;gap:12px}
.barRow{
  display:grid;
  grid-template-columns:95px 1fr 58px;
  align-items:center;
  gap:10px;
  font-size:13px;
  color:var(--muted);
}
.barTrack{
  height:12px;
  border-radius:999px;
  background:#061018;
  border:1px solid rgba(58,77,96,.7);
  overflow:hidden;
}
.barFill{
  height:100%;
  width:0%;
  border-radius:999px;
  background:linear-gradient(90deg,var(--blue),var(--good));
}
.barFill.warn{background:linear-gradient(90deg,var(--warn),#ff9f1c)}
.barFill.bad{background:linear-gradient(90deg,var(--bad),#ff3b3b)}
.tones{
  display:grid;
  gap:8px;
}
.toneRow{
  display:grid;
  grid-template-columns:70px 1fr auto;
  align-items:center;
  gap:10px;
  color:var(--muted);
  font-size:13px;
}
.toneLabel{font-weight:800;color:#e8f1fb}
.toneMini{
  height:8px;
  border-radius:999px;
  background:#061018;
  border:1px solid rgba(58,77,96,.55);
  overflow:hidden;
}
.toneMini div{
  height:100%;
  width:0%;
  background:linear-gradient(90deg,var(--violet),var(--blue));
}
.controls{
  display:flex;
  flex-wrap:wrap;
  gap:10px;
}
button,.btn{
  appearance:none;
  border:1px solid var(--line2);
  background:linear-gradient(180deg,#243142,#172231);
  color:var(--text);
  padding:10px 13px;
  border-radius:12px;
  text-decoration:none;
  font:inherit;
  font-size:14px;
  cursor:pointer;
}
button:hover,.btn:hover{border-color:var(--blue)}
button.primary{
  background:linear-gradient(135deg,#2662ff,#14b8a6);
  border-color:rgba(112,183,255,.5);
}
.small{
  color:var(--muted);
  font-size:13px;
}
.statusLog{
  max-height:150px;
  overflow:auto;
  color:var(--muted);
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:12px;
  line-height:1.45;
}
.footerGrid{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:16px;
  margin-top:16px;
}
.badge{
  display:inline-flex;
  align-items:center;
  gap:6px;
  border-radius:999px;
  padding:5px 9px;
  font-size:12px;
  color:var(--muted);
  border:1px solid var(--line);
  background:rgba(7,11,16,.38);
}
.badge.good{color:var(--good);border-color:rgba(84,242,143,.35)}
.badge.warn{color:var(--warn);border-color:rgba(255,209,102,.35)}
.badge.bad{color:var(--bad);border-color:rgba(255,107,107,.35)}
.kv{
  display:grid;
  grid-template-columns:150px 1fr;
  gap:7px 12px;
  font-size:14px;
}
.kv div:nth-child(odd){color:var(--muted)}
.kv div:nth-child(even){font-weight:700}
.settingsGrid{
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:12px;
}
.setting{
  background:rgba(7,11,16,.42);
  border:1px solid rgba(58,77,96,.65);
  border-radius:14px;
  padding:12px;
}
.setting label{
  display:block;
  color:var(--muted);
  font-size:12px;
  text-transform:uppercase;
  letter-spacing:.08em;
  margin-bottom:7px;
}
.setting input,.setting select,.setting textarea{
  width:100%;
  border:1px solid var(--line2);
  background:#071019;
  color:var(--text);
  border-radius:10px;
  padding:9px 10px;
  font:inherit;
}
.setting textarea{
  min-height:72px;
  resize:vertical;
}
.setting .hint{
  margin-top:6px;
  color:var(--muted2);
  font-size:12px;
  line-height:1.35;
}
@media(max-width:1050px){
  .settingsGrid{grid-template-columns:1fr 1fr}
}
@media(max-width:650px){
  .settingsGrid{grid-template-columns:1fr}
}

.tabs{
  display:flex;
  flex-wrap:wrap;
  gap:8px;
  margin-bottom:14px;
}
.tabBtn{
  border:1px solid var(--line2);
  background:#101a26;
  color:var(--muted);
  border-radius:999px;
  padding:9px 13px;
  font-weight:750;
  cursor:pointer;
}
.tabBtn.active{
  color:#061018;
  border-color:transparent;
  background:linear-gradient(135deg,var(--good),var(--blue));
}
.tabPane{display:none}
.tabPane.active{display:block}
.generatorHero{
  display:grid;
  grid-template-columns:1fr 280px;
  gap:14px;
}
.generatorPreview{
  background:#071019;
  border:1px solid var(--line2);
  border-radius:14px;
  padding:12px;
  min-height:140px;
}
.morsePreview{
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  color:#d9e7f5;
  font-size:15px;
  line-height:1.55;
  word-break:break-word;
  white-space:pre-wrap;
}
@media(max-width:900px){
  .generatorHero{grid-template-columns:1fr}
}

.playbackModes{
  display:flex;
  flex-wrap:wrap;
  gap:10px;
  margin-bottom:14px;
}
.modeTile{
  min-width:96px;
  border:1px solid var(--line2);
  border-radius:14px;
  padding:12px;
  background:#071019;
  color:var(--muted);
  cursor:pointer;
  text-align:center;
  font-weight:800;
}
.modeTile.active{
  color:#061018;
  border-color:transparent;
  background:linear-gradient(135deg,var(--good),var(--blue));
}
.modeTile.disabled{
  opacity:.45;
  cursor:not-allowed;
}
.presetGrid{
  display:flex;
  flex-wrap:wrap;
  gap:8px;
  margin-top:8px;
}
.presetGrid button{
  padding:8px 10px;
}
.advancedTrainer{
  display:none;
  margin-top:12px;
}
.advancedTrainer.active{
  display:block;
}
.trainerSectionTitle{
  margin:2px 0 10px;
  color:var(--text);
  font-weight:850;
  letter-spacing:-.02em;
}

.selfTestResult{
  margin-top:12px;
  padding:12px;
  border:1px solid var(--line2);
  border-radius:14px;
  background:#071019;
  color:var(--muted);
}
.selfTestResult.good{border-color:rgba(84,242,143,.7);color:var(--text)}
.selfTestResult.warn{border-color:rgba(255,209,102,.7);color:var(--text)}
.selfTestResult.bad{border-color:rgba(255,107,107,.7);color:var(--text)}
.selfTestMono{
  margin-top:8px;
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  white-space:pre-wrap;
  word-break:break-word;
  color:#d9e7f5;
}

.networkGrid{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:12px;
}
.networkBox{
  border:1px solid var(--line2);
  border-radius:14px;
  background:#071019;
  padding:12px;
}
.networkBox h4{
  margin:0 0 10px;
  font-size:14px;
}
.networkList{
  display:grid;
  gap:7px;
}
.networkRow{
  display:grid;
  grid-template-columns:1.8fr .45fr .9fr .55fr .6fr;
  gap:8px;
  border-bottom:1px solid rgba(58,77,96,.35);
  padding:6px 0;
  color:var(--muted);
  font-size:13px;
}
.networkRow b{
  color:var(--text);
}
.networkWarn{
  margin-top:12px;
  border:1px solid rgba(255,209,102,.5);
  color:var(--warn);
  background:rgba(255,209,102,.08);
  border-radius:14px;
  padding:12px;
}
@media(max-width:900px){
  .networkGrid{grid-template-columns:1fr}
}

.networkConnectForm{
  display:grid;
  grid-template-columns:1.35fr 1.15fr auto;
  gap:10px;
  align-items:end;
}
.networkConnectForm label{
  display:block;
  color:var(--muted);
  font-size:12px;
  text-transform:uppercase;
  letter-spacing:.08em;
  margin-bottom:7px;
}
.networkConnectForm input{
  width:100%;
  border:1px solid var(--line2);
  background:#071019;
  color:var(--text);
  border-radius:10px;
  padding:9px 10px;
  font:inherit;
}
.networkUseBtn{
  padding:6px 12px;
  font-size:12px;
  font-weight:700;
  border-radius:999px;
  border:1px solid #1d4ed8;
  background:linear-gradient(180deg,#3b82f6 0%,#2563eb 100%);
  color:#ffffff;
  cursor:pointer;
  box-shadow:0 1px 2px rgba(0,0,0,.25);
}
.networkUseBtn:hover{
  border-color:#60a5fa;
  background:linear-gradient(180deg,#60a5fa 0%,#2563eb 100%);
}
@media(max-width:900px){
  .networkConnectForm{grid-template-columns:1fr}
}
.hidden{display:none}
@media(max-width:1050px){
  .grid{grid-template-columns:1fr}
  .footerGrid{grid-template-columns:1fr}
  .topbar{align-items:flex-start;flex-direction:column}
  .statusPills{justify-content:flex-start}
}
@media(max-width:650px){
  .app{padding:14px}
  .metricGrid,.bigMetric{grid-template-columns:1fr}
  .copyBox{min-height:130px}
  .barRow{grid-template-columns:80px 1fr 48px}
}
</style>

<style>
.tftIdlePreview{
  display:block;
  width:100%;
  max-width:260px;
  aspect-ratio:4/3;
  object-fit:cover;
  margin-top:10px;
  border-radius:14px;
  border:1px solid rgba(111, 227, 255, 0.22);
  box-shadow:0 10px 30px rgba(0,0,0,.35), inset 0 0 0 1px rgba(255,255,255,.02);
  opacity:.92;
}
</style>




<style>
/* MW_NEON_HORSE_THEME_V3 */
:root{
  --mw-bg:#02070b;
  --mw-bg2:#06111a;
  --mw-card:#071824;
  --mw-card2:#0c2230;
  --mw-cyan:#42f8ff;
  --mw-cyan-soft:rgba(66,248,255,.34);
  --mw-cyan-faint:rgba(66,248,255,.12);
  --mw-teal:#5eead4;
  --mw-orange:#ffb02e;
  --mw-orange-soft:rgba(255,176,46,.35);
  --mw-purple:#b794ff;
  --mw-green:#68ff9f;
  --mw-red:#ff5f72;
  --mw-text:#eefcff;
  --mw-muted:#93aaba;
}

/* Base backdrop */
html,body{
  background:
    radial-gradient(circle at 68% 0%, rgba(66,248,255,.13), transparent 24rem),
    radial-gradient(circle at 18% 20%, rgba(255,176,46,.08), transparent 24rem),
    radial-gradient(circle at 95% 58%, rgba(183,148,255,.07), transparent 26rem),
    linear-gradient(135deg,#02070b 0%,#06121b 42%,#070c18 100%) !important;
  color:var(--mw-text) !important;
}

/* Grid and scanline atmosphere */
body::before{
  content:"";
  position:fixed;
  inset:0;
  pointer-events:none;
  z-index:-3;
  background-image:
    linear-gradient(rgba(66,248,255,.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(66,248,255,.035) 1px, transparent 1px),
    linear-gradient(rgba(255,255,255,.018) 50%, transparent 50%);
  background-size:38px 38px, 38px 38px, 100% 4px;
  opacity:.75;
  mask-image:radial-gradient(circle at 50% 18%, black 0%, transparent 82%);
}

/* Large horse/key watermark, left side like the mockup */
body::after{
  content:"";
  position:fixed;
  left:-44px;
  top:78px;
  width:360px;
  height:520px;
  pointer-events:none;
  z-index:-2;
  background:url('/assets/horse_boot_splash.png') center/cover no-repeat;
  opacity:.18;
  filter:saturate(1.35) contrast(1.12);
  border-radius:34px;
  box-shadow:
    0 0 90px rgba(66,248,255,.10),
    0 0 130px rgba(255,176,46,.06);
}

/* App container spacing, if applicable */
main,
.container,
.wrap{
  position:relative;
}

/* Main cards: bolder neon rim, but not every random panel */
.card{
  background:
    linear-gradient(180deg, rgba(10,28,42,.90), rgba(3,12,20,.94)) !important;
  border:1px solid rgba(66,248,255,.27) !important;
  border-radius:18px !important;
  box-shadow:
    0 20px 48px rgba(0,0,0,.34),
    0 0 0 1px rgba(66,248,255,.025),
    0 0 28px rgba(66,248,255,.055),
    inset 0 1px 0 rgba(255,255,255,.04) !important;
  overflow:hidden;
}

.card:hover{
  border-color:rgba(66,248,255,.42) !important;
  box-shadow:
    0 22px 52px rgba(0,0,0,.38),
    0 0 34px rgba(66,248,255,.10),
    inset 0 1px 0 rgba(255,255,255,.05) !important;
}

/* Card title/header strip effect */
.card > h3:first-child,
.card > h4:first-child{
  margin-left:-2px;
  margin-right:-2px;
  padding-bottom:8px;
  border-bottom:1px solid rgba(66,248,255,.18);
}

/* Headings */
h1,h2,h3,h4{
  color:var(--mw-text) !important;
}

h1{
  color:#eaffff !important;
  text-shadow:
    0 0 10px rgba(66,248,255,.42),
    0 0 24px rgba(66,248,255,.18) !important;
}

h1::after{
  content:"";
  display:block;
  width:180px;
  height:2px;
  margin-top:6px;
  background:linear-gradient(90deg,var(--mw-cyan),transparent);
  box-shadow:0 0 16px rgba(66,248,255,.45);
}

/* Logo chip */
.logo,
[class*="logo"]{
  box-shadow:
    0 0 18px rgba(66,248,255,.35),
    inset 0 1px 0 rgba(255,255,255,.22) !important;
}

/* Stable COPY hero */
#stableCopy,
.copyHero,
[class*="stable"] [class*="copy"],
.card:has(#stableCopy){
  text-shadow:
    0 0 18px rgba(66,248,255,.18),
    0 0 38px rgba(66,248,255,.08);
}

/* Waiting for CW text */
.big,
.hero,
[class*="hero"]{
  color:#dffaff !important;
  text-shadow:
    0 0 16px rgba(66,248,255,.22),
    0 0 44px rgba(66,248,255,.10) !important;
}

/* Settings tiles */
.setting{
  background:
    linear-gradient(180deg, rgba(5,17,27,.62), rgba(3,10,17,.70)) !important;
  border:1px solid rgba(66,248,255,.16) !important;
  border-radius:16px !important;
  padding:14px !important;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.025),
    0 0 18px rgba(66,248,255,.025) !important;
}

.setting:hover{
  border-color:rgba(66,248,255,.34) !important;
  box-shadow:
    0 0 22px rgba(66,248,255,.07),
    inset 0 1px 0 rgba(255,255,255,.035) !important;
}

.setting label,
label{
  color:#d8f9ff !important;
}

/* Inputs */
input,
select,
textarea{
  background:#030c13 !important;
  color:var(--mw-text) !important;
  border:1px solid rgba(66,248,255,.28) !important;
  border-radius:10px !important;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.025),
    0 0 14px rgba(66,248,255,.025) !important;
}

input:focus,
select:focus,
textarea:focus{
  outline:none !important;
  border-color:rgba(66,248,255,.78) !important;
  box-shadow:
    0 0 0 3px rgba(66,248,255,.11),
    0 0 24px rgba(66,248,255,.12),
    inset 0 1px 0 rgba(255,255,255,.04) !important;
}

/* Range sliders */
input[type="range"]{
  accent-color:var(--mw-teal);
  filter:drop-shadow(0 0 6px rgba(94,234,212,.34));
}

/* Buttons */
button,
.button{
  border:1px solid rgba(66,248,255,.25) !important;
  border-radius:11px !important;
  background:
    linear-gradient(180deg, rgba(22,45,62,.92), rgba(6,20,31,.96)) !important;
  color:var(--mw-text) !important;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.05),
    0 0 14px rgba(66,248,255,.055) !important;
  transition:transform .12s ease, box-shadow .12s ease, border-color .12s ease;
}

button:hover,
.button:hover{
  transform:translateY(-1px);
  border-color:rgba(66,248,255,.60) !important;
  box-shadow:
    0 0 22px rgba(66,248,255,.16),
    inset 0 1px 0 rgba(255,255,255,.07) !important;
}

button.primary,
.primary{
  background:
    linear-gradient(135deg, #5eead4 0%, #43d9ff 48%, #189dff 100%) !important;
  color:#031017 !important;
  font-weight:900 !important;
  border-color:rgba(160,255,255,.86) !important;
  box-shadow:
    0 0 20px rgba(66,248,255,.28),
    0 0 42px rgba(66,248,255,.10),
    inset 0 1px 0 rgba(255,255,255,.32) !important;
}

/* Tabs */
.tabs button,
.tab,
[role="tab"]{
  border-color:rgba(66,248,255,.25) !important;
}

.tabs button.active,
.tab.active,
[role="tab"][aria-selected="true"]{
  background:
    linear-gradient(135deg, #5eead4, #5dbdff) !important;
  color:#021016 !important;
  border-color:rgba(165,255,255,.86) !important;
  box-shadow:0 0 20px rgba(66,248,255,.25) !important;
}

/* Meter bars */
.bar span,
.meter span{
  background:
    linear-gradient(90deg, var(--mw-teal), var(--mw-orange)) !important;
  box-shadow:
    0 0 14px rgba(94,234,212,.24),
    0 0 18px rgba(255,176,46,.18);
}

/* Tone ranking gets a bit of the receiver analyser look */
#toneRanking .bar span,
[class*="tone"] .bar span{
  background:
    linear-gradient(90deg, var(--mw-purple), #7cc7ff, var(--mw-cyan)) !important;
}

/* Pills and badges */
.badge,
.pill{
  background:rgba(2,10,16,.78) !important;
  border:1px solid rgba(66,248,255,.24) !important;
  color:#eaffff !important;
  box-shadow:0 0 14px rgba(66,248,255,.055);
}

.badge.ok,
.badge.good,
.badge.running,
[class*="running"]{
  color:var(--mw-green) !important;
  border-color:rgba(104,255,159,.42) !important;
  box-shadow:0 0 16px rgba(104,255,159,.11);
}

.badge.warn,
.badge.low,
.badge.hot{
  color:var(--mw-orange) !important;
  border-color:rgba(255,176,46,.42) !important;
  box-shadow:0 0 16px rgba(255,176,46,.11);
}

.badge.bad,
.badge.error,
.badge.clip{
  color:var(--mw-red) !important;
  border-color:rgba(255,95,114,.45) !important;
  box-shadow:0 0 16px rgba(255,95,114,.11);
}

/* Hints / muted */
.hint,
.muted,
small{
  color:var(--mw-muted) !important;
}

/* TFT preview */
.tftIdlePreview{
  display:block;
  width:100%;
  max-width:240px;
  aspect-ratio:4/3;
  object-fit:cover;
  margin-top:10px;
  border-radius:14px;
  border:1px solid rgba(66,248,255,.34);
  box-shadow:
    0 16px 34px rgba(0,0,0,.42),
    0 0 30px rgba(66,248,255,.12),
    0 0 18px rgba(255,176,46,.08);
  opacity:.96;
}

/* Logs */
pre,
code,
[class*="log"]{
  color:#d9fbff !important;
}

/* A subtle glow divider on the Morse Controls card */
#controls,
#morseControls,
.card:has(.tabs){
  position:relative;
}

#controls::before,
#morseControls::before,
.card:has(.tabs)::before{
  content:"";
  position:absolute;
  left:18px;
  right:18px;
  top:0;
  height:1px;
  background:linear-gradient(90deg, transparent, rgba(66,248,255,.85), transparent);
  box-shadow:0 0 20px rgba(66,248,255,.42);
}

/* Let the left watermark disappear on narrow screens */
@media (max-width:1100px){
  body::after{
    opacity:.08;
    width:240px;
    height:180px;
    left:auto;
    right:12px;
    top:12px;
  }
}

@media (max-width:800px){
  body::after{
    display:none;
  }
}
</style>






<style>
/* MW_CENTER_SCALE_WATERMARK_V2 */

/* Disable older pseudo-watermarks. */
body::after{
  display:none !important;
}

/* Keep app content above the watermark. */
body > *:not(#mwSplashWatermark){
  position:relative;
  z-index:2;
}

/* Centred scalable splash watermark, tuned to sit behind the middle of the UI
   without disappearing completely behind the top cards. */
#mwSplashWatermark{
  position:fixed;
  inset:0;
  z-index:1;
  pointer-events:none;

  background-image:
    radial-gradient(circle at 50% 54%, rgba(66,248,255,.18), transparent 38%),
    radial-gradient(circle at 52% 64%, rgba(255,176,46,.13), transparent 42%),
    url('/assets/horse_boot_splash_bg.png');

  background-position:
    center 52%,
    center 58%,
    center 48%;

  background-repeat:no-repeat;

  background-size:
    min(106vw, 1180px) min(79vw, 885px),
    min(96vw, 1040px) min(72vw, 780px),
    min(88vw, 940px) auto;

  opacity:.42;
  filter:saturate(1.45) contrast(1.14) brightness(1.12);
  mix-blend-mode:screen;
}

/* Lighter readability veil than before. Still keeps the controls legible. */
#mwSplashWatermark::after{
  content:"";
  position:absolute;
  inset:0;
  background:
    radial-gradient(circle at 50% 50%, rgba(2,7,11,.04), rgba(2,7,11,.36) 58%, rgba(2,7,11,.78) 100%),
    linear-gradient(90deg, rgba(2,7,11,.72), rgba(2,7,11,.10) 46%, rgba(2,7,11,.72));
}

/* A little extra neon glow line so it feels intentional, not accidental. */
#mwSplashWatermark::before{
  content:"";
  position:absolute;
  left:18%;
  right:18%;
  top:54%;
  height:1px;
  background:linear-gradient(90deg, transparent, rgba(66,248,255,.34), rgba(255,176,46,.22), transparent);
  box-shadow:0 0 26px rgba(66,248,255,.18);
}

/* Large screens can carry more art. */
@media (min-width:1500px){
  #mwSplashWatermark{
    opacity:.46;
    background-image:
      radial-gradient(circle at 50% 54%, rgba(66,248,255,.18), transparent 38%),
      radial-gradient(circle at 52% 64%, rgba(255,176,46,.13), transparent 42%),
      url('/assets/horse_boot_splash_bg_wide.png');
    background-size:
      1320px 990px,
      1160px 870px,
      1040px auto;
  }
}

/* Small screens: tone it down. */
@media (max-width:1000px){
  #mwSplashWatermark{
    opacity:.24;
    background-position:
      center 50%,
      center 56%,
      center 50%;
    background-size:
      120vw 90vw,
      110vw 82vw,
      min(100vw, 760px) auto;
  }
}

/* MW_REPLY_HELPER_LAYOUT_V1 */
.aiCopilotWide{
  margin-top:16px;
}
.aiCopilotWide .cardBody{
  display:grid;
  grid-template-columns:minmax(260px,.9fr) minmax(360px,1.1fr);
  gap:14px;
  align-items:start;
}
.aiCopilotWide .controls{
  display:flex;
  flex-wrap:wrap;
  gap:8px;
}
.aiCopilotWide .setting{
  margin-top:0 !important;
}
.aiCopilotWide textarea{
  min-height:86px;
}
.aiCopilotWide pre{
  max-height:105px;
  overflow:auto;
}
.aiCopilotWide .kv{
  margin-top:10px;
}
@media (max-width:1000px){
  .aiCopilotWide .cardBody{
    grid-template-columns:1fr;
  }
}

</style>

<style>
/* MW_LIQUID_GLASS_RADIO_CONSOLE_V3
   Future glass treatment: neon-rich, soft, tactile, still a radio appliance. */
:root{
  --bg:#02050d;
  --panel:#071421;
  --panel2:#0c2634;
  --line:#6beeff;
  --text:#f6fdff;
  --muted:#a8bdc8;
  --good:#70ffac;
  --warn:#ffd36e;
  --bad:#ff7f8d;
  --blue:#66eaff;
  --violet:#c8a6ff;
  --glass:rgba(8,27,42,.54);
  --shadow:
    0 34px 90px rgba(0,0,0,.48),
    0 0 54px rgba(102,234,255,.18);
}

html,body{
  background:
    radial-gradient(circle at 18% 0%, rgba(112,255,172,.20), transparent 24rem),
    radial-gradient(circle at 78% 4%, rgba(102,234,255,.32), transparent 30rem),
    radial-gradient(circle at 92% 62%, rgba(200,166,255,.24), transparent 32rem),
    radial-gradient(circle at 24% 82%, rgba(255,211,110,.13), transparent 26rem),
    linear-gradient(135deg,#02050d 0%,#06121c 44%,#09071a 100%) !important;
}
body::before{
  display:block !important;
  content:"";
  position:fixed;
  inset:0;
  pointer-events:none;
  z-index:-3;
  background-image:
    linear-gradient(rgba(102,234,255,.050) 1px, transparent 1px),
    linear-gradient(90deg, rgba(102,234,255,.045) 1px, transparent 1px),
    linear-gradient(rgba(255,255,255,.022) 50%, transparent 50%);
  background-size:46px 46px,46px 46px,100% 5px;
  opacity:.54;
  mask-image:radial-gradient(circle at 50% 16%, black 0%, transparent 82%);
}

.app{max-width:1680px}
.title h1{
  letter-spacing:-.025em;
  text-shadow:
    0 0 14px rgba(102,234,255,.72),
    0 0 44px rgba(102,234,255,.30),
    0 0 76px rgba(200,166,255,.16) !important;
}
.title h1::after{
  display:block !important;
  width:220px;
  height:2px;
  margin-top:8px;
  background:linear-gradient(90deg,#70ffac,#66eaff,#ffd36e,transparent);
  box-shadow:0 0 22px rgba(102,234,255,.78);
}
.title .sub{letter-spacing:.01em}
.logo{
  background:linear-gradient(135deg,#70ffac 0%,#66eaff 52%,#8ea2ff 100%) !important;
  color:#031017 !important;
  border:1px solid rgba(190,255,255,.82);
  border-radius:18px !important;
  box-shadow:
    0 0 26px rgba(102,234,255,.58),
    0 0 66px rgba(112,255,172,.22),
    inset 0 1px 0 rgba(255,255,255,.50),
    inset 0 -12px 26px rgba(0,40,60,.18) !important;
  letter-spacing:-1px;
}

.card{
  background:
    linear-gradient(145deg,rgba(255,255,255,.105),rgba(255,255,255,.028) 32%,rgba(8,27,42,.62) 100%),
    radial-gradient(circle at 18% 0%, rgba(102,234,255,.18), transparent 18rem),
    linear-gradient(180deg,rgba(7,23,36,.72),rgba(4,12,21,.88)) !important;
  border:1px solid rgba(190,255,255,.34) !important;
  border-radius:26px !important;
  backdrop-filter:blur(28px) saturate(1.65);
  box-shadow:var(--shadow) !important;
}
.card:hover{
  border-color:rgba(190,255,255,.70) !important;
  box-shadow:
    0 36px 100px rgba(0,0,0,.50),
    0 0 72px rgba(102,234,255,.30),
    inset 0 1px 0 rgba(255,255,255,.14) !important;
}
.cardHead{
  border-bottom:1px solid rgba(190,255,255,.20);
  padding-bottom:12px;
}
.cardHead h2,.cardHead h3{letter-spacing:.01em}
.copyText{
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  letter-spacing:.015em;
  font-weight:700;
  color:#f5feff !important;
  text-shadow:
    0 0 18px rgba(102,234,255,.46),
    0 0 48px rgba(102,234,255,.20),
    0 0 72px rgba(112,255,172,.10) !important;
}
.rawText,.log,pre,code,[class*="log"]{
  color:#dffbff !important;
  text-shadow:0 0 14px rgba(102,234,255,.14) !important;
}

.badge,.pill{
  background:
    linear-gradient(180deg,rgba(255,255,255,.105),rgba(255,255,255,.025)),
    rgba(3,12,18,.64) !important;
  border:1px solid rgba(190,255,255,.34) !important;
  border-radius:999px !important;
  backdrop-filter:blur(18px) saturate(1.5);
  color:#ecfdff !important;
  box-shadow:
    0 0 24px rgba(102,234,255,.16),
    inset 0 1px 0 rgba(255,255,255,.15) !important;
}
.badge.good{color:var(--good) !important;border-color:rgba(112,255,172,.60) !important;box-shadow:0 0 28px rgba(112,255,172,.24) !important}
.badge.warn{color:var(--warn) !important;border-color:rgba(255,211,110,.60) !important;box-shadow:0 0 28px rgba(255,211,110,.22) !important}
.badge.bad{color:var(--bad) !important;border-color:rgba(255,127,141,.62) !important;box-shadow:0 0 28px rgba(255,127,141,.22) !important}

button,.btn,.button{
  background:
    linear-gradient(180deg,rgba(255,255,255,.14),rgba(255,255,255,.035)),
    rgba(8,28,42,.72) !important;
  color:#f0fcff !important;
  border:1px solid rgba(190,255,255,.34) !important;
  border-radius:16px !important;
  backdrop-filter:blur(18px) saturate(1.45);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.16),
    0 0 24px rgba(102,234,255,.12) !important;
  transform:none !important;
}
button:hover,.btn:hover,.button:hover{
  border-color:rgba(190,255,255,.78) !important;
  background:
    linear-gradient(180deg,rgba(255,255,255,.22),rgba(255,255,255,.055)),
    rgba(10,40,58,.82) !important;
  box-shadow:
    0 0 36px rgba(102,234,255,.32),
    inset 0 1px 0 rgba(255,255,255,.22) !important;
}
button.primary,.primary{
  background:linear-gradient(135deg,#70ffac 0%,#66eaff 45%,#8ea2ff 100%) !important;
  color:#031017 !important;
  border-color:rgba(190,255,255,.90) !important;
  box-shadow:
    0 0 30px rgba(102,234,255,.48),
    0 0 70px rgba(102,234,255,.20),
    inset 0 1px 0 rgba(255,255,255,.45),
    inset 0 -14px 26px rgba(0,60,80,.16) !important;
}

input,select,textarea{
  background:
    linear-gradient(180deg,rgba(255,255,255,.08),rgba(255,255,255,.018)),
    rgba(3,12,18,.74) !important;
  border:1px solid rgba(190,255,255,.32) !important;
  border-radius:16px !important;
  color:#f0fcff !important;
  backdrop-filter:blur(14px) saturate(1.35);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.10),
    0 0 22px rgba(102,234,255,.08) !important;
}
input:focus,select:focus,textarea:focus{
  border-color:rgba(190,255,255,.86) !important;
  box-shadow:
    0 0 0 4px rgba(102,234,255,.15),
    0 0 42px rgba(102,234,255,.26) !important;
}

.setting,.networkBox,.metric{
  background:
    linear-gradient(145deg,rgba(255,255,255,.075),rgba(255,255,255,.018)),
    rgba(4,14,22,.50) !important;
  border:1px solid rgba(190,255,255,.22) !important;
  border-radius:20px !important;
  backdrop-filter:blur(18px) saturate(1.35);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.08),
    0 0 24px rgba(102,234,255,.06) !important;
}
.setting:hover{
  border-color:rgba(190,255,255,.48) !important;
  box-shadow:0 0 34px rgba(102,234,255,.14) !important;
}

.barFill,.bar span,.meter span,#toneRanking .bar span,[class*="tone"] .bar span{
  background:linear-gradient(90deg,#70ffac,#66eaff,#ffd36e) !important;
  box-shadow:
    0 0 20px rgba(102,234,255,.34),
    0 0 28px rgba(255,211,110,.18) !important;
}

#mwSplashWatermark{opacity:.42 !important;filter:saturate(1.28) contrast(1.08) !important}
#controls::before,#morseControls::before,.card:has(.tabs)::before{
  display:block !important;
  background:linear-gradient(90deg,transparent,rgba(102,234,255,.95),rgba(255,211,110,.62),transparent) !important;
  box-shadow:0 0 30px rgba(102,234,255,.58) !important;
}
</style>

</head>
<body>
<div class="app">
  <div class="topbar">
    <div class="brand">
      <div class="logo">MW</div>
      <div class="title">
        <h1>The Morse Whisperer</h1>
        <div class="sub">CW decoder appliance - Raspberry Pi live receiver</div>
      </div>
    </div>
    <div class="statusPills">
      <div class="pill"><span id="modeDot" class="dot"></span><b id="mode">loading</b></div>
      <div class="pill">Updated <b id="age">--</b></div>
      <div class="pill">Device <b id="device">--</b></div>
      <div class="pill">Squelch <b id="squelch">--</b></div>
    </div>
  </div>

  <div class="grid">
    <main>
      <section class="card">
        <div class="cardHead">
          <h2>Stable COPY</h2>
          <span id="acceptedBadge" class="badge">accepted output</span>
        </div>
        <div class="cardBody copyBox">
          <div id="copy" class="copyText empty">Waiting for CW...</div>
        </div>
      </section>

      <section class="card" style="margin-top:16px">
        <div class="cardHead">
          <h2>Stable RAW</h2>
          <span class="badge">literal accepted decode</span>
        </div>
        <div class="cardBody">
          <div id="raw" class="rawText">No accepted raw copy yet.</div>
        </div>
      </section>
    </main>

    <aside class="sideGrid">
      <section class="card">
        <div class="cardHead">
          <h3>Tone Lock</h3>
          <span id="toneModeBadge" class="badge">--</span>
        </div>
        <div class="cardBody">
          <div class="toneHero">
            <div id="toneLock" class="tone">--</div>
            <div class="hz">Hz</div>
          </div>
          <div class="small" id="toneReason">Waiting for signal</div>
        </div>
      </section>

      <section class="card">
        <div class="cardHead"><h3>Signal Quality</h3></div>
        <div class="cardBody">
          <div class="barGroup">
            <div class="barRow"><div>SNR</div><div class="barTrack"><div id="snrBar" class="barFill"></div></div><b id="snrVal">--</b></div>
            <div class="barRow"><div>Confidence</div><div class="barTrack"><div id="confBar" class="barFill"></div></div><b id="confVal">--</b></div>
            <div class="barRow"><div>RMS</div><div class="barTrack"><div id="rmsBar" class="barFill"></div></div><b id="rmsVal">--</b></div>
            <div class="barRow"><div>Peak</div><div class="barTrack"><div id="peakBar" class="barFill"></div></div><b id="peakVal">--</b></div>
          </div>
        </div>
      </section>

      <section class="card">
        <div class="cardHead"><h3>Operator Controls</h3></div>
        <div class="cardBody">
          <div class="controls">
            <button class="primary" onclick="resetCopy()">Reset copy / buffer</button>
            <button id="filterToggleBtn" type="button" onclick="toggleBandwidthFilter()">Filter: --</button>
            <a class="btn" href="/download/copy.txt">Copy TXT</a>
            <a class="btn" href="/download/report.json">Report JSON</a>
            <a class="btn" href="/api/snapshot">API</a>
          </div>
        </div>
      </section>
    </aside>
  </div>

  <!-- MW_REPLY_HELPER_LAYOUT_V1 -->


      <section class="card aiCopilotWide" id="aiCopilotCard">
        <div class="cardHead">
          <h3>Station Notes</h3>
          <span id="aiProviderBadge" class="badge">local helper</span>
        </div>
        <div class="cardBody">
          <div class="small" style="margin-bottom:10px">
            Optional reply helper for received copy. The decoder stays local; nothing is sent unless the helper is enabled.
          </div>

          <div class="controls">
            <button onclick="aiAnalyseCurrent()">Read current copy</button>
            <button class="primary" onclick="aiSuggestReply()">Draft reply</button>
            <button onclick="aiCopyReply()">Copy reply</button>
            <button onclick="aiPlayReply()">Play as CW</button>
            <button onclick="aiResetQso()">Reset QSO</button>
          </div>

          <div class="kv" style="margin-top:12px">
            <div>Intent</div><div id="aiIntent">--</div>
            <div>Station</div><div id="aiTheirCall">--</div>
            <div>Confidence</div><div id="aiConfidence">--</div>
          </div>

          <div class="setting" style="margin-top:12px">
            <label for="aiReplyText">Draft reply</label>
            <textarea id="aiReplyText" rows="3" placeholder="No draft yet."></textarea>
            <div class="hint" id="aiPlainEnglish">Read the current copy or draft a reply to populate this.</div>
          </div>

          <pre class="log" id="aiWarnings" style="margin-top:10px">Reply helper ready.</pre>
        </div>
      </section>

  <section class="card" style="margin-top:16px">
    <div class="cardHead">
      <h3>Morse Controls</h3>
      <span id="settingsState" class="badge">persistent settings</span>
    </div>
    <div class="cardBody">
      <div class="tabs">
        <button id="tabSettingsBtn" class="tabBtn active" onclick="showControlTab('settings')">Settings</button>
        <button id="tabGeneratorBtn" class="tabBtn" onclick="showControlTab('generator')">CW Generator / Trainer</button>
        <button id="tabNetworkBtn" class="tabBtn" onclick="showControlTab('network')">Network Setup</button>
      </div>

      <div id="tabSettings" class="tabPane active">
        <div class="settingsGrid">
          <div class="setting">
            <label for="setToneMode">Decoder mode</label>
            <select id="setToneMode">
              <option value="session_auto">Full auto - recommended</option>
              <option value="auto">Continuous auto tone</option>
              <option value="fixed">Manual fixed tone</option>
            </select>
            <div class="hint" id="toneModeHelp">
              Full auto scans for the CW tone at the start of a session, then locks it so noise does not drag the decoder around.
            </div>
          </div>

          <div class="setting">
            <label for="setTone">Tone Hz</label>
            <input id="setTone" type="number" min="300" max="1200" step="10">
            <div class="hint">Used for fixed/manual mode and fallback tone.</div>
          </div>

          <div class="setting">
            <label for="setWpm">WPM hint</label>
            <input id="setWpm" type="number" min="3" max="45" step="0.25">
            <div class="hint">Decoder starting estimate. Does not autocorrect text.</div>
          </div>

          <div class="setting">
            <label for="setInputLevel">Input level %</label>
            <input id="setInputLevel" type="range" min="0" max="100" step="1">
            <div class="hint"><span id="setInputLevelVal">--</span>% - attempts ALSA Capture level.</div>
          </div>

          <div class="setting">
            <label for="setAudioFilterMode">Audio bandwidth filter</label>
            <select id="setAudioFilterMode">
              <option value="off">Off</option>
              <option value="wide">Wide - 500 Hz</option>
              <option value="narrow">Narrow - 220 Hz</option>
              <option value="custom">Custom</option>
            </select>
            <div class="hint">Filters around the detected CW tone before decode.</div>
          </div>

          <div class="setting">
            <label for="setAudioFilterBandwidth">Custom filter bandwidth Hz</label>
            <input id="setAudioFilterBandwidth" type="number" min="80" max="1200" step="10">
            <div class="hint">Used only in Custom mode. Start around 300 Hz.</div>
          </div>

          <div class="setting">
            <label for="setLcdBrightness">TFT brightness %</label>
            <input id="setLcdBrightness" type="range" min="10" max="100" step="1">
            <div class="hint"><span id="setLcdBrightnessVal">--</span>% - software dimming unless hardware backlight exists.</div>
          </div>

          <div class="setting">
            <label for="setTftIdleEnabled">TFT idle splash</label>
            <select id="setTftIdleEnabled">
              <option value="true">Enabled</option>
              <option value="false">Disabled</option>
            </select>
            <div class="hint">Shows the horse splash after no CW or button activity.</div>
            <img class="tftIdlePreview" src="/assets/horse_boot_splash.png" alt="TFT idle splash preview">
          </div>

          <div class="setting">
            <label for="setTftIdleSeconds">TFT idle timeout</label>
            <input id="setTftIdleSeconds" type="number" min="15" max="3600" step="15">
            <div class="hint">Seconds before idle splash. 300 = five minutes. Any button wakes the TFT.</div>
          </div>

          <div class="setting">
            <label for="setOutputDevice">USB speaker output</label>
            <input id="setOutputDevice" type="text" placeholder="plughw:2,0">
            <div class="hint">Used by the CW generator via aplay.</div>
          </div>

          <div class="setting">
            <label for="setAiEnabled">Reply helper</label>
            <select id="setAiEnabled">
              <option value="false">Disabled - local only</option>
              <option value="true">Enabled - assist only</option>
            </select>
            <div class="hint">Decoder always remains local. The helper only reads copy and drafts replies for review.</div>
          </div>

          <div class="setting">
            <label for="setAiProvider">Reply source</label>
            <select id="setAiProvider">
              <option value="local">Local rules only</option>
              <option value="openai">OpenAI / ChatGPT</option>
            </select>
            <div class="hint">OpenAI requires /etc/morse-whisperer/ai.env.</div>
          </div>

          <div class="setting">
            <label for="setAiModel">Reply model</label>
            <input id="setAiModel" type="text" placeholder="gpt-4.1-mini">
            <div class="hint">Used only when the reply helper is enabled.</div>
          </div>

          <div class="setting">
            <label for="setAiRealtimeAssist">Auto notes</label>
            <select id="setAiRealtimeAssist">
              <option value="false">Disabled</option>
              <option value="true">Enabled for new copy</option>
            </select>
            <div class="hint">When the reply helper is enabled, read new stable COPY events automatically.</div>
          </div>
        </div>

        <div class="controls" style="margin-top:14px">
          <button class="primary" onclick="saveSettings()">Save settings</button>
          <button onclick="resetDefaults()">Reset to defaults</button>
        </div>
      </div>

      <div id="tabGenerator" class="tabPane">
        <div class="trainerSectionTitle">Playback medium</div>
        <div class="playbackModes">
          <button id="playbackSound" class="modeTile active" onclick="setPlaybackMode('sound')">Sound</button>
          <button id="playbackLight" class="modeTile disabled" onclick="setPlaybackMode('light')" title="Future visual flash trainer mode">Light</button>
          <button id="playbackVibrate" class="modeTile disabled" onclick="setPlaybackMode('vibrate')" title="Future external haptic output">Vibrate</button>
        </div>

        <div class="generatorHero">
          <div>
            <div class="trainerSectionTitle">Timing</div>
            <div class="settingsGrid">
              <div class="setting">
                <label for="cwWpm">Character speed WPM</label>
                <input id="cwWpm" type="number" min="3" max="40" step="0.25">
                <div class="hint">How fast each letter is sent.</div>
              </div>

              <div class="setting">
                <label for="cwFarnsworth">Farnsworth / overall WPM</label>
                <input id="cwFarnsworth" type="number" min="3" max="40" step="0.25">
                <div class="hint">Lower values stretch spacing between characters and words.</div>
              </div>

              <div class="setting">
                <label for="cwKeyProfile">Simulated Morse key</label>
                <select id="cwKeyProfile">
                  <option value="computer">Computer - perfect timing</option>
                  <option value="paddle_clean">Paddle - clean</option>
                  <option value="paddle_learner">Paddle - learner</option>
                  <option value="bug_light">Bug - light humanise</option>
                  <option value="straight_human">Straight key - humanise</option>
                </select>
                <div class="hint">Adds timing character. Computer mode is best for decoder testing.</div>
              </div>

              <div class="setting">
                <label for="cwTone">Pitch Hz</label>
                <input id="cwTone" type="number" min="300" max="1200" step="10">
                <div class="hint">Audio pitch for generated CW.</div>
              </div>

              <div class="setting">
                <label for="cwVolume">Volume %</label>
                <input id="cwVolume" type="range" min="5" max="95" step="1" value="35">
                <div class="hint"><span id="cwVolumeVal">35</span>% output level.</div>
              </div>

              <div class="setting">
                <label for="cwAdvancedToggle">Advanced timing</label>
                <select id="cwAdvancedToggle" onchange="toggleTrainerAdvanced()">
                  <option value="off">Hidden</option>
                  <option value="on">Show advanced timing</option>
                </select>
                <div class="hint">Start delay, end gap, and future weighting controls.</div>
              </div>
            </div>

            <div id="advancedTrainer" class="advancedTrainer">
              <div class="settingsGrid">
                <div class="setting">
                  <label for="cwStartDelay">Start-up delay ms</label>
                  <input id="cwStartDelay" type="number" min="0" max="5000" step="50">
                  <div class="hint">Silence before sending starts.</div>
                </div>

                <div class="setting">
                  <label for="cwEndGap">End gap ms</label>
                  <input id="cwEndGap" type="number" min="0" max="5000" step="50">
                  <div class="hint">Silence after sending finishes.</div>
                </div>

                <div class="setting">
                  <label for="cwPlaybackMode">Playback mode</label>
                  <select id="cwPlaybackMode">
                    <option value="sound">Sound</option>
                    <option value="light" disabled>Light - future</option>
                    <option value="vibrate" disabled>Vibrate - future</option>
                  </select>
                  <div class="hint">Only Sound is active on this hardware today.</div>
                </div>
              </div>
            </div>

            <div class="trainerSectionTitle" style="margin-top:16px">Text / lesson</div>
            <div class="setting">
              <label for="cwText">Training text</label>
              <textarea id="cwText">VVV THE MORSE WHISPERER TEST 73</textarea>
              <div class="hint">Generated locally and played out the USB sound card.</div>
              <div class="presetGrid">
                <button onclick="setTrainerPreset('VVV THE MORSE WHISPERER TEST 73')">Test</button>
                <button onclick="setTrainerPreset('AAAAAAAAAA THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG')">Decoder test</button>
                <button onclick="setTrainerPreset('ZL1SXG ZL2RO 73')">Callsigns</button>
                <button onclick="setTrainerPreset('CQ CQ CQ DE ZL1SXG ZL1SXG K')">CQ call</button>
                <button onclick="setTrainerPreset('12345 67890')">Numbers</button>
                <button onclick="setTrainerPreset('PARIS PARIS PARIS')">PARIS</button>
              </div>
            </div>
          </div>

          <div class="generatorPreview">
            <div class="small" style="margin-bottom:8px">Morse preview</div>
            <div id="cwPreview" class="morsePreview">...</div>
          </div>
        </div>

        <div class="controls" style="margin-top:14px">
          <button class="primary" onclick="playCw()">Play CW</button>
          <button onclick="selfTestCw()">Generate + Decode</button>
          <button onclick="stopCw()">Stop CW</button>
          <button onclick="saveSettings()">Save trainer settings</button>
        </div>

        <div id="selfTestResult" class="selfTestResult">
          Self-test decode has not been run yet.
        </div>
      </div>

      <div id="tabNetwork" class="tabPane">
<div class="networkGrid" style="margin-top:14px">
          <div class="networkBox">
            <h4>Current network status</h4>
            <div class="kv">
              <div>Hostname</div><div id="netHostname">--</div>
              <div>IP addresses</div><div id="netIps">--</div>
              <div>Default route</div><div id="netDefaultRoute">--</div>
              <div>Wi-Fi device</div><div id="netWifiDevice">--</div>
              <div>Active Wi-Fi</div><div id="netActiveWifi">--</div>
              <div>Hotspot active</div><div id="netHotspotActive">--</div>
              <div>Fallback service</div><div id="netFallbackService">--</div>
              <div>Setup SSID</div><div id="netSetupSsid">The Morse Whisperer</div>
              <div>Setup URL</div><div id="netSetupUrl">http://10.42.0.1:8080</div>
            </div>

            <div class="controls" style="margin-top:14px">
              <button class="primary" onclick="loadNetworkStatus()">Refresh status</button>
              <button onclick="scanWifi()">Scan Wi-Fi</button>
            </div>
          </div>

          <div class="networkBox">
            <h4>Nearby Wi-Fi networks</h4>
            <div id="wifiScanList" class="networkList">
              Press Scan Wi-Fi.
            </div>
          </div>
        </div>

        <div class="networkBox" style="margin-top:12px">
          <h4>Join Wi-Fi network</h4>
          <div class="networkWarn" style="margin-top:0">
            Changing Wi-Fi can disconnect this browser or SSH session. If possible, plug in Ethernet before changing networks.
          </div>

          <div class="networkConnectForm" style="margin-top:12px">
            <div>
              <label for="netConnectSsid">SSID</label>
              <input id="netConnectSsid" type="text" placeholder="Network name">
            </div>
            <div>
              <label for="netConnectPassword">Password / PSK</label>
              <input id="netConnectPassword" type="password" placeholder="Leave blank for open Wi-Fi">
            </div>
            <div>
              <button class="primary" onclick="connectWifiManual()">Connect Wi-Fi</button>
            </div>
          </div>

          <div class="small" style="margin-top:10px">
            Press Connect beside a scanned network to fill the SSID, then enter the password and press Connect Wi-Fi.
          </div>
        </div>

        <div class="networkBox" style="margin-top:12px">
          <h4>Saved NetworkManager connections</h4>
          <div id="netConnections" class="networkList">Loading...</div>
        </div>
      </div>

      <div class="small" id="settingsMsg" style="margin-top:10px">Settings survive reboot via config.json.</div>
    </div>
  </section>

  <div class="footerGrid">
    <section class="card">
      <div class="cardHead">
        <h3>Current Signal</h3>
        <span id="levelBadge" class="badge">--</span>
      </div>
      <div class="cardBody">
        <div class="kv">
          <div>Selected tone</div><div id="selectedTone">--</div>
          <div>Fallback target</div><div id="targetTone">--</div>
          <div>WPM estimate</div><div id="wpm">--</div>
          <div>Reason</div><div id="reason">--</div>
          <div>Session</div><div id="session">--</div>
          <div>Buffer</div><div id="buffer">--</div>
        </div>
      </div>
    </section>

    <section class="card">
      <div class="cardHead"><h3>Tone Ranking</h3><span class="badge">current audio</span></div>
      <div class="cardBody">
        <div id="tones" class="tones">Waiting for tone scan...</div>
      </div>
    </section>
  </div>

  <div class="footerGrid">
    <section class="card">
      <div class="cardHead"><h3>Rejected Candidate</h3><span class="badge">hidden unless enabled</span></div>
      <div class="cardBody">
        <div id="candidate" class="rawText small">No rejected candidate shown.</div>
      </div>
    </section>

    <section class="card">
      <div class="cardHead"><h3>Status Log</h3></div>
      <div class="cardBody">
        <div id="log" class="statusLog">Loading...</div>
      </div>
    </section>
  </div>
</div>

<script>
function $(id){return document.getElementById(id)}
function num(v,d=1){return Number(v||0).toFixed(d)}
function clamp(v,min,max){return Math.max(min,Math.min(max,v))}
function pct(v,min,max){return clamp(((v-min)/(max-min))*100,0,100)}
function esc(s){return String(s??'')}
function setBar(id,val,cls=''){
  const el=$(id);
  el.style.width=clamp(val,0,100)+'%';
  el.className='barFill '+cls;
}
function levelClass(level){
  if(level==='GOOD') return 'good';
  if(level==='HOT'||level==='LOW') return 'warn';
  if(level==='CLIP'||level==='IDLE') return 'bad';
  return '';
}
function reasonClass(reason, conf, snr){
  if(reason==='ok' && Number(conf||0)>=0.85 && Number(snr||0)>=12) return 'good';
  if(reason==='low_or_no_signal') return 'bad';
  if(String(reason||'').includes('mismatch')) return 'warn';
  return 'warn';
}
async function resetCopy(){
  await fetch('/api/reset',{method:'POST'});
  $('copy').textContent='Waiting for CW...';
  $('copy').classList.add('empty');
  $('raw').textContent='No accepted raw copy yet.';
}

/* MW_MAIN_FILTER_TOGGLE_V1 */
function filterLabel(cfg){
  const enabled = cfg.audio_filter_enabled !== false;
  const mode = enabled ? (cfg.audio_filter_mode || 'wide') : 'off';
  if(mode === 'narrow') return 'Filter: Narrow';
  if(mode === 'custom') return 'Filter: Custom';
  if(mode === 'off') return 'Filter: Off';
  return 'Filter: Wide';
}

function updateFilterToggleButton(cfg){
  const btn = $('filterToggleBtn');
  if(!btn) return;

  btn.textContent = filterLabel(cfg || {});
  const mode = ((cfg || {}).audio_filter_enabled === false) ? 'off' : ((cfg || {}).audio_filter_mode || 'wide');

  btn.classList.remove('primary');
  btn.classList.toggle('active', mode !== 'off');

  if(mode === 'narrow'){
    btn.title = 'Bandwidth filter is narrow. Click to turn filter off.';
  }else if(mode === 'off'){
    btn.title = 'Bandwidth filter is off. Click to switch to wide.';
  }else if(mode === 'custom'){
    btn.title = 'Custom bandwidth filter is active. Click to switch to wide.';
  }else{
    btn.title = 'Bandwidth filter is wide. Click to switch to narrow.';
  }
}

async function toggleBandwidthFilter(){
  const btn = $('filterToggleBtn');
  if(btn){
    btn.disabled = true;
    btn.textContent = 'Filter: ...';
  }

  try{
    const current = await fetch('/api/settings?ts=' + Date.now(), {cache:'no-store'}).then(r=>r.json());
    const cfg = current.config || {};
    const enabled = cfg.audio_filter_enabled !== false;
    const mode = enabled ? (cfg.audio_filter_mode || 'wide') : 'off';

    let nextEnabled = true;
    let nextMode = 'wide';

    if(mode === 'wide'){
      nextMode = 'narrow';
    }else if(mode === 'narrow'){
      nextEnabled = false;
      nextMode = 'off';
    }else{
      nextMode = 'wide';
    }

    const payload = {
      audio_filter_enabled: nextEnabled,
      audio_filter_mode: nextMode,
      audio_filter_bandwidth_hz: Number(cfg.audio_filter_bandwidth_hz || 300)
    };

    const saved = await fetch('/api/settings', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify(payload)
    }).then(r=>r.json());

    if(!saved.ok){
      throw new Error(saved.error || 'settings save failed');
    }

    const updated = Object.assign({}, cfg, payload);
    updateFilterToggleButton(updated);

    if($('settingsMsg')){
      $('settingsMsg').textContent = 'Bandwidth filter set to ' + (nextEnabled ? nextMode : 'off') + '.';
    }
  }catch(e){
    if($('settingsMsg')){
      $('settingsMsg').textContent = 'Filter toggle failed: ' + e;
    }
  }finally{
    if(btn) btn.disabled = false;
  }
}

/* MW_REPLY_HELPER_WEB_CARD_V1 */
let mwAiLastAnalysis = null;
let mwAiLastReply = null;

function aiSetStatus(message, good=false){
  const el = $('aiWarnings');
  if(!el) return;
  el.textContent = message || '';
  el.className = 'log' + (good ? ' good' : '');
}

function aiCurrentCopyText(){
  const copy = ($('copy')?.textContent || '').trim();
  const raw = ($('raw')?.textContent || '').trim();

  if(copy && copy !== 'Waiting for CW...' && copy !== 'Waiting for CW...' && !copy.includes('Waiting for CW')){
    return copy;
  }

  if(raw && raw !== 'No accepted raw copy yet.'){
    return raw;
  }

  return '';
}

function aiUpdateProviderBadge(ctxOrSettings){
  const badge = $('aiProviderBadge');
  if(!badge) return;

  const enabled = ctxOrSettings && ctxOrSettings.ai_enabled === true;
  const provider = (ctxOrSettings && ctxOrSettings.ai_provider) || 'local';

  if(enabled && provider === 'openai'){
    badge.textContent = 'reply helper on';
    badge.className = 'badge good';
  }else{
    badge.textContent = 'local helper';
    badge.className = 'badge';
  }
}

function aiRenderAnalysis(analysis){
  if(!analysis) return;

  mwAiLastAnalysis = analysis;
  $('aiIntent').textContent = analysis.detected_intent || '--';
  $('aiTheirCall').textContent = analysis.their_call || ((analysis.qso_state||{}).their_call) || '--';

  const conf = Number(analysis.confidence || (analysis.decoder_quality||{}).confidence || 0);
  $('aiConfidence').textContent = conf ? conf.toFixed(2) : '--';

  const warnings = analysis.warnings || [];
  const provider = analysis.provider || (analysis.local_only ? 'local' : 'helper');
  const fallback = analysis.fallback_used ? ' - fallback used' : '';
  aiSetStatus(`Read by: ${provider}${fallback}\n${warnings.length ? warnings.join('\n') : 'No warnings.'}`, warnings.length === 0);

  aiUpdateProviderBadge({
    ai_enabled: analysis.local_only ? false : true,
    ai_provider: analysis.provider || 'local'
  });
}

function aiRenderReply(reply){
  if(!reply) return;

  mwAiLastReply = reply;
  $('aiReplyText').value = reply.suggested_reply_text || '';
  $('aiPlainEnglish').textContent = reply.plain_english || 'Review before sending.';

  const conf = Number(reply.confidence || 0);
  if(conf) $('aiConfidence').textContent = conf.toFixed(2);

  const warnings = reply.warnings || [];
  const provider = reply.provider || (reply.local_only ? 'local' : 'helper');
  const fallback = reply.fallback_used ? ' - fallback used' : '';
  aiSetStatus(`Drafted by: ${provider}${fallback}\n${warnings.length ? warnings.join('\n') : 'Review before transmit.'}`, warnings.length === 0);
}

async function aiAnalyseCurrent(){
  const text = aiCurrentCopyText();

  if(!text){
    aiSetStatus('No decoded copy available yet.');
    return;
  }

  aiSetStatus('Reading current copy...');

  try{
    const result = await fetch('/api/ai/analyse', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({text})
    }).then(r=>r.json());

    if(!result.ok){
      throw new Error(result.error || 'analysis failed');
    }

    aiRenderAnalysis(result);
  }catch(e){
    aiSetStatus('Copy read failed: ' + e);
  }
}

async function aiSuggestReply(){
  const text = aiCurrentCopyText();

  if(!text){
    aiSetStatus('No decoded copy available yet.');
    return;
  }

  aiSetStatus('Drafting reply...');

  try{
    const result = await fetch('/api/ai/reply', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({text})
    }).then(r=>r.json());

    if(!result.ok){
      throw new Error(result.error || 'reply failed');
    }

    aiRenderAnalysis(result.analysis);
    aiRenderReply(result.reply);
  }catch(e){
    aiSetStatus('Draft failed: ' + e);
  }
}

async function aiCopyReply(){
  const text = ($('aiReplyText')?.value || '').trim();

  if(!text){
    aiSetStatus('No draft reply to copy.');
    return;
  }

  try{
    if(navigator.clipboard && navigator.clipboard.writeText){
      await navigator.clipboard.writeText(text);
      aiSetStatus('Draft reply copied to clipboard.', true);
      return;
    }

    const area = $('aiReplyText');
    if(area){
      area.focus();
      area.select();
      const ok = document.execCommand && document.execCommand('copy');
      if(ok){
        aiSetStatus('Draft reply copied using browser fallback.', true);
        return;
      }
    }

    aiSetStatus('Clipboard unavailable. The reply text is selected; press Ctrl+C.');
  }catch(e){
    const area = $('aiReplyText');
    if(area){
      area.focus();
      area.select();
    }
    aiSetStatus('Clipboard unavailable. The reply text is selected; press Ctrl+C.');
  }
}

async function aiPlayReply(){
  const text = ($('aiReplyText')?.value || '').trim();

  if(!text){
    aiSetStatus('No draft reply to play.');
    return;
  }

  aiSetStatus('Playing draft reply through CW generator...');

  try{
    const payload = {
      text,
      tone_hz:Number($('cwTone')?.value || $('setTone')?.value || 700),
      wpm:Number($('cwWpm')?.value || $('setWpm')?.value || 18.75),
      farnsworth_wpm:Number($('cwFarnsworth')?.value || $('cwWpm')?.value || $('setWpm')?.value || 18.75),
      key_profile:$('cwKeyProfile')?.value || 'computer',
      start_delay_ms:Number($('cwStartDelay')?.value || 0),
      end_gap_ms:Number($('cwEndGap')?.value || 1000),
      playback_mode:$('cwPlaybackMode')?.value || 'sound',
      output_device:$('setOutputDevice')?.value || 'plughw:2,0',
      volume_percent:Number($('cwVolume')?.value || 35)
    };

    const result = await fetch('/api/cw/play', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify(payload)
    }).then(r=>r.json());

    if(!result.ok){
      throw new Error(result.error || 'CW generator failed');
    }

    aiSetStatus('Draft reply is playing as CW audio. Review before any RF transmit.', true);
  }catch(e){
    aiSetStatus('Play reply failed: ' + e);
  }
}

async function aiResetQso(){
  try{
    const result = await fetch('/api/ai/qso/reset', {method:'POST'}).then(r=>r.json());
    mwAiLastAnalysis = null;
    mwAiLastReply = null;
    $('aiIntent').textContent = '--';
    $('aiTheirCall').textContent = '--';
    $('aiConfidence').textContent = '--';
    $('aiReplyText').value = '';
    $('aiPlainEnglish').textContent = 'QSO context reset.';
    aiSetStatus(result.ok ? 'QSO context reset.' : 'QSO reset may have failed.', !!result.ok);
  }catch(e){
    aiSetStatus('QSO reset failed: ' + e);
  }
}

async function aiLoadContext(){
  try{
    const ctx = await fetch('/api/ai/context?ts=' + Date.now(), {cache:'no-store'}).then(r=>r.json());
    aiUpdateProviderBadge(ctx || {});
    if(ctx && ctx.qso_state){
      $('aiTheirCall').textContent = ctx.qso_state.their_call || '--';
      $('aiIntent').textContent = ctx.qso_state.stage || '--';
    }
  }catch(e){
    // Keep quiet. This is an assist card only.
  }
}



/* MW_AI_REALTIME_ASSIST_CLIPBOARD_V1 */
let mwAiRealtimeLastCopy = '';
let mwAiRealtimeLastCallAt = 0;
let mwAiRealtimeBusy = false;

function aiRealtimeEnabled(cfg){
  return !!(
    cfg &&
    cfg.ai_enabled === true &&
    cfg.ai_realtime_assist === true
  );
}

async function aiMaybeRealtimeAssist(copy, cfg){
  copy = String(copy || '').trim();

  if(!copy) return;
  if(!aiRealtimeEnabled(cfg)) return;
  if(copy === mwAiRealtimeLastCopy) return;
  if(mwAiRealtimeBusy) return;

  const now = Date.now();

  // Avoid API hammering if the held copy flickers or updates quickly.
  const minGapMs = Number((cfg && cfg.ai_realtime_min_gap_ms) || 12000);
  if(now - mwAiRealtimeLastCallAt < minGapMs) return;

  mwAiRealtimeBusy = true;
  mwAiRealtimeLastCallAt = now;
  mwAiRealtimeLastCopy = copy;

  aiSetStatus('Auto notes: reading new stable copy...');

  try{
    const result = await fetch('/api/ai/reply', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({text:copy, source:'realtime_stable_copy'})
    }).then(r=>r.json());

    if(!result.ok){
      throw new Error(result.error || 'auto-assist failed');
    }

    aiRenderAnalysis(result.analysis);
    aiRenderReply(result.reply);

    const provider = (result.reply && result.reply.provider) || (result.analysis && result.analysis.provider) || 'local';
    const fallback = (result.reply && result.reply.fallback_used) || (result.analysis && result.analysis.fallback_used);
    aiSetStatus('Auto notes updated from new stable copy. Source: ' + provider + (fallback ? ' - fallback used' : '') + '. Review before transmit.', true);
  }catch(e){
    aiSetStatus('Auto notes failed: ' + e);
  }finally{
    mwAiRealtimeBusy = false;
  }
}


function updateToneRanking(ranking){
  const list=(ranking||[]).slice(0,10);
  if(!list.length){
    $('tones').textContent='Waiting for tone scan...';
    return;
  }
  const max=Math.max(...list.map(x=>Number(x.score||0)), 0.0000001);
  $('tones').innerHTML=list.map((t,i)=>{
    const width=(Number(t.score||0)/max)*100;
    return `<div class="toneRow">
      <div class="toneLabel">${t.tone_hz} Hz</div>
      <div class="toneMini"><div style="width:${width}%"></div></div>
      <div>${Number(t.score||0).toExponential(2)}</div>
    </div>`;
  }).join('');
}

const MORSE_MAP={
  A:'.-',B:'-...',C:'-.-.',D:'-..',E:'.',F:'..-.',G:'--.',H:'....',I:'..',J:'.---',
  K:'-.-',L:'.-..',M:'--',N:'-.',O:'---',P:'.--.',Q:'--.-',R:'.-.',S:'...',T:'-',
  U:'..-',V:'...-',W:'.--',X:'-..-',Y:'-.--',Z:'--..',
  1:'.----',2:'..---',3:'...--',4:'....-',5:'.....',6:'-....',7:'--...',8:'---..',9:'----.',0:'-----',
  '.':'.-.-.-', ',':'--..--', '?':'..--..', '/':'-..-.', '=':'-...-', '+':'.-.-.', '-':'-....-'
};
function showControlTab(name){
  const settings=name==='settings';
  const generator=name==='generator';
  const network=name==='network';

  $('tabSettings')?.classList.toggle('active',settings);
  $('tabGenerator')?.classList.toggle('active',generator);
  $('tabNetwork')?.classList.toggle('active',network);

  $('tabSettingsBtn')?.classList.toggle('active',settings);
  $('tabGeneratorBtn')?.classList.toggle('active',generator);
  $('tabNetworkBtn')?.classList.toggle('active',network);

  if(network) loadNetworkStatus();
}

function setPlaybackMode(mode){
  if(mode!=='sound'){
    $('settingsMsg').textContent='Only Sound playback is active on this hardware today.';
    return;
  }
  $('cwPlaybackMode').value='sound';
  $('playbackSound')?.classList.add('active');
  $('playbackLight')?.classList.remove('active');
  $('playbackVibrate')?.classList.remove('active');
}
function toggleTrainerAdvanced(){
  const show=$('cwAdvancedToggle')?.value==='on';
  $('advancedTrainer')?.classList.toggle('active',show);
}
function setTrainerPreset(text){
  $('cwText').value=text;
  updateCwPreview();
}

function updateCwPreview(){
  const src=($('cwText')?.value||'').toUpperCase().trim();
  const out=[];
  for(const word of src.split(/\s+/)){
    const letters=[];
    for(const ch of word){
      if(MORSE_MAP[ch]) letters.push(MORSE_MAP[ch]);
    }
    if(letters.length) out.push(letters.join(' '));
  }
  if($('cwPreview')) $('cwPreview').textContent=out.join('   ') || '...';
}


function updateToneModeHelp(){
  const mode=$('setToneMode')?.value || 'session_auto';
  const el=$('toneModeHelp');
  if(!el) return;

  if(mode==='session_auto'){
    el.textContent='Full auto scans for the CW tone at the start of a session, then locks it. Best default for live radio.';
  }else if(mode==='auto'){
    el.textContent='Continuous auto keeps following the strongest tone live. Useful for testing, but may jump if noise or harmonics are stronger.';
  }else{
    el.textContent='Manual fixed tone uses the selected tone only. Best for learning, controlled tests, and training.';
  }
}

async function loadSettings(){
  try{
    const r=await fetch('/api/settings?ts='+Date.now(),{cache:'no-store'});
    const s=await r.json();
    const cfg=s.config||{};
    $('setToneMode').value=cfg.tone_mode||'session_auto';
    updateToneModeHelp();
    $('setTone').value=cfg.target_tone_hz||700;
    $('setWpm').value=cfg.initial_wpm||18.75;
    $('setInputLevel').value=cfg.input_capture_percent ?? 70;
    $('setInputLevelVal').textContent=$('setInputLevel').value;
    if ($('setAudioFilterMode')) {
      $('setAudioFilterMode').value = (cfg.audio_filter_enabled === false) ? 'off' : (cfg.audio_filter_mode || 'wide');
    }
    if ($('setAudioFilterBandwidth')) {
      $('setAudioFilterBandwidth').value = cfg.audio_filter_bandwidth_hz ?? 300;
    }
    $('setLcdBrightness').value=cfg.lcd_brightness_percent ?? 55;
    $('setLcdBrightnessVal').textContent=$('setLcdBrightness').value;
    $('setTftIdleEnabled').value=String(cfg.tft_screen_timeout_enabled !== false);
    $('setTftIdleSeconds').value=cfg.tft_screen_timeout_sec ?? 300;
    $('setOutputDevice').value=cfg.audio_output_device||'plughw:2,0';
    if ($('setAiEnabled')) $('setAiEnabled').value=String(cfg.ai_enabled===true);
    if ($('setAiProvider')) $('setAiProvider').value=cfg.ai_provider||'local';
    if ($('setAiModel')) $('setAiModel').value=cfg.ai_model||'gpt-4.1-mini';
    if ($('setAiRealtimeAssist')) $('setAiRealtimeAssist').value=String(cfg.ai_realtime_assist===true);
    updateFilterToggleButton(cfg);
    $('cwTone').value=cfg.cw_generator_tone_hz || cfg.target_tone_hz || 700;
    $('cwWpm').value=cfg.cw_generator_wpm || cfg.initial_wpm || 18.75;
    $('cwFarnsworth').value=cfg.cw_generator_farnsworth_wpm || cfg.cw_generator_wpm || cfg.initial_wpm || 18.75;
    $('cwKeyProfile').value=cfg.cw_generator_key_profile || 'computer';
    $('cwStartDelay').value=cfg.cw_generator_start_delay_ms ?? 0;
    $('cwEndGap').value=cfg.cw_generator_end_gap_ms ?? 1000;
    $('cwPlaybackMode').value=cfg.cw_generator_playback_mode || 'sound';
    $('cwVolume').value=cfg.cw_generator_volume_percent ?? 35;
    $('cwVolumeVal').textContent=$('cwVolume').value;
    updateCwPreview();
  }catch(e){
    $('settingsMsg').textContent='Settings load failed: '+e;
  }
}
$('setToneMode')?.addEventListener('change',updateToneModeHelp);
$('setInputLevel')?.addEventListener('input',()=>{$('setInputLevelVal').textContent=$('setInputLevel').value});
$('setLcdBrightness')?.addEventListener('input',()=>{$('setLcdBrightnessVal').textContent=$('setLcdBrightness').value});
$('cwVolume')?.addEventListener('input',()=>{$('cwVolumeVal').textContent=$('cwVolume').value});
$('cwText')?.addEventListener('input',updateCwPreview);
$('cwTone')?.addEventListener('input',updateCwPreview);
$('cwWpm')?.addEventListener('input',updateCwPreview);
$('cwFarnsworth')?.addEventListener('input',updateCwPreview);
$('cwKeyProfile')?.addEventListener('change',updateCwPreview);
$('cwAdvancedToggle')?.addEventListener('change',toggleTrainerAdvanced);

async function saveSettings(){
  const payload={
    tone_mode:$('setToneMode').value,
    target_tone_hz:Number($('setTone').value),
    initial_wpm:Number($('setWpm').value),
    input_capture_percent:Number($('setInputLevel').value),
    audio_filter_enabled:$('setAudioFilterMode') ? ($('setAudioFilterMode').value !== 'off') : true,
    audio_filter_mode:$('setAudioFilterMode') ? $('setAudioFilterMode').value : 'wide',
    audio_filter_bandwidth_hz:$('setAudioFilterBandwidth') ? Math.max(80,Math.min(1200,Number($('setAudioFilterBandwidth').value||300))) : 300,
    lcd_brightness_percent:Number($('setLcdBrightness').value),
    tft_screen_timeout_enabled:$('setTftIdleEnabled').value==='true',
    tft_screen_timeout_sec:Math.max(15,Math.min(3600,Number($('setTftIdleSeconds').value||300))),
    tft_screen_timeout_image:'/opt/morse-whisperer-pi/assets/horse_boot_splash.png',
    audio_output_device:$('setOutputDevice').value,
    ai_enabled:$('setAiEnabled') ? ($('setAiEnabled').value==='true') : false,
    ai_provider:$('setAiProvider') ? $('setAiProvider').value : 'local',
    ai_model:$('setAiModel') ? $('setAiModel').value : 'gpt-4.1-mini',
    ai_realtime_assist:$('setAiRealtimeAssist') ? ($('setAiRealtimeAssist').value==='true') : false,
    ai_require_confirmation:true,
    volume_percent:Number($('cwVolume').value),
    cw_generator_tone_hz:Number($('cwTone').value),
    cw_generator_wpm:Number($('cwWpm').value),
    cw_generator_farnsworth_wpm:Number($('cwFarnsworth').value),
    cw_generator_key_profile:$('cwKeyProfile').value,
    cw_generator_start_delay_ms:Number($('cwStartDelay').value),
    cw_generator_end_gap_ms:Number($('cwEndGap').value),
    cw_generator_playback_mode:$('cwPlaybackMode').value,
    cw_generator_volume_percent:Number($('cwVolume').value)
  };
  const r=await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  const s=await r.json();
  $('settingsMsg').textContent=s.ok ? 'Saved. Some settings apply immediately; decoder service restart is not required.' : ('Save failed: '+(s.error||'unknown'));
  $('settingsState').className='badge '+(s.ok?'good':'bad');
}
async function playCw(){
  const payload={
    text:$('cwText').value,
    tone_hz:Number($('cwTone').value),
    wpm:Number($('cwWpm').value),
    farnsworth_wpm:Number($('cwFarnsworth').value),
    key_profile:$('cwKeyProfile').value,
    start_delay_ms:Number($('cwStartDelay').value),
    end_gap_ms:Number($('cwEndGap').value),
    playback_mode:$('cwPlaybackMode').value,
    output_device:$('setOutputDevice').value,
    volume_percent:Number($('cwVolume').value)
  };
  const r=await fetch('/api/cw/play',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  const s=await r.json();
  $('settingsMsg').textContent=s.ok ? 'CW generator playing.' : ('CW play failed: '+(s.error||'unknown'));
  $('settingsState').className='badge '+(s.ok?'good':'bad');
}
async function stopCw(){
  const r=await fetch('/api/cw/stop',{method:'POST'});
  const s=await r.json();
  $('settingsMsg').textContent=s.ok ? 'CW generator stopped.' : ('Stop failed: '+(s.error||'unknown'));
}
async function selfTestCw(){
  const payload={
    text:$('cwText').value,
    tone_hz:Number($('cwTone').value),
    wpm:Number($('cwWpm').value),
    farnsworth_wpm:Number($('cwFarnsworth')?.value || $('cwWpm').value),
    key_profile:$('cwKeyProfile')?.value || 'computer',
    start_delay_ms:Number($('cwStartDelay')?.value || 0),
    end_gap_ms:Number($('cwEndGap')?.value || 1000),
    volume_percent:Number($('cwVolume').value)
  };

  const box=$('selfTestResult');
  box.className='selfTestResult';
  box.textContent='Generating CW and running decoder self-test...';

  const r=await fetch('/api/cw/selftest',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  const s=await r.json();

  if(!s.ok){
    box.className='selfTestResult bad';
    box.textContent='Self-test failed: '+(s.error||'unknown');
    return;
  }

  const cls=s.status==='PASS' ? 'good' : (s.status==='CLOSE' ? 'warn' : 'bad');
  box.className='selfTestResult '+cls;
  box.innerHTML=
    '<b>Self-test: '+s.status+'</b>'+
    '<div class="selfTestMono">'+
    'Expected: '+(s.expected||'')+'\\n'+
    'Decoded : '+(s.decoded||'')+'\\n'+
    'Raw     : '+(s.raw||'')+'\\n'+
    'Tone    : '+s.tone_hz+' Hz\\n'+
    'WPM     : '+Number(s.wpm||0).toFixed(2)+' / Farnsworth '+Number(s.farnsworth_wpm||0).toFixed(2)+'\\n'+
    'SNR     : '+Number(s.snr_db||0).toFixed(1)+' dB\\n'+
    'Conf    : '+Number(s.confidence||0).toFixed(2)+
    '</div>';

  $('settingsMsg').textContent='CW self-test complete: '+s.status;
}
async function resetDefaults(){
  if(!confirm('Reset Morse Whisperer settings to safe defaults?')) return;
  const r=await fetch('/api/settings/defaults',{method:'POST'});
  const s=await r.json();
  $('settingsMsg').textContent=s.ok ? 'Defaults restored and saved.' : ('Reset failed: '+(s.error||'unknown'));
  await loadSettings();
aiLoadContext();
}

function renderConnections(conns){
  if(!conns || !conns.length){
    $('netConnections').textContent='No saved connections reported.';
    return;
  }
  $('netConnections').innerHTML=conns.map(c=>`
    <div class="networkRow">
      <b>${esc(c.name||'--')}</b>
      <span>${esc(c.type||'--')}</span>
      <span>${esc(c.device||'--')}</span>
    </div>
  `).join('');
}

async function loadNetworkStatus(){
  try{
    const r=await fetch('/api/network/status?ts='+Date.now(),{cache:'no-store'});
    const s=await r.json();

    if(!s.ok){
      $('settingsMsg').textContent='Network status failed: '+(s.error||'unknown');
      return;
    }

    $('netHostname').textContent=s.hostname||'--';
    $('netIps').textContent=(s.ip_addresses||[]).join(' ') || '--';
    $('netDefaultRoute').textContent=s.default_route ? 'yes' : 'no';
    $('netWifiDevice').textContent=s.wifi_device||'--';
    $('netActiveWifi').textContent=s.active_wifi_connection||'--';
    $('netHotspotActive').textContent=s.hotspot_active ? 'yes' : 'no';
    $('netFallbackService').textContent=(s.fallback_service_active||'unknown')+' / '+(s.fallback_service_enabled||'unknown');
    $('netSetupSsid').textContent=s.setup_ssid||'The Morse Whisperer';
    $('netSetupUrl').textContent='http://'+(s.setup_ip||'10.42.0.1')+':8080';

    renderConnections(s.connections||[]);
    $('settingsMsg').textContent='Network status refreshed.';
  }catch(e){
    $('settingsMsg').textContent='Network status failed: '+e;
  }
}

function renderWifiNetworks(nets){
  const list=$('wifiScanList');
  if(!list) return;
  list.innerHTML='';

  nets.forEach((n)=>{
    const row=document.createElement('div');
    row.className='networkRow';

    const ssid=n.ssid || '';
    const label=document.createElement('b');
    label.textContent=(n.in_use ? '* ' : '') + (ssid || '(hidden)');

    const sig=document.createElement('span');
    sig.textContent=Number(n.signal||0)+'%';

    const sec=document.createElement('span');
    sec.textContent=n.security || 'open';

    const chan=document.createElement('span');
    chan.textContent='ch '+(n.channel || '--');

    const action=document.createElement('span');
    const btn=document.createElement('button');
    btn.type='button';
    btn.className='networkUseBtn';
    btn.textContent='Connect';
    btn.dataset.ssid=ssid;
    btn.addEventListener('click',()=>{
      const target=$('netConnectSsid');
      if(!target) return;
      target.value=btn.dataset.ssid || '';
      if(!target.value){
        $('settingsMsg').textContent='Hidden network selected. Type the SSID manually.';
        target.focus();
        return;
      }
      $('settingsMsg').textContent='Selected Wi-Fi SSID: '+target.value;
      const pass=$('netConnectPassword');
      if(pass) pass.focus();
    });
    action.appendChild(btn);

    row.appendChild(label);
    row.appendChild(sig);
    row.appendChild(sec);
    row.appendChild(chan);
    row.appendChild(action);
    list.appendChild(row);
  });
}

async function connectWifiManual(){
  const ssid=($('netConnectSsid')?.value||'').trim();
  const password=$('netConnectPassword')?.value||'';

  if(!ssid){
    $('settingsMsg').textContent='Enter a Wi-Fi SSID first.';
    return;
  }

  const warning=
    'Connect this Pi to Wi-Fi network "'+ssid+'"?\n\n'+
    'This may disconnect the current browser or SSH session if the Pi changes networks.\n\n'+
    'Continue?';

  if(!confirm(warning)){
    $('settingsMsg').textContent='Wi-Fi connect cancelled.';
    return;
  }

  $('settingsMsg').textContent='Connecting to Wi-Fi "'+ssid+'"...';

  try{
    const r=await fetch('/api/network/connect',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({ssid:ssid,password:password})
    });

    const s=await r.json();

    if(!s.ok){
      $('settingsMsg').textContent='Wi-Fi connect failed: '+(s.error||'unknown')+(s.rollback_attempted?' Rollback was attempted.':'');
      return;
    }

    $('settingsMsg').textContent='Connected to '+ssid+'. IP address(es): '+((s.ip_addresses||[]).join(' ')||'checking...');
    setTimeout(loadNetworkStatus,3000);
  }catch(e){
    $('settingsMsg').textContent='Connection request sent, but browser lost contact. Check the Pi IP address or reconnect to the correct network.';
  }
}

async function scanWifi(){
  $('wifiScanList').textContent='Scanning...';
  try{
    const r=await fetch('/api/network/scan?ts='+Date.now(),{cache:'no-store'});
    const s=await r.json();

    if(!s.ok){
      $('wifiScanList').textContent='Scan failed: '+(s.error||'unknown');
      return;
    }

    const nets=s.networks||[];
    if(!nets.length){
      $('wifiScanList').textContent='No networks found.';
      return;
    }

    renderWifiNetworks(nets);
    $('settingsMsg').textContent='Wi-Fi scan complete.';
  }catch(e){
    $('wifiScanList').textContent='Scan failed: '+e;
  }
}

async function tick(){
  try{
    const r=await fetch('/api/snapshot?ts='+Date.now(),{cache:'no-store'});
    const s=await r.json();
    const d=s.decode||{}, q=s.quality||{}, a=s.audio||{}, cfg=s.config||{};
    updateFilterToggleButton(cfg);

    const copy=esc(d.stable_copy || d.copy || '').trim();
    const raw=esc(d.stable_raw || d.raw || '').trim();

    aiMaybeRealtimeAssist(copy, cfg);

    $('copy').textContent=copy || 'Waiting for CW...';
    $('copy').classList.toggle('empty', !copy);
    $('raw').textContent=raw || 'No accepted raw copy yet.';

    const age=s.updated_at ? ((Date.now()/1000)-s.updated_at) : 0;
    $('age').textContent=num(age,1)+'s ago';
    $('mode').textContent=s.mode||'unknown';
    $('device').textContent=((a.backend||'')+':'+(a.device||'')).replace(/^:/,'--');
    $('squelch').textContent=q.squelch_open ? 'OPEN' : 'closed';

    const goodMode=(s.mode==='running');
    $('modeDot').className='dot '+(goodMode?'good':'warn');

    const conf=Number(q.confidence||0);
    const snr=Number(q.snr_db||0);
    const cls=reasonClass(q.reason,conf,snr);
    $('acceptedBadge').className='badge '+(copy?'good':'');
    $('acceptedBadge').textContent=copy?'accepted / held':'waiting';

    const toneLock=q.live_tone_lock_hz || q.selected_tone_hz || '--';
    $('toneLock').textContent=toneLock;
    $('toneReason').textContent=q.live_tone_lock_reason || q.reason || 'Waiting for signal';
    $('toneModeBadge').textContent=(q.live_mode||cfg.tone_mode||'--').replaceAll('_',' ');
    $('toneModeBadge').className='badge '+(q.squelch_open?'good':'');

    setBar('snrBar',pct(snr,-5,45), snr<6?'bad':snr<12?'warn':'');
    setBar('confBar',pct(conf,0,1), conf<0.45?'bad':conf<0.85?'warn':'');
    setBar('rmsBar',pct(Number(a.rms||0),0,0.09));
    setBar('peakBar',pct(Number(a.peak||0),0,0.6), Number(a.clipping_percent||0)>0?'bad':'');

    $('snrVal').textContent=num(snr,1)+' dB';
    $('confVal').textContent=num(conf,2);
    $('rmsVal').textContent=num(a.rms,3);
    $('peakVal').textContent=num(a.peak,3);

    const level=a.level_status||'--';
    $('levelBadge').className='badge '+levelClass(level);
    $('levelBadge').textContent='Audio '+level;

    $('selectedTone').textContent=(q.selected_tone_hz||'--')+' Hz';
    $('targetTone').textContent=(q.target_tone_hz||cfg.target_tone_hz||'--')+' Hz';
    $('wpm').textContent=num(q.wpm,1);
    $('reason').innerHTML=`<span class="badge ${cls}">${q.reason||'--'}</span>`;
    $('session').textContent=`${num(q.live_session_seconds,1)}s - quiet ${num(q.quiet_for_sec,1)}s`;
    $('buffer').textContent=`${num(a.buffered_seconds,1)}s - trims ${a.overruns||0}`;

    updateToneRanking(q.tone_ranking);

    const cand=(d.candidate_copy || d.candidate_raw || '').trim();
    $('candidate').textContent=cand || 'No rejected candidate shown.';

    $('log').textContent=(s.status||[])
      .slice(-14)
      .map(x=>new Date(x.time*1000).toLocaleTimeString()+'  '+x.message)
      .join('\n') || 'No status messages yet.';
  }catch(e){
    $('mode').textContent='offline';
    $('modeDot').className='dot bad';
    $('log').textContent='UI update failed: '+e;
  }
}
setInterval(tick,800);
tick();
loadSettings();
</script>







<script>
/* MW_CENTER_SCALE_WATERMARK_V2 */
(function(){
  function installSplashWatermark(){
    const oldIds = ['mwHorseWatermark', 'mwHorseWatermarkGlow'];
    for (const id of oldIds) {
      const el = document.getElementById(id);
      if (el) el.remove();
    }

    if (document.getElementById('mwSplashWatermark')) return;

    const wm = document.createElement('div');
    wm.id = 'mwSplashWatermark';
    wm.setAttribute('aria-hidden', 'true');
    document.body.prepend(wm);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', installSplashWatermark);
  } else {
    installSplashWatermark();
  }
})();
</script>


<script>
/* MW_DECODER_PROFILE_UI_PHASE2_SAFE */
(function(){
  async function getProfile(){
    const r = await fetch('/api/decoder/profile', {cache:'no-store'});
    if(!r.ok) throw new Error('GET /api/decoder/profile failed');
    return await r.json();
  }

  async function setProfile(profile){
    const r = await fetch('/api/decoder/profile', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({profile:profile, restart:true})
    });
    const data = await r.json().catch(() => ({}));
    if(!r.ok || !data.ok) throw new Error(data.error || 'Profile switch failed');
    return data;
  }

  function makePanel(){
    if(document.getElementById('mwDecoderProfilePanel')) return;

    const panel = document.createElement('div');
    panel.id = 'mwDecoderProfilePanel';
    panel.style.cssText = [
      'border:1px solid rgba(148,163,184,.35)',
      'border-radius:14px',
      'padding:12px',
      'margin:12px 0',
      'background:rgba(15,23,42,.72)',
      'box-shadow:0 8px 22px rgba(0,0,0,.20)'
    ].join(';');

    panel.innerHTML = `
      <div style="font-weight:700;margin-bottom:8px;">Decoder Profile</div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
        <select id="mwDecoderProfileSelect" style="padding:8px;border-radius:8px;">
          <option value="clean">Clean CW</option>
          <option value="kiwi">Radio CW</option>
        </select>
        <button id="mwDecoderProfileApply" type="button" style="padding:8px 12px;border-radius:8px;cursor:pointer;">Apply & Restart</button>
      </div>
      <div id="mwDecoderProfileStatus" style="font-size:12px;opacity:.86;margin-top:8px;">Loading profile...</div>
    `;

    const target =
      document.querySelector('#settings') ||
      document.querySelector('.settings') ||
      document.querySelector('main') ||
      document.querySelector('.wrap') ||
      document.body;

    target.prepend(panel);

    document.getElementById('mwDecoderProfileApply').addEventListener('click', async () => {
      const select = document.getElementById('mwDecoderProfileSelect');
      const status = document.getElementById('mwDecoderProfileStatus');
      const profile = select.value;

      status.textContent = 'Applying ' + profile + ' profile and restarting...';

      try {
        await setProfile(profile);
        status.textContent = 'Profile saved. Service restarting and clearing decoder. Reloading shortly...';
        setTimeout(() => location.reload(), 9000);
      } catch(e) {
        status.textContent = 'Profile switch failed: ' + e.message;
      }
    });
  }

  async function refreshPanel(){
    makePanel();
    const select = document.getElementById('mwDecoderProfileSelect');
    const status = document.getElementById('mwDecoderProfileStatus');

    try {
      const p = await getProfile();
      select.value = p.decoder_profile || 'clean';

      let toneRange = 'tones unknown';
      if(Array.isArray(p.allowed_tones_hz) && p.allowed_tones_hz.length){
        toneRange = p.allowed_tones_hz[0] + '-' + p.allowed_tones_hz[p.allowed_tones_hz.length - 1] + ' Hz';
      }

      const friendlyName = (p.decoder_profile === 'kiwi') ? 'Radio CW' : ((p.decoder_profile === 'clean') ? 'Clean CW' : (p.decoder_profile || 'unknown'));
      status.textContent =
        'Active: ' + friendlyName +
        ' | mode: ' + (p.tone_mode || '?') +
        ' | target: ' + (p.target_tone_hz || '?') + ' Hz' +
        ' | filter: ' + (p.audio_filter_mode || '?') +
        ' | ' + toneRange;
    } catch(e) {
      status.textContent = 'Profile status unavailable: ' + e.message;
    }
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', refreshPanel);
  } else {
    refreshPanel();
  }
})();
</script>

</body>
</html>
"""


def no_cache_response(body: str, mimetype: str) -> Response:
    return Response(
        body,
        mimetype=mimetype,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


def create_app(state, ring, config: Dict) -> Flask:
    app = Flask(__name__)
    install_ai_routes(app, state, config)

    @app.route("/")
    def index():
        return no_cache_response(HTML, "text/html")

    @app.route("/api/decode/history")
    def decode_history():
        snap = state.snapshot()
        return jsonify({
            "ok": True,
            "history": snap.get("decode_history", []),
        })


    @app.route("/assets/<path:filename>")
    def mw_assets(filename):
        return send_from_directory("/opt/morse-whisperer-pi/assets", filename)


    @app.route("/api/snapshot")
    def snapshot():
        resp = jsonify(state.snapshot())
        resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.route("/api/reset", methods=["POST"])
    def reset():
        now = time.time()

        # Clear the web-facing ring immediately.
        ring.clear()

        snap = state.snapshot()
        dec = snap.get("decode", {})
        dec.update({
            "raw": "",
            "copy": "",
            "stable_copy": "",
            "stable_raw": "",
            "candidate_raw": "",
            "candidate_copy": "",
            "events": [],
            "accepted": False,
            "live_mode": "reset",
        })

        control = snap.get("control", {})
        if not isinstance(control, dict):
            control = {}
        control["reset_requested_at"] = now
        control["reset_counter"] = int(control.get("reset_counter", 0)) + 1

        q = snap.get("quality", {})
        if not isinstance(q, dict):
            q = {}
        q.update({
            "reason": "reset_requested",
            "squelch_open": False,
            "live_session_seconds": 0,
            "live_session_samples": 0,
            "live_tone_lock_hz": None,
            "live_tone_lock_reason": "reset",
        })

        state.update(decode=dec, quality=q, control=control, mode="reset")
        state.append_status("Reset requested from web UI")
        return jsonify({"ok": True, "reset_counter": control["reset_counter"], "reset_requested_at": now})

    @app.route("/api/tone/scan", methods=["POST"])
    def tone_scan():
        now = time.time()

        snap = state.snapshot()
        control = snap.get("control", {})
        if not isinstance(control, dict):
            control = {}

        control["tone_scan_requested_at"] = now
        control["tone_scan_counter"] = int(control.get("tone_scan_counter", 0)) + 1

        q = snap.get("quality", {})
        if not isinstance(q, dict):
            q = {}

        q.update({
            "live_tone_lock_hz": None,
            "live_tone_lock_reason": "manual_scan_requested",
            "reason": "manual_tone_scan_requested",
        })

        state.update(control=control, quality=q)
        state.append_status("Manual tone scan requested")

        return jsonify({
            "ok": True,
            "tone_scan_counter": control["tone_scan_counter"],
            "tone_scan_requested_at": now,
        })

    @app.route("/api/tft/next", methods=["POST"])
    def tft_next():
        now = time.time()
        snap = state.snapshot()
        control = snap.get("control", {})
        if not isinstance(control, dict):
            control = {}
        control["tft_next_page_requested_at"] = now
        control["tft_next_page_counter"] = int(control.get("tft_next_page_counter", 0)) + 1
        state.update(control=control)
        state.append_status("TFT next page requested")
        return jsonify({"ok": True, "tft_next_page_counter": control["tft_next_page_counter"]})

    @app.route("/api/tft/freeze", methods=["POST"])
    def tft_freeze():
        now = time.time()
        snap = state.snapshot()
        control = snap.get("control", {})
        if not isinstance(control, dict):
            control = {}
        control["tft_freeze_requested_at"] = now
        control["tft_freeze_counter"] = int(control.get("tft_freeze_counter", 0)) + 1
        state.update(control=control)
        state.append_status("TFT freeze toggle requested")
        return jsonify({"ok": True, "tft_freeze_counter": control["tft_freeze_counter"]})


    # MW_FILTER_BUTTON_API_V1
    FILTER_MODE_ORDER = ["off", "wide", "narrow", "custom"]

    def filter_mode_summary():
        enabled = bool(config.get("audio_filter_enabled", True))
        mode = str(config.get("audio_filter_mode", "wide") or "wide").lower()

        if not enabled:
            mode = "off"

        if mode not in FILTER_MODE_ORDER:
            mode = "wide"

        if mode == "off":
            enabled = False
        else:
            enabled = True

        return {
            "ok": True,
            "audio_filter_enabled": enabled,
            "audio_filter_mode": mode,
            "audio_filter_wide_hz": int(config.get("audio_filter_wide_hz", 500)),
            "audio_filter_narrow_hz": int(config.get("audio_filter_narrow_hz", 220)),
            "audio_filter_bandwidth_hz": int(config.get("audio_filter_bandwidth_hz", 300)),
            "audio_filter_max_hz": int(config.get("audio_filter_max_hz", 1200)),
        }

    def set_filter_mode(mode: str):
        mode = str(mode or "wide").lower()
        if mode not in FILTER_MODE_ORDER:
            mode = "wide"

        config["audio_filter_enabled"] = mode != "off"
        config["audio_filter_mode"] = mode
        config.setdefault("audio_filter_wide_hz", 500)
        config.setdefault("audio_filter_narrow_hz", 220)
        config.setdefault("audio_filter_bandwidth_hz", 300)
        config.setdefault("audio_filter_max_hz", 1200)

        save_config(config)
        state.update(config=config)

        snap = state.snapshot()
        control = snap.get("control", {})
        if not isinstance(control, dict):
            control = {}
        control["bandwidth_filter_changed_at"] = time.time()
        control["bandwidth_filter_counter"] = int(control.get("bandwidth_filter_counter", 0)) + 1
        control["bandwidth_filter_mode"] = mode
        state.update(control=control)

        state.append_status(f"Bandwidth filter set to {mode}")
        data = filter_mode_summary()
        data["counter"] = control["bandwidth_filter_counter"]
        return data

    def step_filter_mode(direction: int):
        current = filter_mode_summary()["audio_filter_mode"]
        try:
            idx = FILTER_MODE_ORDER.index(current)
        except ValueError:
            idx = 1

        idx = (idx + int(direction)) % len(FILTER_MODE_ORDER)
        return set_filter_mode(FILTER_MODE_ORDER[idx])

    @app.route("/api/filter/status")
    def filter_status():
        return jsonify(filter_mode_summary())

    @app.route("/api/filter/up", methods=["POST"])
    def filter_up():
        return jsonify(step_filter_mode(+1))

    @app.route("/api/filter/down", methods=["POST"])
    def filter_down():
        return jsonify(step_filter_mode(-1))

    @app.route("/api/filter/set", methods=["POST"])
    def filter_set():
        data = request.get_json(silent=True) or {}
        return jsonify(set_filter_mode(str(data.get("mode", "wide"))))


    SETTINGS_ALLOWLIST = {
        "tone_mode": str,
        "target_tone_hz": int,
        "initial_wpm": float,
        "input_capture_percent": int,
        "audio_filter_enabled": bool,
        "audio_filter_mode": str,
        "audio_filter_bandwidth_hz": int,
        "audio_filter_wide_hz": int,
        "audio_filter_narrow_hz": int,
        "audio_filter_max_hz": int,
        "lcd_brightness_percent": int,
        "tft_screen_timeout_enabled": bool,
        "tft_screen_timeout_sec": int,
        "tft_screen_timeout_image": str,
        "audio_output_device": str,
        "ai_enabled": bool,
        "ai_provider": str,
        "ai_model": str,
        "ai_realtime_assist": bool,
        "ai_require_confirmation": bool,
        "ai_reply_style": str,
        "ai_operator_callsign": str,
        "ai_operator_name": str,
        "ai_operator_qth": str,
        "cw_generator_tone_hz": int,
        "cw_generator_wpm": float,
        "cw_generator_farnsworth_wpm": float,
        "cw_generator_key_profile": str,
        "cw_generator_start_delay_ms": int,
        "cw_generator_end_gap_ms": int,
        "cw_generator_playback_mode": str,
        "cw_generator_volume_percent": int,
    }

    SAFE_DEFAULTS = {
        "target_tone_hz": 700,
        "tone_mode": "session_auto",
        "initial_wpm": 18.75,
        "threshold_bias": 0.48,
        "window_ms": 12,
        "hop_ms": 8,
        "decode_window_sec": 10,
        "char_gap_units": 2.25,
        "word_gap_units": 6.0,
        "adaptive_word_gap_enabled": False,
        "audio_output_device": "plughw:2,0",
        "ai_enabled": False,
        "ai_provider": "local",
        "ai_model": "gpt-4.1-mini",
        "ai_realtime_assist": False,
        "ai_require_confirmation": True,
        "ai_reply_style": "short_cw",
        "ai_operator_callsign": "N0CALL",
        "ai_operator_name": "SEAN",
        "ai_operator_qth": "NAPIER",
        "input_capture_percent": 70,
        "audio_filter_enabled": True,
        "audio_filter_mode": "wide",
        "audio_filter_wide_hz": 500,
        "audio_filter_narrow_hz": 220,
        "audio_filter_bandwidth_hz": 300,
        "audio_filter_max_hz": 1200,
        "lcd_brightness_percent": 55,
        "tft_screen_timeout_enabled": True,
        "tft_screen_timeout_sec": 300,
        "tft_screen_timeout_image": "/opt/morse-whisperer-pi/assets/horse_boot_splash.png",
        "cw_generator_tone_hz": 700,
        "cw_generator_wpm": 18.75,
        "cw_generator_farnsworth_wpm": 18.75,
        "cw_generator_key_profile": "computer",
        "cw_generator_start_delay_ms": 0,
        "cw_generator_end_gap_ms": 1000,
        "cw_generator_playback_mode": "sound",
        "cw_generator_volume_percent": 35,
        "splash_enabled": False,
        "systemd_splash_enabled": True,
        "safe_splash_seconds": 3.2,
    }

    cw_process = {"proc": None}

    def clamp_num(value, lo, hi, default):
        try:
            v = float(value)
        except Exception:
            return default
        return max(lo, min(hi, v))

    def apply_capture_level(percent: int) -> str:
        percent = int(clamp_num(percent, 0, 100, 70))
        dev = str(config.get("audio_device", "") or "")
        card = None
        if dev.startswith("plughw:"):
            try:
                card = dev.split(":", 1)[1].split(",", 1)[0]
            except Exception:
                card = None
        cmds = []
        if card:
            cmds.append(["amixer", "-c", str(card), "sset", "Capture", f"{percent}%"])
            cmds.append(["amixer", "-c", str(card), "sset", "Mic", f"{percent}%"])
        cmds.append(["amixer", "sset", "Capture", f"{percent}%"])
        errors = []
        for cmd in cmds:
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, timeout=3)
                return "applied"
            except Exception as e:
                errors.append(str(e))
        return "saved_only"

    def apply_lcd_brightness(percent: int) -> str:
        percent = int(clamp_num(percent, 5, 100, 100))
        roots = [Path("/sys/class/backlight"), Path("/sys/class/leds")]
        for root in roots:
            if not root.exists():
                continue
            for item in root.iterdir():
                brightness = item / "brightness"
                max_brightness = item / "max_brightness"
                if brightness.exists() and os.access(brightness, os.W_OK):
                    try:
                        maxv = int(max_brightness.read_text().strip()) if max_brightness.exists() else 255
                        val = max(1, int(maxv * percent / 100.0))
                        brightness.write_text(str(val))
                        return f"applied:{item.name}"
                    except Exception:
                        pass
        return "saved_only"

    MORSE_GEN = {
        "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.",
        "G": "--.", "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..",
        "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
        "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-",
        "Y": "-.--", "Z": "--..",
        "1": ".----", "2": "..---", "3": "...--", "4": "....-", "5": ".....",
        "6": "-....", "7": "--...", "8": "---..", "9": "----.", "0": "-----",
        ".": ".-.-.-", ",": "--..--", "?": "..--..", "/": "-..-.", "=": "-...-",
        "+": ".-.-.", "-": "-....-", "(": "-.--.", ")": "-.--.-",
    }

    def write_cw_wav(
        path: Path,
        text_value: str,
        tone_hz: int,
        wpm: float,
        volume: float = 0.35,
        farnsworth_wpm: float | None = None,
        key_profile: str = "computer",
        start_delay_ms: int = 0,
        end_gap_ms: int = 1000,
    ):
        sr = 8000
        char_wpm = clamp_num(wpm, 3, 40, 18.75)
        overall_wpm = clamp_num(farnsworth_wpm if farnsworth_wpm else char_wpm, 3, char_wpm, char_wpm)

        dot = 1.2 / max(1.0, float(char_wpm))
        gap_dot = 1.2 / max(1.0, float(overall_wpm))

        tone_hz = int(clamp_num(tone_hz, 300, 1200, 700))
        volume = clamp_num(volume, 0.05, 0.95, 0.35)

        profile = str(key_profile or "computer")
        profile_map = {
            "computer": (0.000, 1.00),
            "paddle_clean": (0.020, 1.00),
            "paddle_learner": (0.065, 1.02),
            "bug_light": (0.050, 1.07),
            "straight_human": (0.085, 1.04),
        }
        jitter, weight = profile_map.get(profile, profile_map["computer"])
        rng = random.Random(time.time())

        samples = []

        def humanise(sec: float, mark: bool = False) -> float:
            if jitter <= 0:
                return max(0.0, sec)
            factor = 1.0 + rng.uniform(-jitter, jitter)
            if mark:
                factor *= weight
            return max(0.0, sec * factor)

        def add_silence(sec):
            samples.extend([0] * max(0, int(sr * sec)))

        def add_tone(sec):
            sec = humanise(sec, mark=True)
            n = max(1, int(sr * sec))
            fade = max(1, int(sr * 0.004))
            for i in range(n):
                env = 1.0
                if i < fade:
                    env = i / fade
                elif i > n - fade:
                    env = max(0.0, (n - i) / fade)
                val = int(32767 * volume * env * math.sin(2 * math.pi * tone_hz * (i / sr)))
                samples.append(val)

        start_delay_ms = int(clamp_num(start_delay_ms, 0, 5000, 0))
        end_gap_ms = int(clamp_num(end_gap_ms, 0, 5000, 1000))

        if start_delay_ms:
            add_silence(start_delay_ms / 1000.0)

        clean = " ".join(str(text_value or "").upper().split())[:240]
        for word_i, word in enumerate(clean.split(" ")):
            if word_i:
                add_silence(humanise(gap_dot * 7))
            for char_i, ch in enumerate(word):
                code = MORSE_GEN.get(ch)
                if not code:
                    continue
                if char_i:
                    add_silence(humanise(gap_dot * 3))
                for elem_i, elem in enumerate(code):
                    if elem_i:
                        add_silence(humanise(dot))
                    add_tone(dot if elem == "." else dot * 3)

        if end_gap_ms:
            add_silence(end_gap_ms / 1000.0)

        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(b"".join(struct.pack("<h", int(x)) for x in samples))


    def read_wav_mono_float32(path: Path) -> np.ndarray:
        with wave.open(str(path), "rb") as wf:
            channels = wf.getnchannels()
            width = wf.getsampwidth()
            frames = wf.readframes(wf.getnframes())

        if width != 2:
            raise ValueError(f"Unsupported WAV sample width: {width}")

        data = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
        if channels > 1:
            data = data.reshape(-1, channels)[:, 0]
        return data.astype(np.float32, copy=False)

    def normalise_compare_text(value: str) -> str:
        return "".join(ch for ch in str(value or "").upper() if ch.isalnum())

    def selftest_status(expected: str, decoded: str) -> str:
        e = normalise_compare_text(expected)
        d = normalise_compare_text(decoded)

        if not e and not d:
            return "PASS"
        if e == d:
            return "PASS"
        if d and (e.startswith(d) or d.startswith(e)):
            return "CLOSE"

        # Simple overlap score without bringing in extra dependencies.
        common = 0
        for a, b in zip(e, d):
            if a == b:
                common += 1
        ratio = common / max(1, len(e))
        if ratio >= 0.80:
            return "CLOSE"
        return "FAIL"


    def run_cmd(args, timeout=8):
        try:
            cp = subprocess.run(
                args,
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
            }
        except Exception as e:
            return {"ok": False, "returncode": -1, "stdout": "", "stderr": str(e)}

    def nmcli_lines(args, timeout=8):
        res = run_cmd(["nmcli"] + args, timeout=timeout)
        if not res["ok"] and not res["stdout"]:
            return []
        return [line for line in res["stdout"].splitlines() if line.strip()]

    def parse_nmcli_colon_line(line):
        parts = []
        cur = ""
        esc_next = False

        for ch in str(line):
            if esc_next:
                cur += ch
                esc_next = False
            elif ch == "\\":
                esc_next = True
            elif ch == ":":
                parts.append(cur)
                cur = ""
            else:
                cur += ch

        parts.append(cur)
        return parts

    @app.route("/api/network/status")
    def network_status():
        try:
            hostname = run_cmd(["hostname"])["stdout"] or ""
            ip_line = run_cmd(["hostname", "-I"])["stdout"] or ""
            ip_addresses = [x for x in ip_line.split() if x]

            default_route = bool(
                run_cmd(["sh", "-c", "ip route show default | grep -q '^default '"])["ok"]
            )

            devices = []
            wifi_device = ""

            for line in nmcli_lines(["-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device", "status"]):
                parts = parse_nmcli_colon_line(line)
                while len(parts) < 4:
                    parts.append("")

                dev = {
                    "device": parts[0],
                    "type": parts[1],
                    "state": parts[2],
                    "connection": parts[3],
                }
                devices.append(dev)

                if dev["type"] == "wifi" and dev["device"] != "p2p-dev-wlan0" and not wifi_device:
                    wifi_device = dev["device"]

            connections = []
            active_wifi_connection = ""
            hotspot_active = False

            for line in nmcli_lines(["-t", "-f", "NAME,TYPE,DEVICE,AUTOCONNECT", "connection", "show"]):
                parts = parse_nmcli_colon_line(line)
                while len(parts) < 4:
                    parts.append("")

                item = {
                    "name": parts[0],
                    "type": parts[1],
                    "device": parts[2],
                    "autoconnect": parts[3],
                }
                connections.append(item)

            for line in nmcli_lines(["-t", "-f", "NAME,DEVICE", "connection", "show", "--active"]):
                parts = parse_nmcli_colon_line(line)
                while len(parts) < 2:
                    parts.append("")

                if parts[1] == wifi_device:
                    active_wifi_connection = parts[0]

                if parts[0] == "morse-whisperer-setup-hotspot":
                    hotspot_active = True

            fallback_active = (
                run_cmd(["systemctl", "is-active", "morse-whisperer-network-fallback.service"])["stdout"]
                or "unknown"
            )
            fallback_enabled = (
                run_cmd(["systemctl", "is-enabled", "morse-whisperer-network-fallback.service"])["stdout"]
                or "unknown"
            )

            return jsonify({
                "ok": True,
                "hostname": hostname,
                "ip_addresses": ip_addresses,
                "default_route": default_route,
                "wifi_device": wifi_device,
                "devices": devices,
                "connections": connections,
                "active_wifi_connection": active_wifi_connection,
                "hotspot_active": hotspot_active,
                "fallback_service_active": fallback_active,
                "fallback_service_enabled": fallback_enabled,
                "setup_ssid": "The Morse Whisperer",
                "setup_ip": "10.42.0.1",
            })

        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500


    @app.route("/api/network/connect", methods=["POST"])
    def network_connect():
        data = request.get_json(silent=True) or {}
        ssid = str(data.get("ssid") or "").strip()
        password = str(data.get("password") or "")

        if not ssid:
            return jsonify({"ok": False, "error": "SSID is required"}), 400

        try:
            helper = "/opt/morse-whisperer-pi/tools/network_connect_helper.py"
            payload = json.dumps({
                "ssid": ssid,
                "password": password,
            })

            # NetworkManager authorisation is handled by Polkit.
            # Do not use sudo here: the service runs with NoNewPrivileges=yes.
            helper_cmd = [helper]

            cp = subprocess.run(
                helper_cmd,
                input=payload,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=75,
            )

            raw = (cp.stdout or "").strip()
            if not raw:
                return jsonify({
                    "ok": False,
                    "error": cp.stderr.strip() or "Network helper returned no output",
                    "returncode": cp.returncode,
                }), 500

            try:
                result = json.loads(raw)
            except Exception:
                return jsonify({
                    "ok": False,
                    "error": "Network helper returned invalid JSON",
                    "stdout": raw,
                    "stderr": cp.stderr.strip(),
                    "returncode": cp.returncode,
                }), 500

            if result.get("ok"):
                try:
                    state.append_status(f"Wi-Fi connect requested: {ssid}")
                except Exception:
                    pass
                return jsonify(result)

            return jsonify(result), 500

        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500


    @app.route("/api/network/scan")
    def network_scan():
        try:
            # Read-only scan. This does not connect, disconnect, or start hotspot mode.
            #
            # The UI shows unique network names like a phone does. If multiple APs
            # advertise the same SSID, keep the strongest one.
            lines = nmcli_lines(
                [
                    "-t",
                    "-f",
                    "IN-USE,SSID,SIGNAL,SECURITY,CHAN,FREQ",
                    "device",
                    "wifi",
                    "list",
                    "--rescan",
                    "yes",
                ],
                timeout=20,
            )

            best_by_ssid = {}

            for line in lines:
                parts = parse_nmcli_colon_line(line)
                while len(parts) < 6:
                    parts.append("")

                in_use = parts[0].strip() == "*"
                ssid = parts[1]
                signal = parts[2]
                security = parts[3] or "open"
                channel = parts[4]
                freq = parts[5]

                try:
                    signal_num = int(signal or 0)
                except Exception:
                    signal_num = 0

                key = (ssid, security)
                existing = best_by_ssid.get(key)

                item = {
                    "in_use": in_use,
                    "ssid": ssid,
                    "signal": signal_num,
                    "security": security,
                    "channel": channel,
                    "freq": freq,
                }

                if existing is None:
                    best_by_ssid[key] = item
                elif in_use or signal_num > int(existing.get("signal", 0)):
                    best_by_ssid[key] = item

            networks = list(best_by_ssid.values())
            networks.sort(key=lambda x: (not x.get("in_use", False), -x.get("signal", 0), x.get("ssid", "")))

            return jsonify({
                "ok": True,
                "networks": networks[:80],
            })

        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500


    @app.route("/api/settings")
    def get_settings():
        resp = jsonify({"ok": True, "config": config})
        resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.route("/api/settings", methods=["POST"])
    def update_settings():
        data = request.get_json(silent=True) or {}
        changed = {}
        for key, caster in SETTINGS_ALLOWLIST.items():
            if key not in data:
                continue
            try:
                value = caster(data[key])
            except Exception:
                continue

            if key in ("target_tone_hz", "cw_generator_tone_hz"):
                value = int(clamp_num(value, 300, 1200, 700))
            elif key in ("initial_wpm", "cw_generator_wpm", "cw_generator_farnsworth_wpm"):
                value = float(clamp_num(value, 3, 45, 18.75))
            elif key in ("cw_generator_start_delay_ms", "cw_generator_end_gap_ms"):
                value = int(clamp_num(value, 0, 5000, 0 if key.endswith("start_delay_ms") else 1000))
            elif key in ("input_capture_percent", "lcd_brightness_percent", "cw_generator_volume_percent"):
                value = int(clamp_num(value, 0 if key.startswith("input") else 5, 100, 70))
            elif key == "cw_generator_key_profile" and value not in ("computer", "paddle_clean", "paddle_learner", "bug_light", "straight_human"):
                value = "computer"
            elif key == "cw_generator_playback_mode" and value not in ("sound",):
                value = "sound"
            elif key == "tone_mode" and value not in ("session_auto", "auto", "fixed"):
                value = "session_auto"
            elif key == "ai_provider" and value not in ("local", "openai"):
                value = "local"
            elif key == "ai_model":
                value = str(value or "gpt-4.1-mini").strip()[:80]
            elif key == "audio_filter_mode" and value not in ("off", "wide", "narrow", "custom"):
                value = "wide"
            elif key in ("audio_filter_bandwidth_hz", "audio_filter_wide_hz", "audio_filter_narrow_hz", "audio_filter_max_hz"):
                value = int(clamp_num(value, 80, 1200, 300))

            config[key] = value
            changed[key] = value

        capture_status = None
        brightness_status = None
        if "input_capture_percent" in changed:
            capture_status = apply_capture_level(int(changed["input_capture_percent"]))
        if "lcd_brightness_percent" in changed:
            brightness_status = apply_lcd_brightness(int(changed["lcd_brightness_percent"]))

        save_config(config)
        state.update(config=config)
        state.append_status(f"Settings saved: {', '.join(changed.keys()) or 'none'}")
        return jsonify({"ok": True, "changed": changed, "capture_status": capture_status, "brightness_status": brightness_status})

    @app.route("/api/settings/defaults", methods=["POST"])
    def reset_settings_defaults():
        config.update(SAFE_DEFAULTS)
        save_config(config)
        state.update(config=config)
        state.append_status("Settings reset to safe defaults")
        return jsonify({"ok": True, "config": config})

    @app.route("/api/cw/play", methods=["POST"])
    def cw_play():
        data = request.get_json(silent=True) or {}
        text_value = str(data.get("text") or "VVV THE MORSE WHISPERER TEST 73")
        tone_hz = int(clamp_num(data.get("tone_hz", config.get("cw_generator_tone_hz", config.get("target_tone_hz", 700))), 300, 1200, 700))
        wpm = float(clamp_num(data.get("wpm", config.get("cw_generator_wpm", config.get("initial_wpm", 18.75))), 3, 40, 18.75))
        farnsworth_wpm = float(clamp_num(data.get("farnsworth_wpm", config.get("cw_generator_farnsworth_wpm", wpm)), 3, wpm, wpm))
        key_profile = str(data.get("key_profile") or config.get("cw_generator_key_profile") or "computer")
        if key_profile not in ("computer", "paddle_clean", "paddle_learner", "bug_light", "straight_human"):
            key_profile = "computer"
        playback_mode = str(data.get("playback_mode") or config.get("cw_generator_playback_mode") or "sound")
        if playback_mode != "sound":
            return jsonify({"ok": False, "error": "Only sound playback is supported on this hardware today."}), 400
        start_delay_ms = int(clamp_num(data.get("start_delay_ms", config.get("cw_generator_start_delay_ms", 0)), 0, 5000, 0))
        end_gap_ms = int(clamp_num(data.get("end_gap_ms", config.get("cw_generator_end_gap_ms", 1000)), 0, 5000, 1000))
        volume = float(clamp_num(data.get("volume_percent", config.get("cw_generator_volume_percent", 35)), 5, 95, 35)) / 100.0
        output_device = str(data.get("output_device") or config.get("audio_output_device") or "plughw:2,0")

        try:
            old = cw_process.get("proc")
            if old and old.poll() is None:
                old.terminate()

            wav_path = Path(tempfile.gettempdir()) / "morse-whisperer-generator.wav"
            write_cw_wav(
                wav_path,
                text_value,
                tone_hz,
                wpm,
                volume=volume,
                farnsworth_wpm=farnsworth_wpm,
                key_profile=key_profile,
                start_delay_ms=start_delay_ms,
                end_gap_ms=end_gap_ms,
            )

            proc = subprocess.Popen(
                ["aplay", "-q", "-D", output_device, str(wav_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            cw_process["proc"] = proc
            state.append_status(f"CW generator playing {tone_hz} Hz at {wpm:.1f}/{farnsworth_wpm:.1f} WPM via {output_device}")
            return jsonify({
                "ok": True,
                "tone_hz": tone_hz,
                "wpm": wpm,
                "farnsworth_wpm": farnsworth_wpm,
                "key_profile": key_profile,
                "start_delay_ms": start_delay_ms,
                "end_gap_ms": end_gap_ms,
                "output_device": output_device,
            })
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500


    @app.route("/api/cw/selftest", methods=["POST"])
    def cw_selftest():
        data = request.get_json(silent=True) or {}

        try:
            text_value = str(data.get("text") or "VVV THE MORSE WHISPERER TEST 73")

            tone_hz = int(clamp_num(
                data.get("tone_hz", config.get("cw_generator_tone_hz", config.get("target_tone_hz", 700))),
                300,
                1200,
                700,
            ))

            wpm = float(clamp_num(
                data.get("wpm", config.get("cw_generator_wpm", config.get("initial_wpm", 18.75))),
                3,
                40,
                18.75,
            ))

            farnsworth_wpm = float(clamp_num(
                data.get("farnsworth_wpm", config.get("cw_generator_farnsworth_wpm", wpm)),
                3,
                wpm,
                wpm,
            ))

            key_profile = str(data.get("key_profile") or config.get("cw_generator_key_profile") or "computer")
            if key_profile not in ("computer", "paddle_clean", "paddle_learner", "bug_light", "straight_human"):
                key_profile = "computer"

            start_delay_ms = int(clamp_num(
                data.get("start_delay_ms", config.get("cw_generator_start_delay_ms", 0)),
                0,
                5000,
                0,
            ))

            end_gap_ms = int(clamp_num(
                data.get("end_gap_ms", config.get("cw_generator_end_gap_ms", 1000)),
                0,
                5000,
                1000,
            ))

            volume = float(clamp_num(
                data.get("volume_percent", config.get("cw_generator_volume_percent", 35)),
                5,
                95,
                35,
            )) / 100.0

            wav_path = Path(tempfile.gettempdir()) / "morse-whisperer-selftest.wav"

            write_cw_wav(
                wav_path,
                text_value,
                tone_hz,
                wpm,
                volume=volume,
                farnsworth_wpm=farnsworth_wpm,
                key_profile=key_profile,
                start_delay_ms=start_delay_ms,
                end_gap_ms=end_gap_ms,
            )

            samples = read_wav_mono_float32(wav_path)

            test_cfg = dict(config)
            test_cfg["tone_mode"] = "fixed"
            test_cfg["target_tone_hz"] = tone_hz
            test_cfg["initial_wpm"] = wpm

            result = analyse_samples(samples, test_cfg)
            status = selftest_status(text_value, result.copy)

            state.append_status(
                f"CW self-test {status}: {tone_hz} Hz {wpm:.1f}/{farnsworth_wpm:.1f} WPM"
            )

            selftest_result = {
                "ok": True,
                "status": status,
                "expected": text_value.upper(),
                "decoded": result.copy,
                "raw": result.raw,
                "tone_hz": tone_hz,
                "wpm": wpm,
                "farnsworth_wpm": farnsworth_wpm,
                "key_profile": key_profile,
                "snr_db": result.snr_db,
                "confidence": result.confidence,
                "dot_ms": result.dot_ms,
                "marks": result.marks,
                "spaces": result.spaces,
                "reason": result.reason,
                "updated_at": time.time(),
            }

            state.update(trainer_selftest=selftest_result)

            return jsonify(selftest_result)

        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500


    @app.route("/api/cw/stop", methods=["POST"])
    def cw_stop():
        proc = cw_process.get("proc")
        if proc and proc.poll() is None:
            proc.terminate()
        state.append_status("CW generator stopped")
        return jsonify({"ok": True})

    @app.route("/download/report.json")
    def report_json():
        data = json.dumps(state.snapshot(), indent=2)
        return Response(
            data,
            mimetype="application/json",
            headers={
                "Content-Disposition": "attachment; filename=morse-whisperer-report.json",
                "Cache-Control": "no-store",
            },
        )

    @app.route("/download/copy.txt")
    def copy_txt():
        snap = state.snapshot()
        dec = snap.get("decode", {})
        text = (
            "COPY:\n"
            + str(dec.get("stable_copy") or dec.get("copy") or "")
            + "\n\nRAW:\n"
            + str(dec.get("stable_raw") or dec.get("raw") or "")
            + "\n"
        )
        return Response(
            text,
            mimetype="text/plain",
            headers={
                "Content-Disposition": "attachment; filename=morse-whisperer-copy.txt",
                "Cache-Control": "no-store",
            },
        )


    # MW_DECODER_PROFILE_API_PHASE2_SAFE
    @app.route("/api/decoder/profile", methods=["GET", "POST"])
    def api_decoder_profile():
        import json
        import subprocess
        import sys
        from pathlib import Path

        cfg_path = Path("/opt/morse-whisperer-pi/config.json")
        helper = Path("/opt/morse-whisperer-pi/tools/set_decoder_profile.py")
        restart_helper = Path("/opt/morse-whisperer-pi/tools/restart_after_profile_switch.py")

        def read_profile():
            cfg = json.loads(cfg_path.read_text())
            tones = cfg.get("allowed_tones_hz") or []
            return {
                "ok": True,
                "decoder_profile": cfg.get("decoder_profile", "unknown"),
                "tone_mode": cfg.get("tone_mode"),
                "target_tone_hz": cfg.get("target_tone_hz"),
                "allowed_tones_hz": tones,
                "audio_filter_mode": cfg.get("audio_filter_mode"),
                "audio_filter_narrow_hz": cfg.get("audio_filter_narrow_hz"),
                "copy_min_decoded_symbols": cfg.get("copy_min_decoded_symbols"),
                "copy_max_failed_symbols": cfg.get("copy_max_failed_symbols"),
                "copy_min_confidence": cfg.get("copy_min_confidence"),
                "copy_min_snr": cfg.get("copy_min_snr"),
                "decode_window_sec": cfg.get("decode_window_sec"),
                "word_gap_units": cfg.get("word_gap_units"),
            }

        if request.method == "GET":
            return jsonify(read_profile())

        data = request.get_json(silent=True) or {}
        profile = str(data.get("profile") or "").strip().lower()
        restart = bool(data.get("restart", True))

        if profile not in ("clean", "kiwi"):
            return jsonify({"ok": False, "error": "profile must be clean or kiwi"}), 400

        cp = subprocess.run(
            [sys.executable, str(helper), profile],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        if cp.returncode != 0:
            return jsonify({
                "ok": False,
                "error": "profile helper failed",
                "stdout": cp.stdout,
                "stderr": cp.stderr,
            }), 500

        result = read_profile()
        result["stdout"] = cp.stdout
        result["restart_requested"] = restart

        if restart:
            subprocess.Popen(
                [sys.executable, str(restart_helper)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            result["message"] = "Profile saved. Restart and decoder clear requested."
        else:
            result["message"] = "Profile saved. Manual restart required."

        return jsonify(result)


    return app
