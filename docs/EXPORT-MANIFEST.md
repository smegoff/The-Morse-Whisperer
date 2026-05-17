# Morse Whisperer Appliance Export

Created: 2026-05-17T14:16:31+12:00
Host: TheMorseWhisperer
Kernel: Linux TheMorseWhisperer 6.18.29+rpt-rpi-v8 #1 SMP PREEMPT Debian 1:6.18.29-1+rpt1 (2026-05-12) aarch64 GNU/Linux

## Services
● morse-whisperer.service - The Morse Whisperer CW Decoder Appliance
     Loaded: loaded (/etc/systemd/system/morse-whisperer.service; enabled; preset: enabled)
    Drop-In: /etc/systemd/system/morse-whisperer.service.d
             └─10-device-permissions.conf, 10-display-permissions.conf, 20-disable-splash-prestart.conf, 40-safe-animated-boot-splash.conf
     Active: active (running) since Sun 2026-05-17 14:08:22 NZST; 8min ago
 Invocation: 2fec078c2e394122ace5d1b74dc51baf
   Main PID: 868 (python)
      Tasks: 5 (limit: 4505)
        CPU: 54.504s
     CGroup: /system.slice/morse-whisperer.service
             ├─868 /opt/morse-whisperer-pi/venv/bin/python -m morse_whisperer
             └─895 arecord -q -D plughw:2,0 -r 8000 -f S16_LE -c 1 -t raw

May 17 14:16:22 TheMorseWhisperer python[868]: 192.168.10.209 - - [17/May/2026 14:16:22] "GET /api/snapshot?ts=1778984183286 HTTP/1.1" 200 -
May 17 14:16:23 TheMorseWhisperer python[868]: 192.168.10.209 - - [17/May/2026 14:16:23] "GET /api/snapshot?ts=1778984184345 HTTP/1.1" 200 -
May 17 14:16:24 TheMorseWhisperer python[868]: 192.168.10.209 - - [17/May/2026 14:16:24] "GET /api/snapshot?ts=1778984185351 HTTP/1.1" 200 -
May 17 14:16:25 TheMorseWhisperer python[868]: 192.168.10.209 - - [17/May/2026 14:16:25] "GET /api/snapshot?ts=1778984186393 HTTP/1.1" 200 -
May 17 14:16:26 TheMorseWhisperer python[868]: 192.168.10.209 - - [17/May/2026 14:16:26] "GET /api/snapshot?ts=1778984187397 HTTP/1.1" 200 -
May 17 14:16:27 TheMorseWhisperer python[868]: 192.168.10.209 - - [17/May/2026 14:16:27] "GET /api/snapshot?ts=1778984188437 HTTP/1.1" 200 -
May 17 14:16:28 TheMorseWhisperer python[868]: 192.168.10.209 - - [17/May/2026 14:16:28] "GET /api/snapshot?ts=1778984189438 HTTP/1.1" 200 -
May 17 14:16:29 TheMorseWhisperer python[868]: 192.168.10.209 - - [17/May/2026 14:16:29] "GET /api/snapshot?ts=1778984190453 HTTP/1.1" 200 -
May 17 14:16:30 TheMorseWhisperer python[868]: 192.168.10.209 - - [17/May/2026 14:16:30] "GET /api/snapshot?ts=1778984191466 HTTP/1.1" 200 -
May 17 14:16:31 TheMorseWhisperer python[868]: 192.168.10.209 - - [17/May/2026 14:16:31] "GET /api/snapshot?ts=1778984192573 HTTP/1.1" 200 -

● morse-whisperer-buttons.service - The Morse Whisperer TFT Button Sidecar
     Loaded: loaded (/etc/systemd/system/morse-whisperer-buttons.service; enabled; preset: enabled)
     Active: active (running) since Sun 2026-05-17 14:10:37 NZST; 5min ago
 Invocation: 734da4e296b34ac0962cb07d7ae5e2e4
   Main PID: 1375 (python)
      Tasks: 1 (limit: 4505)
        CPU: 627ms
     CGroup: /system.slice/morse-whisperer-buttons.service
             └─1375 /opt/morse-whisperer-pi/venv/bin/python -

May 17 14:11:57 TheMorseWhisperer button_sidecar.sh[1375]: [mw-buttons] 2026-05-17 14:11:57 POST /api/tft/freeze OK
May 17 14:11:58 TheMorseWhisperer button_sidecar.sh[1375]: [mw-buttons] 2026-05-17 14:11:58 Button 1 GPIO23 released after 2.12s
May 17 14:12:01 TheMorseWhisperer button_sidecar.sh[1375]: [mw-buttons] 2026-05-17 14:12:01 Button 1 GPIO23 pressed
May 17 14:12:01 TheMorseWhisperer button_sidecar.sh[1375]: [mw-buttons] 2026-05-17 14:12:01 Button 1 GPIO23 released after 0.20s
May 17 14:12:01 TheMorseWhisperer button_sidecar.sh[1375]: [mw-buttons] 2026-05-17 14:12:01 Button 1 short: TFT next page
May 17 14:12:01 TheMorseWhisperer button_sidecar.sh[1375]: [mw-buttons] 2026-05-17 14:12:01 POST /api/tft/next OK
May 17 14:12:02 TheMorseWhisperer button_sidecar.sh[1375]: [mw-buttons] 2026-05-17 14:12:02 Button 1 GPIO23 pressed
May 17 14:12:02 TheMorseWhisperer button_sidecar.sh[1375]: [mw-buttons] 2026-05-17 14:12:02 Button 1 GPIO23 released after 0.15s
May 17 14:12:02 TheMorseWhisperer button_sidecar.sh[1375]: [mw-buttons] 2026-05-17 14:12:02 Button 1 short: TFT next page
May 17 14:12:02 TheMorseWhisperer button_sidecar.sh[1375]: [mw-buttons] 2026-05-17 14:12:02 POST /api/tft/next OK

## Git status inside appliance, if any

## Important checksums
019654e2e2f3d90bfb56724771e65cc32a59da22d54180dc4595edccb89071fc  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/morse_whisperer/buttons.py
07945b994ada08005757baf65176621f82f4b7326e68fe2490a5739a017e6e30  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/assets/boot_splash.png
16a0e7bca333b31600fb55819ad48f456fe0c641015ae0af931120d8d2713958  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/install.sh
1bc1ca80cea0ffe925b3403b36b46090a2ce9ced6e0b20f55e3ad4e93ca2e7cb  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/tools/record_wav.py
2dda6b1b686ef99c1381d3930a817b8c71c9854b04309ab09148f1bff94db042  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/morse_whisperer/formatter.py
38f94a31afb7558ee77fcdb5ccc93175c4e2f077fe1ff4fb10427e97eec56145  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/tools/splash_screen.py
3bbf02f9e9ddb80ad0a65e10658fbbb5eed168828fd4b857005616e72739c06a  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/tools/network_fallback.sh
4172023a4efaf3bd1b03d8673a15df170701dcb2f4e9379edb359a505e7cbfae  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/morse_whisperer/display.py
4422cd01eacc4b23e43890ce0ec602e525b874895d78bcb17b25ef02b5ba81e5  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/config.json
475114e2b3123b6b6b6da590d32133c6d4af2b62c58b649ed0059c0e74303910  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/morse_whisperer/web.py
4bc15c04259f64df0fca349537d4e1d0cc6482fecd28862e8427e9b3a57f876d  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/config.json.bak-gap-65-20260516-131232
4c46d35b5559350e1f5cd7da8f9a43eba9cc3ab76c2780a0251a8ae553c54bd9  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/tools/network_connect_helper.py
4d343a88e755a31f95623d8d4e01cc3fac2c72982b45fc51b2ffbd5fb808007d  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/config.json.bak-slow-gap-20260516-124453
602ddbe46bb337effe06acc02215e65b97e9281a494ca031af0b046cd87de4c9  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/tools/button_sidecar_filter.py
65a7c914a92823ac0b328259c87084febcf3a5f74601995abbec0bc6ab47ce52  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/tools/tone_truth.py
6a50cf7349402466320dd27b501d1eed655b77c1c193cf723dc2cf4af7bfae72  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/tools/animated_boot_splash.py
6b69434ba9d58e897d0f0e89d9f04a1bc4ee54a4e61b1bebf7dfc25b48bb4407  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/assets/horse_boot_splash.png
6cf573528524cf6e96837ff827bafc90116a139f821f72000aa65446c1270662  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/tools/list_audio.py
7f242a63d8cc9740ff4fac5c1e0a7d3fee1deec1b195f83d5ffab2d56db6cf0a  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/tools/button_sidecar_safe_disabled.py
832ece34d4c9204e0eb7d1971b6bf533c9bab732ea41b6df065fb7e4a22160f1  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/morse_whisperer/config.py
869d05f33e019a1412952a65b6eaaaf3f0a9c4f579824954987c80a663d099fe  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/tools/safe_splash.py
8a174adcea619e5366297aa7fae305f45ac1a976ebd63163b9ddaadd2207ee83  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/morse_whisperer/app.py
8a316f3fa9307aa3cf437b88879db01caa7a753db1fcb8205b2d0c5efb55b5f6  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/README_RECOVERY.md
8e602e9fcacc02a7a7c3619e432da1cb8a5016d82dc49e62855ac63faaa040f6  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/config.example.json
96adeb3e026be360311c3942aedf5ace6569a06746da09d5bb92a7745ca8222c  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/config.json.bak-gap-middle-20260516-130356
a7833154ef22876fa19e1ec8355064aea30a04319390cb28d4b11b33a9b1de38  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/morse_whisperer/__init__.py
af50e696623a5a5cb05b73789d8c3d25397e2c289a6f602cf069c30bc467fec2  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/morse_whisperer/audio.py
bd2feb0ba2a2276399a0a60c5aba78e91ea294ea0a0dcfce72dacd458c2b35f0  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/morse_whisperer/dsp.py
d21642dd881bfd3bf262464a9b92bfeabdd5b64853bbb5fedb59fa6f552c1506  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/config.json.bak-display-fb1-20260515-150206
d840abbb949d9fe0f05a07c779a2b094b85a24f5d54cc6ae67cabca37296baae  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/tools/safe_splash_v2.py
db188377e4bbf41d420143f902544670578581ff237ac5fc4e4edc6e9b7b1122  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/tools/decode_wav.py
dd09488b3cc3fe0d318db9b1bd461d032c8101d238133be221e88eac95987219  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/assets/horse_watermark.png
de078e1008c78ddefe9b656a90ba8092866a32a8689fef678860027a0b95d32a  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/morse_whisperer/__main__.py
eab5b55e5b341320af103d8879bf737125685af3aa91027340aba8a15b06a557  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/tools/button_sidecar.sh
ed8a52d7de9dafbab2b49a6f1e6a5898a67129a01ce7f6f5ebc16555a126e9ec  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/morse_whisperer/state.py
f4b568e642d9c3d7f78fdec70465f1ecb7d964b9fb65656aeff7328afb1c1a0d  /tmp/mw-github-export-20260517-141631/morse-whisperer-pi/tools/boot_splash_image.py
