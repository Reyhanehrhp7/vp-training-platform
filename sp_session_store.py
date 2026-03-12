"""
Simple file-backed live session store for Doctor <-> SP Patient chat.

This module enables two human users to exchange messages in real-time-ish
through a shared JSON file per session.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


LIVE_SESSIONS_DIR = Path("data") / "live_sessions"


def _sanitize_session_id(session_id: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in (session_id or "").strip())
    return cleaned[:80]


def _session_path(session_id: str) -> Path:
    safe_id = _sanitize_session_id(session_id)
    if not safe_id:
        raise ValueError("Session ID cannot be empty")
    LIVE_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    return LIVE_SESSIONS_DIR / f"{safe_id}.json"


def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temp_path.replace(path)


def _default_session_payload(session_id: str) -> Dict[str, Any]:
    now = datetime.now().isoformat()
    return {
        "session_id": _sanitize_session_id(session_id),
        "status": "active",
        "created_at": now,
        "updated_at": now,
        "metadata": {
            "case": "",
            "case_name": "",
            "doctor_id": None,
            "sp_patient_id": None,
        },
        "messages": []
    }


def load_or_create_session(
    session_id: str,
    case_key: Optional[str] = None,
    case_name: Optional[str] = None,
    doctor_id: Optional[str] = None,
    sp_patient_id: Optional[str] = None,
) -> Dict[str, Any]:
    path = _session_path(session_id)
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = _default_session_payload(session_id)

    metadata = payload.setdefault("metadata", {})
    if case_key and not metadata.get("case"):
        metadata["case"] = case_key
    if case_name and not metadata.get("case_name"):
        metadata["case_name"] = case_name
    if doctor_id and not metadata.get("doctor_id"):
        metadata["doctor_id"] = doctor_id
    if sp_patient_id and not metadata.get("sp_patient_id"):
        metadata["sp_patient_id"] = sp_patient_id

    if metadata.get("student_id") and not metadata.get("doctor_id"):
        metadata["doctor_id"] = metadata["student_id"]
    if metadata.get("sp_id") and not metadata.get("sp_patient_id"):
        metadata["sp_patient_id"] = metadata["sp_id"]

    if metadata.get("doctor_id") and not metadata.get("sp_patient_id"):
        payload["status"] = "waiting_sp"
    elif metadata.get("doctor_id") and metadata.get("sp_patient_id"):
        payload["status"] = "active"
    elif payload.get("status") != "closed":
        payload["status"] = "active"

    payload["updated_at"] = datetime.now().isoformat()
    _atomic_write_json(path, payload)
    return payload


def get_session(session_id: str) -> Dict[str, Any]:
    path = _session_path(session_id)
    if not path.exists():
        return _default_session_payload(session_id)
    return json.loads(path.read_text(encoding="utf-8"))


def append_message(session_id: str, sender_role: str, sender_id: str, content: str) -> Dict[str, Any]:
    if not content or not content.strip():
        raise ValueError("Message cannot be empty")

    payload = get_session(session_id)
    payload.setdefault("messages", []).append({
        "timestamp": datetime.now().isoformat(),
        "sender_role": sender_role,
        "sender_id": sender_id,
        "content": content.strip()
    })
    payload["updated_at"] = datetime.now().isoformat()

    path = _session_path(session_id)
    _atomic_write_json(path, payload)
    return payload


def close_session(session_id: str) -> Dict[str, Any]:
    payload = get_session(session_id)
    payload["status"] = "closed"
    payload["updated_at"] = datetime.now().isoformat()

    path = _session_path(session_id)
    _atomic_write_json(path, payload)
    return payload


def get_messages(session_id: str) -> List[Dict[str, Any]]:
    return get_session(session_id).get("messages", [])


def assign_sp_patient(session_id: str, sp_patient_id: str) -> Dict[str, Any]:
    if not sp_patient_id or not sp_patient_id.strip():
        raise ValueError("SP patient ID is required")

    payload = get_session(session_id)
    metadata = payload.setdefault("metadata", {})
    existing_sp = metadata.get("sp_patient_id")

    if existing_sp and existing_sp != sp_patient_id:
        raise ValueError("This session is already joined by another SP patient")

    metadata["sp_patient_id"] = sp_patient_id.strip()
    payload["status"] = "active"
    payload["updated_at"] = datetime.now().isoformat()

    path = _session_path(session_id)
    _atomic_write_json(path, payload)
    return payload


def list_waiting_sessions() -> List[Dict[str, Any]]:
    LIVE_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    sessions: List[Dict[str, Any]] = []

    for path in LIVE_SESSIONS_DIR.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        metadata = payload.get("metadata", {})
        status = payload.get("status")
        if status == "closed":
            continue
        if metadata.get("doctor_id") and not metadata.get("sp_patient_id"):
            sessions.append({
                "session_id": payload.get("session_id"),
                "doctor_id": metadata.get("doctor_id"),
                "case": metadata.get("case"),
                "case_name": metadata.get("case_name"),
                "created_at": payload.get("created_at"),
                "updated_at": payload.get("updated_at"),
            })

    sessions.sort(key=lambda item: item.get("updated_at") or "", reverse=True)
    return sessions
