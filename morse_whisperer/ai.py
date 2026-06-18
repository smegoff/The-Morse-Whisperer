# Local-first rule:
# The decoder and QSO parser always run locally. External AI, when enabled,
# is assistance only: analysis/reply suggestions for human review.
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from flask import jsonify, request


CALLSIGN_RE = re.compile(
    r"\b(?:(?:[A-Z]{1,2}\d[A-Z]{1,4})|(?:\d[A-Z]{1,2}\d[A-Z]{1,4})|(?:ZL\d[A-Z]{1,4})|(?:VK\d[A-Z]{1,4})|(?:K[A-Z0-9]{1,5})|(?:N[A-Z0-9]{1,5})|(?:W[A-Z0-9]{1,5}))\b"
)

RST_RE = re.compile(r"\b(?:RST|RPT|UR|YOU(?:R)?(?:\s+RST)?)?\s*([1-5][1-9][1-9])\b")

COMMON_PROSIGNS = {
    "AR": "end_of_message",
    "SK": "end_of_contact",
    "KN": "specific_station_only",
    "K": "over",
    "BK": "break",
    "BT": "separator",
}

COMMON_ABBREVIATIONS = {
    "CQ": "calling_any_station",
    "DE": "from",
    "UR": "your",
    "RST": "readability_strength_tone",
    "RIG": "radio",
    "ANT": "antenna",
    "PWR": "power",
    "QTH": "location",
    "OP": "operator_name",
    "NAME": "operator_name",
    "HW": "how_copy",
    "CPY": "copy",
    "FB": "fine_business",
    "TNX": "thanks",
    "TU": "thank_you",
    "73": "best_regards",
}


class LocalQsoState:
    """Tiny in-memory QSO state.

    This intentionally does not persist yet. It is safe to restart/clear while
    we are proving the API shape.
    """

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.data: Dict[str, Any] = {
            "their_call": None,
            "my_call": None,
            "stage": "idle",
            "name": None,
            "qth": None,
            "rst_sent": None,
            "rst_received": None,
            "last_copy": "",
            "last_updated": time.time(),
            "notes": [],
        }

    def update(self, values: Dict[str, Any]) -> None:
        for key, value in values.items():
            if value is not None and value != "":
                self.data[key] = value
        self.data["last_updated"] = time.time()

    def snapshot(self) -> Dict[str, Any]:
        return dict(self.data)


_QSO = LocalQsoState()


def _normalise_copy(text: str) -> str:
    text = (text or "").upper()
    text = text.replace("\n", " ")
    text = re.sub(r"[^A-Z0-9/?.=+\- ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _tokens(text: str) -> List[str]:
    return [t for t in _normalise_copy(text).split(" ") if t]


def _extract_callsigns(text: str) -> List[str]:
    found: List[str] = []
    for match in CALLSIGN_RE.findall(_normalise_copy(text)):
        call = match.upper()
        if call not in found and not call.isdigit():
            found.append(call)
    return found


def _extract_rst(text: str) -> Optional[str]:
    match = RST_RE.search(_normalise_copy(text))
    if not match:
        return None
    return match.group(1)


def _detect_intent(text: str) -> str:
    toks = _tokens(text)
    tokset = set(toks)

    if "CQ" in tokset:
        return "calling_cq"
    if "73" in tokset or "SK" in tokset:
        return "signing_off"
    if "RST" in tokset or _extract_rst(text):
        return "sending_report"
    if "?" in text or "HW" in tokset or "CPY" in tokset:
        return "asking_copy"
    if "K" in tokset or "KN" in tokset:
        return "over_to_station"
    if "DE" in tokset:
        return "station_identification"

    return "unknown"


def _extract_qso_fields(text: str, my_call: str) -> Dict[str, Any]:
    text_norm = _normalise_copy(text)
    toks = _tokens(text_norm)
    calls = _extract_callsigns(text_norm)
    rst = _extract_rst(text_norm)

    their_call = None
    my_call_norm = (my_call or "").upper().strip()

    # If "DE CALL" appears, that is normally the sending station.
    if "DE" in toks:
        for i, tok in enumerate(toks):
            if tok == "DE" and i + 1 < len(toks):
                candidate = toks[i + 1]
                if CALLSIGN_RE.match(candidate) and candidate != my_call_norm:
                    their_call = candidate
                    break

    if not their_call:
        for call in calls:
            if call != my_call_norm:
                their_call = call
                break

    # Basic NAME / OP / QTH extraction. Keep this conservative.
    name = None
    qth = None

    for key in ("NAME", "OP"):
        if key in toks:
            idx = toks.index(key)
            if idx + 1 < len(toks):
                candidate = toks[idx + 1]
                if candidate not in COMMON_ABBREVIATIONS and not CALLSIGN_RE.match(candidate):
                    name = candidate.title()
                    break

    if "QTH" in toks:
        idx = toks.index("QTH")
        if idx + 1 < len(toks):
            parts = []
            for tok in toks[idx + 1 : idx + 4]:
                if tok in ("K", "KN", "BK", "BT", "RST", "UR", "HW", "CPY", "73"):
                    break
                if CALLSIGN_RE.match(tok):
                    break
                parts.append(tok.title())
            qth = " ".join(parts) if parts else None

    return {
        "their_call": their_call,
        "callsigns": calls,
        "rst": rst,
        "name": name,
        "qth": qth,
    }


def _latest_copy_from_snapshot(snap: Dict[str, Any]) -> Dict[str, str]:
    decode = snap.get("decode", {}) or {}

    copy = (
        decode.get("copy")
        or decode.get("stable_copy")
        or decode.get("candidate_copy")
        or ""
    )

    raw = (
        decode.get("raw")
        or decode.get("stable_raw")
        or decode.get("candidate_raw")
        or ""
    )

    return {
        "copy": str(copy or ""),
        "raw": str(raw or ""),
    }


def _history_from_snapshot(snap: Dict[str, Any], max_items: int = 10) -> List[Dict[str, Any]]:
    hist = snap.get("decode_history") or snap.get("history") or []
    if not isinstance(hist, list):
        return []

    out = []
    for item in hist[-max_items:]:
        if isinstance(item, dict):
            out.append(item)
        else:
            out.append({"copy": str(item)})
    return out


def analyse_copy_local(text: str, config: Dict[str, Any], snap: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    my_call = str(
        config.get("ai_operator_callsign")
        or config.get("station_callsign")
        or "N0CALL"
    ).upper()

    cleaned = _normalise_copy(text)
    intent = _detect_intent(cleaned)
    fields = _extract_qso_fields(cleaned, my_call)

    qso_update: Dict[str, Any] = {
        "my_call": my_call,
        "last_copy": cleaned,
        "stage": intent,
    }

    if fields.get("their_call"):
        qso_update["their_call"] = fields["their_call"]
    if fields.get("name"):
        qso_update["name"] = fields["name"]
    if fields.get("qth"):
        qso_update["qth"] = fields["qth"]
    if fields.get("rst"):
        qso_update["rst_received"] = fields["rst"]

    _QSO.update(qso_update)

    quality = {}
    if snap:
        q = snap.get("quality", {}) or {}
        quality = {
            "selected_tone_hz": q.get("selected_tone_hz"),
            "wpm": q.get("wpm"),
            "snr_db": q.get("snr_db"),
            "confidence": q.get("confidence"),
            "reason": q.get("reason"),
        }

    warnings = []
    if not cleaned:
        warnings.append("No decoded copy available.")
    if not fields.get("their_call"):
        warnings.append("No remote callsign confidently detected.")

    return {
        "ok": True,
        "cleaned_copy": cleaned,
        "detected_intent": intent,
        "their_call": fields.get("their_call"),
        "my_call": my_call,
        "qso_fields": {
            "callsigns": fields.get("callsigns", []),
            "rst": fields.get("rst"),
            "name": fields.get("name"),
            "qth": fields.get("qth"),
        },
        "qso_state": _QSO.snapshot(),
        "decoder_quality": quality,
        "warnings": warnings,
        "local_only": True,
    }


def suggest_reply_local(analysis: Dict[str, Any], config: Dict[str, Any], requested_mode: Optional[str] = None) -> Dict[str, Any]:
    qso = analysis.get("qso_state", {}) or {}
    my_call = str(qso.get("my_call") or config.get("station_callsign") or "N0CALL").upper()
    their_call = str(qso.get("their_call") or analysis.get("their_call") or "").upper()
    intent = requested_mode or analysis.get("detected_intent") or "unknown"

    if not their_call:
        return {
            "ok": True,
            "suggested_reply_text": "",
            "plain_english": "No callsign was detected, so I am not suggesting a reply yet.",
            "confidence": 0.25,
            "needs_human_review": True,
            "warnings": ["No remote callsign detected."],
            "local_only": True,
        }

    if intent == "calling_cq":
        reply = f"{their_call} DE {my_call} {my_call} KN"
        plain = f"Answering {their_call}'s CQ and inviting them to continue."
        confidence = 0.82
    elif intent == "sending_report":
        reply = f"{their_call} DE {my_call} R RST 599 599 NAME SEAN QTH NAPIER KN"
        plain = "Acknowledging their report and sending a simple report/name/QTH exchange."
        confidence = 0.70
    elif intent == "signing_off":
        reply = f"{their_call} DE {my_call} TU 73 SK"
        plain = "Closing the contact politely."
        confidence = 0.80
    elif intent == "asking_copy":
        reply = f"{their_call} DE {my_call} R R CPY OK HW CPY? KN"
        plain = "Confirming copy and asking how they copy you."
        confidence = 0.68
    else:
        reply = f"{their_call} DE {my_call} R R KN"
        plain = "Generic acknowledgement. Human review strongly recommended."
        confidence = 0.55

    return {
        "ok": True,
        "suggested_reply_text": reply,
        "plain_english": plain,
        "confidence": confidence,
        "needs_human_review": True,
        "warnings": [],
        "local_only": True,
    }




# MW_AI_PROVIDER_REPAIR_V2
# Local-first rule:
# - Local decode and local QSO parsing always run first.
# - External AI providers are optional assistance only.
# - If a provider fails, local result is returned with a warning.

def _strip_code_fences(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_response_text(payload: Dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]

    chunks: List[str] = []
    for item in payload.get("output", []) or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []) or []:
            if not isinstance(content, dict):
                continue
            if content.get("type") in ("output_text", "text") and isinstance(content.get("text"), str):
                chunks.append(content["text"])
    return "\n".join(chunks).strip()


def _chat_completion_text(payload: Dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices or not isinstance(choices[0], dict):
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    return ""


def _gemini_response_text(payload: Dict[str, Any]) -> str:
    chunks: List[str] = []
    for candidate in payload.get("candidates", []) or []:
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("content") or {}
        for part in content.get("parts", []) or []:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                chunks.append(part["text"])
    return "\n".join(chunks).strip()


def _provider(config: Dict[str, Any]) -> str:
    return str(config.get("ai_provider", "local") or "local").strip().lower()


def _external_ai_enabled(config: Dict[str, Any]) -> bool:
    return bool(config.get("ai_enabled", False)) and _provider(config) in {"openai", "gemini", "groq", "openrouter"}


def _env_key(config: Dict[str, Any], provider: str) -> str:
    explicit = str(config.get("ai_api_key_env") or "").strip()
    if explicit and not (provider != "openai" and explicit == "OPENAI_API_KEY"):
        return explicit
    return {
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "groq": "GROQ_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
    }.get(provider, "OPENAI_API_KEY")


def _parse_provider_json(provider: str, model: str, output_text: str) -> Dict[str, Any]:
    if not output_text:
        raise RuntimeError(f"{provider} response did not include output text")

    try:
        parsed = json.loads(_strip_code_fences(output_text))
    except Exception as e:
        raise RuntimeError(f"{provider} output was not valid JSON: {output_text[:600]}") from e

    if not isinstance(parsed, dict):
        raise RuntimeError(f"{provider} output JSON was not an object")

    parsed["provider"] = provider
    parsed["model"] = model
    parsed["local_only"] = False
    return parsed


def _openai_request(config: Dict[str, Any], messages: List[Dict[str, str]]) -> Dict[str, Any]:
    api_key_env = _env_key(config, "openai")
    api_key = os.environ.get(api_key_env, "").strip()

    if not api_key:
        raise RuntimeError(f"{api_key_env} is not set in systemd environment")

    model = str(config.get("ai_model") or "gpt-4.1-mini")
    timeout = float(config.get("ai_timeout_sec", 20) or 20)

    body = {
        "model": model,
        "input": messages,
        "temperature": float(config.get("ai_temperature", 0.2) or 0.2),
        "max_output_tokens": int(config.get("ai_max_output_tokens", 700) or 700),
    }

    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            payload = json.loads(raw)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"OpenAI HTTP {e.code}: {detail[:600]}") from e

    return _parse_provider_json("openai", model, _extract_response_text(payload))


def _chat_request(
    config: Dict[str, Any],
    provider: str,
    messages: List[Dict[str, str]],
    url: str,
    default_model: str,
) -> Dict[str, Any]:
    api_key_env = _env_key(config, provider)
    api_key = os.environ.get(api_key_env, "").strip()

    if not api_key:
        raise RuntimeError(f"{api_key_env} is not set in systemd environment")

    model = str(config.get("ai_model") or default_model)
    timeout = float(config.get("ai_timeout_sec", 20) or 20)
    body = {
        "model": model,
        "messages": messages,
        "temperature": float(config.get("ai_temperature", 0.2) or 0.2),
        "max_tokens": int(config.get("ai_max_output_tokens", 700) or 700),
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if provider == "openrouter":
        headers["HTTP-Referer"] = str(config.get("ai_site_url") or "http://morse-whisperer.local")
        headers["X-Title"] = str(config.get("ai_app_title") or "The Morse Whisperer")

    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            payload = json.loads(raw)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"{provider} HTTP {e.code}: {detail[:600]}") from e

    return _parse_provider_json(provider, model, _chat_completion_text(payload))


def _gemini_request(config: Dict[str, Any], messages: List[Dict[str, str]]) -> Dict[str, Any]:
    api_key_env = _env_key(config, "gemini")
    api_key = os.environ.get(api_key_env, "").strip()

    if not api_key:
        raise RuntimeError(f"{api_key_env} is not set in systemd environment")

    model = str(config.get("ai_model") or "gemini-2.5-flash-lite")
    timeout = float(config.get("ai_timeout_sec", 20) or 20)
    system_text = "\n".join(m["content"] for m in messages if m.get("role") == "system")
    user_text = "\n\n".join(m["content"] for m in messages if m.get("role") != "system")
    body = {
        "contents": [{"role": "user", "parts": [{"text": user_text}]}],
        "generationConfig": {
            "temperature": float(config.get("ai_temperature", 0.2) or 0.2),
            "maxOutputTokens": int(config.get("ai_max_output_tokens", 700) or 700),
            "responseMimeType": "application/json",
        },
    }
    if system_text:
        body["systemInstruction"] = {"parts": [{"text": system_text}]}

    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            payload = json.loads(raw)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"gemini HTTP {e.code}: {detail[:600]}") from e

    return _parse_provider_json("gemini", model, _gemini_response_text(payload))


def _provider_request(config: Dict[str, Any], messages: List[Dict[str, str]]) -> Dict[str, Any]:
    provider = _provider(config)
    if provider == "openai":
        return _openai_request(config, messages)
    if provider == "gemini":
        return _gemini_request(config, messages)
    if provider == "groq":
        return _chat_request(
            config,
            provider,
            messages,
            "https://api.groq.com/openai/v1/chat/completions",
            "llama-3.1-8b-instant",
        )
    if provider == "openrouter":
        return _chat_request(
            config,
            provider,
            messages,
            "https://openrouter.ai/api/v1/chat/completions",
            "openrouter/free",
        )
    raise RuntimeError(f"Unsupported AI provider: {provider}")


def transcribe_audio_gemini(wav_bytes: bytes, config: Dict[str, Any], sample_rate: int, duration_sec: float) -> Dict[str, Any]:
    api_key_env = _env_key(config, "gemini")
    api_key = os.environ.get(api_key_env, "").strip()

    if not api_key:
        raise RuntimeError(f"{api_key_env} is not set in systemd environment")
    if not wav_bytes:
        raise RuntimeError("No audio bytes supplied")

    model = str(
        config.get("cq_voice_model")
        or config.get("cq_ai_model")
        or config.get("ai_model")
        or "gemini-2.5-flash-lite"
    )
    timeout = float(config.get("ai_timeout_sec", 30) or 30)
    prompt = (
        "Transcribe the speech in this amateur radio receive audio. "
        "The audio may contain QRM, QRN, weak modulation, static, heterodynes, and silence. "
        "Return strict JSON only with keys: ok, transcript, confidence, language, "
        "heard_speech, callsigns, summary, warnings. "
        "Do not invent words, callsigns, signal reports, names, or locations. "
        "If speech is not intelligible, set transcript to an empty string, heard_speech to false, "
        "and explain briefly in warnings."
    )
    body = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {
                        "inlineData": {
                            "mimeType": "audio/wav",
                            "data": base64.b64encode(wav_bytes).decode("ascii"),
                        }
                    },
                ],
            }
        ],
        "generationConfig": {
            "temperature": float(config.get("ai_temperature", 0.1) or 0.1),
            "maxOutputTokens": int(config.get("ai_max_output_tokens", 700) or 700),
            "responseMimeType": "application/json",
        },
    }

    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            payload = json.loads(raw)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"gemini HTTP {e.code}: {detail[:800]}") from e

    output_text = _gemini_response_text(payload)
    if not output_text:
        raise RuntimeError("gemini response did not include output text")

    try:
        parsed = json.loads(_strip_code_fences(output_text))
    except Exception:
        parsed = {
            "ok": True,
            "transcript": output_text.strip(),
            "confidence": 0.5,
            "language": None,
            "heard_speech": bool(output_text.strip()),
            "callsigns": [],
            "summary": "",
            "warnings": ["Gemini returned plain text instead of JSON."],
        }

    if not isinstance(parsed, dict):
        raise RuntimeError("gemini transcript output JSON was not an object")

    parsed.setdefault("ok", True)
    parsed.setdefault("transcript", "")
    parsed.setdefault("confidence", 0.0)
    parsed.setdefault("heard_speech", bool(str(parsed.get("transcript") or "").strip()))
    parsed.setdefault("warnings", [])
    parsed["provider"] = "gemini"
    parsed["model"] = model
    parsed["sample_rate"] = int(sample_rate)
    parsed["duration_sec"] = float(duration_sec)
    parsed["local_only"] = False
    return parsed


def transcribe_audio_pocketsphinx(wav_bytes: bytes, config: Dict[str, Any], sample_rate: int, duration_sec: float) -> Dict[str, Any]:
    exe = shutil.which("pocketsphinx_continuous")
    if not exe:
        raise RuntimeError("pocketsphinx_continuous is not installed")
    if not wav_bytes:
        raise RuntimeError("No audio bytes supplied")

    timeout = float(config.get("voice_local_timeout_sec", 25) or 25)
    with tempfile.NamedTemporaryFile(prefix="mw-voice-", suffix=".wav", delete=False) as handle:
        path = handle.name
        handle.write(wav_bytes)

    try:
        cp = subprocess.run(
            [
                exe,
                "-infile",
                path,
                "-samprate",
                str(int(sample_rate)),
                "-logfn",
                "/dev/null",
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass

    text_lines: List[str] = []
    for line in (cp.stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        upper = line.upper()
        if upper.startswith(("READY", "LISTENING", "ERROR", "INFO")):
            continue
        text_lines.append(line)

    transcript = " ".join(text_lines).strip()
    warnings = []
    if cp.returncode not in (0,):
        warnings.append(f"PocketSphinx exited with code {cp.returncode}.")
    if cp.stderr.strip():
        warnings.append(cp.stderr.strip()[:300])
    if not transcript:
        warnings.append("PocketSphinx did not find intelligible speech.")

    return {
        "ok": True,
        "provider": "pocketsphinx",
        "model": "pocketsphinx-en-us",
        "transcript": transcript,
        "confidence": 0.35 if transcript else 0.0,
        "language": "en-US",
        "heard_speech": bool(transcript),
        "callsigns": _extract_callsigns(transcript),
        "summary": transcript[:160],
        "warnings": warnings,
        "sample_rate": int(sample_rate),
        "duration_sec": float(duration_sec),
        "local_only": True,
    }


def _analysis_prompt(text: str, config: Dict[str, Any], snap: Optional[Dict[str, Any]], local: Dict[str, Any]) -> List[Dict[str, str]]:
    context = {
        "my_callsign": local.get("my_call") or config.get("ai_operator_callsign") or config.get("station_callsign") or "N0CALL",
        "decoded_copy": text,
        "local_analysis": local,
        "qso_state": _QSO.snapshot(),
        "decoder_quality": local.get("decoder_quality", {}),
    }

    system = (
        "You are assisting an amateur radio CW operator. "
        "Return strict JSON only. Do not use markdown. "
        "Do not invent callsigns, RST reports, names, QTHs, or facts. "
        "Preserve uncertainty. Keep the output concise. "
        "Never claim that anything was transmitted."
    )

    user = (
        "Analyse this CW decoded text. Return JSON with these keys: "
        "ok, cleaned_copy, detected_intent, their_call, my_call, qso_fields, "
        "qso_state_update, warnings, confidence, plain_english. "
        "qso_fields must contain callsigns, rst, name, qth. "
        "qso_state_update must only include facts supported by the decode. "
        "Context:\n"
        + json.dumps(context, ensure_ascii=False, indent=2)
    )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _reply_prompt(analysis: Dict[str, Any], config: Dict[str, Any], local_reply: Dict[str, Any], requested_mode: Optional[str]) -> List[Dict[str, str]]:
    context = {
        "my_callsign": analysis.get("my_call") or config.get("ai_operator_callsign") or config.get("station_callsign") or "N0CALL",
        "requested_mode": requested_mode,
        "analysis": analysis,
        "local_suggested_reply": local_reply,
        "qso_state": _QSO.snapshot(),
        "reply_style": config.get("ai_reply_style", "short_cw"),
    }

    system = (
        "You are assisting an amateur radio CW operator. "
        "Return strict JSON only. Do not use markdown. "
        "Suggested replies must be short CW text for human review. "
        "Do not invent received details. "
        "Never auto-transmit and never claim something was transmitted."
    )

    user = (
        "Suggest a CW reply. Return JSON with these keys: "
        "ok, suggested_reply_text, plain_english, confidence, needs_human_review, warnings. "
        "If too uncertain, return an empty suggested_reply_text and a warning. "
        "Context:\n"
        + json.dumps(context, ensure_ascii=False, indent=2)
    )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def analyse_copy(text: str, config: Dict[str, Any], snap: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    local = analyse_copy_local(text, config, snap=snap)
    local.setdefault("provider", "local")
    local.setdefault("local_only", True)

    if not _external_ai_enabled(config):
        return local

    provider = _provider(config)
    try:
        result = _provider_request(config, _analysis_prompt(text, config, snap, local))

        cleaned = _normalise_copy(str(result.get("cleaned_copy") or local.get("cleaned_copy") or text))
        result.setdefault("ok", True)
        result.setdefault("cleaned_copy", cleaned)
        result.setdefault("detected_intent", local.get("detected_intent"))
        result.setdefault("their_call", local.get("their_call"))
        result.setdefault("my_call", local.get("my_call"))
        result.setdefault("qso_fields", local.get("qso_fields", {}))
        result.setdefault("warnings", [])
        result["decoder_quality"] = local.get("decoder_quality", {})

        qso_update = result.get("qso_state_update") or {}
        if not isinstance(qso_update, dict):
            qso_update = {}

        if result.get("their_call"):
            qso_update.setdefault("their_call", result.get("their_call"))
        qso_update.setdefault("my_call", result.get("my_call") or local.get("my_call"))
        qso_update.setdefault("last_copy", cleaned)
        qso_update.setdefault("stage", result.get("detected_intent") or local.get("detected_intent"))

        _QSO.update(qso_update)
        result["qso_state"] = _QSO.snapshot()
        result["fallback_used"] = False
        return result

    except Exception as e:
        local["fallback_used"] = True
        local.setdefault("warnings", [])
        local["warnings"].append(f"{provider} provider failed; local fallback used: {e}")
        return local


def suggest_reply(analysis: Dict[str, Any], config: Dict[str, Any], requested_mode: Optional[str] = None) -> Dict[str, Any]:
    local = suggest_reply_local(analysis, config, requested_mode=requested_mode)
    local.setdefault("provider", "local")
    local.setdefault("local_only", True)

    if not _external_ai_enabled(config):
        return local

    provider = _provider(config)
    try:
        result = _provider_request(config, _reply_prompt(analysis, config, local, requested_mode))
        result.setdefault("ok", True)
        result.setdefault("suggested_reply_text", local.get("suggested_reply_text", ""))
        result.setdefault("plain_english", local.get("plain_english", ""))
        result.setdefault("confidence", local.get("confidence", 0.5))
        result.setdefault("needs_human_review", True)
        result.setdefault("warnings", [])
        result["needs_human_review"] = True
        result["fallback_used"] = False
        return result

    except Exception as e:
        local["fallback_used"] = True
        local.setdefault("warnings", [])
        local["warnings"].append(f"{provider} provider failed; local fallback used: {e}")
        return local




def install_ai_routes(app, state, config: Dict[str, Any]) -> None:
    """Register local AI/Copilot API routes on the Flask app."""

    @app.route("/api/ai/context", methods=["GET"])
    def ai_context():
        snap = state.snapshot()
        latest = _latest_copy_from_snapshot(snap)

        return jsonify({
            "ok": True,
            "copy": latest["copy"],
            "raw": latest["raw"],
            "history": _history_from_snapshot(snap, int(config.get("ai_max_history_items", 10))),
            "quality": snap.get("quality", {}) or {},
            "qso_state": _QSO.snapshot(),
            "ai_enabled": bool(config.get("ai_enabled", False)),
            "local_only": True,
        })

    @app.route("/api/ai/analyse", methods=["POST"])
    def ai_analyse():
        snap = state.snapshot()
        data = request.get_json(silent=True) or {}
        latest = _latest_copy_from_snapshot(snap)

        text = str(data.get("copy") or data.get("text") or latest["copy"] or latest["raw"] or "")
        result = analyse_copy(text, config, snap=snap)
        return jsonify(result)

    @app.route("/api/ai/reply", methods=["POST"])
    def ai_reply():
        snap = state.snapshot()
        data = request.get_json(silent=True) or {}
        latest = _latest_copy_from_snapshot(snap)

        text = str(data.get("copy") or data.get("text") or latest["copy"] or latest["raw"] or "")
        mode = data.get("mode")
        analysis = analyse_copy(text, config, snap=snap)
        reply = suggest_reply(analysis, config, requested_mode=mode)

        return jsonify({
            "ok": True,
            "analysis": analysis,
            "reply": reply,
        })

    @app.route("/api/ai/qso/reset", methods=["POST"])
    def ai_qso_reset():
        _QSO.reset()
        try:
            state.append_status("AI Copilot QSO context reset")
        except Exception:
            pass
        return jsonify({
            "ok": True,
            "qso_state": _QSO.snapshot(),
        })
