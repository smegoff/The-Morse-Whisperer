from __future__ import annotations

import re
import shutil
import subprocess
from typing import Any, Dict

from flask import jsonify, request

from .ai import analyse_copy, suggest_reply
from .config import save_config


CALLSIGN_RE = re.compile(r"^[A-Z0-9]{1,3}[0-9][A-Z0-9/]{1,8}$")

CQ_DEFAULTS: Dict[str, Any] = {
    "cq_enabled": False,
    "cq_callsign": "N0CALL",
    "cq_cat_enabled": False,
    "cq_cat_backend": "rigctl",
    "cq_cat_model": "3073",
    "cq_cat_device": "/dev/ttyUSB0",
    "cq_cat_baud": 19200,
    "cq_band_allowlist": "40m,20m,15m,10m",
    "cq_busy_rms_threshold": 0.006,
    "cq_busy_snr_threshold_db": 6.0,
    "cq_ai_enabled": True,
    "cq_ai_provider": "openai",
    "cq_ai_model": "gpt-4.1-mini",
    "cq_allow_transmit": False,
}

CQ_SETTINGS_ALLOWLIST = {
    "cq_enabled": bool,
    "cq_callsign": str,
    "cq_cat_enabled": bool,
    "cq_cat_backend": str,
    "cq_cat_model": str,
    "cq_cat_device": str,
    "cq_cat_baud": int,
    "cq_band_allowlist": str,
    "cq_busy_rms_threshold": float,
    "cq_busy_snr_threshold_db": float,
    "cq_ai_enabled": bool,
    "cq_ai_provider": str,
    "cq_ai_model": str,
}


def cq_defaults_for_config(config: Dict[str, Any]) -> Dict[str, Any]:
    defaults = dict(CQ_DEFAULTS)
    defaults["cq_callsign"] = str(config.get("station_callsign") or "N0CALL").upper()
    return defaults


def cq_config(config: Dict[str, Any]) -> Dict[str, Any]:
    cfg = cq_defaults_for_config(config)
    for key in CQ_DEFAULTS:
        if key in config:
            cfg[key] = config[key]
    cfg["cq_callsign"] = normalise_callsign(cfg.get("cq_callsign"), cfg["cq_callsign"])
    cfg["cq_cat_baud"] = clamp_int(cfg.get("cq_cat_baud"), 1200, 115200, 19200)
    cfg["cq_busy_rms_threshold"] = clamp_float(cfg.get("cq_busy_rms_threshold"), 0.0001, 0.2, 0.006)
    cfg["cq_busy_snr_threshold_db"] = clamp_float(cfg.get("cq_busy_snr_threshold_db"), 0.0, 40.0, 6.0)
    cfg["cq_allow_transmit"] = False
    return cfg


def normalise_callsign(value: Any, fallback: str = "N0CALL") -> str:
    call = str(value or fallback or "N0CALL").strip().upper()
    call = re.sub(r"[^A-Z0-9/]", "", call)
    if not CALLSIGN_RE.match(call):
        return str(fallback or "N0CALL").strip().upper()
    return call


def clamp_int(value: Any, low: int, high: int, default: int) -> int:
    try:
        return max(low, min(high, int(value)))
    except Exception:
        return default


def clamp_float(value: Any, low: float, high: float, default: float) -> float:
    try:
        return max(low, min(high, float(value)))
    except Exception:
        return default


def channel_status(snapshot: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    audio = snapshot.get("audio", {}) or {}
    quality = snapshot.get("quality", {}) or {}
    decode = snapshot.get("decode", {}) or {}

    copy = str(decode.get("stable_copy") or decode.get("copy") or "").strip()
    level = str(audio.get("level_status") or "").upper()
    rms = float(audio.get("rms") or 0.0)
    snr = float(quality.get("snr_db") or 0.0)
    confidence = float(quality.get("confidence") or 0.0)
    squelch_open = bool(quality.get("squelch_open"))
    recent_activity = bool(quality.get("recent_activity"))

    reasons = []
    if copy:
        reasons.append("decoded copy present")
    if squelch_open:
        reasons.append("decoder squelch open")
    if recent_activity:
        reasons.append("recent keyed activity")
    if rms >= float(cfg["cq_busy_rms_threshold"]):
        reasons.append("audio above busy RMS threshold")
    if snr >= float(cfg["cq_busy_snr_threshold_db"]):
        reasons.append("signal SNR above busy threshold")
    if level in ("GOOD", "HOT", "CLIP"):
        reasons.append(f"audio level {level}")

    if reasons:
        state = "busy"
    elif level in ("IDLE", "LOW", "") and rms < float(cfg["cq_busy_rms_threshold"]):
        state = "clear"
        reasons.append("quiet audio and no decoder activity")
    else:
        state = "unknown"
        reasons.append("insufficient evidence")

    return {
        "state": state,
        "reason": "; ".join(reasons),
        "audio_level": level or "--",
        "rms": rms,
        "snr_db": snr,
        "confidence": confidence,
        "squelch_open": squelch_open,
        "recent_activity": recent_activity,
        "decoded_copy": copy,
    }


def read_cat_status(cfg: Dict[str, Any]) -> Dict[str, Any]:
    status = {
        "enabled": bool(cfg.get("cq_cat_enabled")),
        "backend": str(cfg.get("cq_cat_backend") or "rigctl"),
        "available": False,
        "frequency_hz": None,
        "mode": None,
        "ptt": None,
        "error": None,
    }
    if not status["enabled"]:
        status["error"] = "CAT disabled"
        return status
    if status["backend"] != "rigctl":
        status["error"] = "Only rigctl status probing is wired in this milestone"
        return status
    rigctl = shutil.which("rigctl")
    if not rigctl:
        status["error"] = "rigctl not found"
        return status

    base = [
        rigctl,
        "-m",
        str(cfg.get("cq_cat_model") or "3073"),
        "-r",
        str(cfg.get("cq_cat_device") or "/dev/ttyUSB0"),
        "-s",
        str(cfg.get("cq_cat_baud") or 19200),
    ]
    try:
        freq = subprocess.run(base + ["f"], check=True, capture_output=True, text=True, timeout=2)
        mode = subprocess.run(base + ["m"], check=True, capture_output=True, text=True, timeout=2)
        ptt = subprocess.run(base + ["t"], check=True, capture_output=True, text=True, timeout=2)
        status.update(
            {
                "available": True,
                "frequency_hz": int(float(freq.stdout.strip().splitlines()[0])),
                "mode": mode.stdout.strip().splitlines()[0] if mode.stdout.strip() else None,
                "ptt": ptt.stdout.strip().splitlines()[0] if ptt.stdout.strip() else None,
                "error": None,
            }
        )
    except Exception as e:
        status["error"] = str(e)
    return status


def cq_status(snapshot: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    cfg = cq_config(config)
    return {
        "ok": True,
        "app": "CQ Rag Chew",
        "phase": "listen_only_foundation",
        "transmit_available": False,
        "safety": [
            "Transmit is disabled in this milestone.",
            "Frequency changes and PTT are not exposed by the CQ Rag Chew API yet.",
            "Use the busy/clear judgement as advisory until CAT and audio evidence are proven on the bench.",
        ],
        "config": cfg,
        "ai": {
            "enabled": bool(cfg.get("cq_ai_enabled")),
            "provider": str(cfg.get("cq_ai_provider") or "openai"),
            "model": str(cfg.get("cq_ai_model") or config.get("ai_model") or "gpt-4.1-mini"),
            "mode": "suggestion_only",
        },
        "radio": read_cat_status(cfg),
        "channel": channel_status(snapshot, cfg),
    }


def latest_copy(snapshot: Dict[str, Any]) -> str:
    decode = snapshot.get("decode", {}) or {}
    return str(
        decode.get("stable_copy")
        or decode.get("copy")
        or decode.get("candidate_copy")
        or decode.get("stable_raw")
        or decode.get("raw")
        or ""
    ).strip()


def cq_ai_config(config: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    ai_cfg = dict(config)
    ai_cfg["ai_enabled"] = bool(cfg.get("cq_ai_enabled"))
    ai_cfg["ai_provider"] = str(cfg.get("cq_ai_provider") or "openai")
    ai_cfg["ai_model"] = str(cfg.get("cq_ai_model") or config.get("ai_model") or "gpt-4.1-mini")
    ai_cfg["ai_operator_callsign"] = str(cfg.get("cq_callsign") or config.get("station_callsign") or "N0CALL")
    ai_cfg["ai_reply_style"] = "short_cw"
    ai_cfg["ai_require_confirmation"] = True
    return ai_cfg


def cq_plan(snapshot: Dict[str, Any], config: Dict[str, Any], requested_mode: str | None = None) -> Dict[str, Any]:
    cfg = cq_config(config)
    channel = channel_status(snapshot, cfg)
    radio = read_cat_status(cfg)
    copy = latest_copy(snapshot)
    ai_cfg = cq_ai_config(config, cfg)

    analysis = analyse_copy(copy, ai_cfg, snap=snapshot)
    reply = suggest_reply(analysis, ai_cfg, requested_mode=requested_mode)

    warnings = []
    warnings.extend(analysis.get("warnings") or [])
    warnings.extend(reply.get("warnings") or [])
    if channel.get("state") == "busy" and not copy:
        warnings.append("Frequency appears busy, but no usable copy is available yet.")
    if channel.get("state") == "clear":
        warnings.append("No station is currently copied; a CQ draft is not generated until transmit controls exist.")

    return {
        "ok": True,
        "app": "CQ Rag Chew",
        "phase": "openai_planning_listen_only",
        "transmit_available": False,
        "copy": copy,
        "channel": channel,
        "radio": radio,
        "analysis": analysis,
        "reply": reply,
        "warnings": warnings,
        "safety": [
            "OpenAI is used only for analysis and draft suggestions.",
            "No CQ Rag Chew endpoint can transmit, key PTT, or change frequency in this milestone.",
            "Human review remains required before any future transmit path.",
        ],
    }


def install_cq_routes(app, state, config: Dict[str, Any]) -> None:
    @app.route("/api/cq/status")
    def cq_status_route():
        resp = jsonify(cq_status(state.snapshot(), config))
        resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.route("/api/cq/settings", methods=["POST"])
    def cq_settings_route():
        data = request.get_json(silent=True) or {}
        changed = {}
        for key, caster in CQ_SETTINGS_ALLOWLIST.items():
            if key not in data:
                continue
            try:
                value = caster(data[key])
            except Exception:
                continue
            if key == "cq_callsign":
                value = normalise_callsign(value, str(config.get("station_callsign") or "N0CALL").upper())
            elif key == "cq_cat_backend" and value not in ("rigctl", "flrig"):
                value = "rigctl"
            elif key == "cq_cat_model":
                value = str(value or "3073").strip()[:32]
            elif key == "cq_cat_device":
                value = str(value or "/dev/ttyUSB0").strip()[:120]
            elif key == "cq_cat_baud":
                value = clamp_int(value, 1200, 115200, 19200)
            elif key == "cq_band_allowlist":
                value = str(value or "40m,20m,15m,10m").strip()[:120]
            elif key == "cq_busy_rms_threshold":
                value = clamp_float(value, 0.0001, 0.2, 0.006)
            elif key == "cq_busy_snr_threshold_db":
                value = clamp_float(value, 0.0, 40.0, 6.0)
            elif key == "cq_ai_provider" and value not in ("local", "openai"):
                value = "openai"
            elif key == "cq_ai_model":
                value = str(value or "gpt-4.1-mini").strip()[:80]

            config[key] = value
            changed[key] = value

        config["cq_allow_transmit"] = False
        save_config(config)
        state.update(config=config)
        state.append_status(f"CQ Rag Chew settings saved: {', '.join(changed.keys()) or 'none'}")
        return jsonify({"ok": True, "changed": changed, "config": cq_config(config)})

    @app.route("/api/cq/plan", methods=["POST"])
    def cq_plan_route():
        data = request.get_json(silent=True) or {}
        mode = data.get("mode")
        result = cq_plan(state.snapshot(), config, requested_mode=mode)
        return jsonify(result)
