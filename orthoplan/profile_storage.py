"""Local workspace separation, not authentication or an access-control boundary."""
from pathlib import Path
from uuid import UUID
from contextvars import ContextVar
from functools import wraps
import os

from orthoplan.cases import default_case_store

current_profile = ContextVar("ortho_profile", default="default")


def handler_case_store(handler) -> Path:
    raw = os.environ.get("ORTHOPLAN_CASE_STORE")
    return profile_case_store(Path(raw) if raw else default_case_store(), handler.headers.get("X-Ortho-Profile", "default"))


def profile_case_store(base: Path, profile_id: str = "default") -> Path:
    if profile_id == "default":
        return base
    try:
        if str(UUID(profile_id)) != profile_id:
            raise ValueError
    except (ValueError, AttributeError) as exc:
        raise ValueError("Invalid local profile identifier") from exc
    return base.parent / ".orthoplan-profiles" / profile_id / base.name


def profile_directory(base: Path) -> Path:
    identity = current_profile.get()
    return base if identity == "default" else base / "profiles" / identity


def profile_request(method):
    @wraps(method)
    def wrapped(handler):
        identity = handler.headers.get("X-Ortho-Profile", "default")
        try:
            profile_case_store(Path("validate.json"), identity)
        except ValueError:
            handler._send_json(400, {"ok": False, "errors": ["Invalid local profile identifier"]})
            return
        token = current_profile.set(identity)
        try:
            return method(handler)
        finally:
            current_profile.reset(token)
    return wrapped
