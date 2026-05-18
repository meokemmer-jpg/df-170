
# K16: Concurrent-Spawn-Mutex (fcntl-based, Trinity-CONSERVATIVE 2026-05-17)
def k16_lock_or_exit(df_name: str):
    """Acquire exclusive lock or exit(3). Prevents concurrent DF runs."""
    import fcntl, os, sys
    lock_path = f"/tmp/df-trinity-{df_name}.lock"
    fd = os.open(lock_path, os.O_CREAT | os.O_WRONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except BlockingIOError:
        sys.exit(3)


# K13: External-Anchor-Mock-RFC3161 (Trinity-CONSERVATIVE 2026-05-17)
def k13_anchor(payload_hash: str) -> dict:
    """Mock RFC3161-style timestamp anchor."""
    from datetime import datetime, timezone
    return {
        "anchor_type": "rfc3161-mock",
        "iso_ts": datetime.now(timezone.utc).isoformat(),
        "payload_hash": payload_hash,
    }


# K12: HMAC-SHA256-Provenance (Trinity-CONSERVATIVE 2026-05-17)
def k12_provenance(payload: bytes, key: bytes = b"df-trinity-conservative-v1") -> dict:
    """Returns payload_hash + HMAC-SHA256 signature."""
    import hashlib, hmac
    return {
        "payload_hash": hashlib.sha256(payload).hexdigest(),
        "hmac_sha256": hmac.new(key, payload, hashlib.sha256).hexdigest(),
    }

"""DF-170 engine for Buecher-Sales-Watch tracking output."""

import re
import os
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime, timezone

DF_DIR = Path(__file__).parent
LOCK_DIR = Path("/tmp/df-170.lock")
DF_ID = "170"
DECISION_KEYWORDS_REGEX = re.compile(
    r"\b(entscheid[a-z]*|empfehl(?:e|en|t|st)|sollt(?:e|en|est)|recommend[a-z]*|decid[a-z]*|advis[a-z]*|propos[a-z]*)\b",
    re.IGNORECASE,
)


@dataclass
class TrackerOutput:
    welle: str = "25"
    df: str = "DF-170"
    iso_timestamp: str = ""
    source: str = "mock"
    sales_total_units: int = 0
    revenue_eur: float = 0.0
    sales_per_book: dict = field(default_factory=dict)
    ranking_per_marketplace: dict = field(default_factory=dict)
    review_count: int = 0


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _file_stable(path, min_age_sec=300) -> bool:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return False
    try:
        age = time.time() - p.stat().st_mtime
    except OSError:
        return False
    return age >= min_age_sec


def acquire_lock_with_identity() -> bool:
    stale_after_sec = 6 * 60 * 60
    now = time.time()

    try:
        LOCK_DIR.mkdir(mode=0o700)
    except FileExistsError:
        try:
            age = now - LOCK_DIR.stat().st_mtime
        except OSError:
            return False

        if age <= stale_after_sec:
            return False

        try:
            for child in LOCK_DIR.iterdir():
                if child.is_file() or child.is_symlink():
                    child.unlink()
            LOCK_DIR.rmdir()
            LOCK_DIR.mkdir(mode=0o700)
        except OSError:
            return False
    except OSError:
        return False

    identity = {
        "pid": os.getpid(),
        "created_at": iso_now(),
        "df_id": DF_ID,
        "cwd": str(Path.cwd()),
    }

    try:
        (LOCK_DIR / "identity.json").write_text(
            json.dumps(identity, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        release_lock()
        return False

    return True


def release_lock() -> None:
    try:
        for child in LOCK_DIR.iterdir():
            if child.is_file() or child.is_symlink():
                child.unlink()
        LOCK_DIR.rmdir()
    except FileNotFoundError:
        return
    except OSError:
        return


def k17_pre_action_verification(anchors) -> dict:
    missing = []
    for anchor in anchors or []:
        p = Path(anchor)
        if not p.is_absolute():
            p = DF_DIR / p
        if not p.exists():
            missing.append(str(anchor))

    return {
        "ok": not missing,
        "missing_anchors": missing,
        "env_tag": "real" if _is_real_api_enabled() else "mock",
    }


def _is_real_api_enabled() -> bool:
    raw = os.environ.get("DF_170_REAL_API_ENABLED", "false")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def scan_output_for_decision_keywords(text) -> list:
    if text is None:
        return []
    seen = []
    for match in DECISION_KEYWORDS_REGEX.finditer(str(text)):
        token = match.group(0)
        if token.lower() not in {x.lower() for x in seen}:
            seen.append(token)
    return seen


def assert_no_decision_keywords(output) -> None:
    if not isinstance(output, str):
        output = json.dumps(output, ensure_ascii=False, sort_keys=True)
    hits = scan_output_for_decision_keywords(output)
    if hits:
        raise ValueError("Q_0/K_0 keyword block hit: " + ", ".join(hits))


def collect_tracker_output() -> TrackerOutput:
    out = TrackerOutput()
    out.iso_timestamp = iso_now()

    if _is_real_api_enabled():
        out.source = "real"
        out.sales_total_units = int(os.environ.get("DF_170_SALES_TOTAL_UNITS", "0"))
        out.revenue_eur = float(os.environ.get("DF_170_REVENUE_EUR", "0") or "0")
        out.review_count = int(os.environ.get("DF_170_REVIEW_COUNT", "0"))
        out.sales_per_book = _json_env_dict("DF_170_SALES_PER_BOOK")
        out.ranking_per_marketplace = _json_env_dict("DF_170_RANKING_PER_MARKETPLACE")
        return out

    out.source = "mock"
    out.sales_total_units = 0
    out.revenue_eur = 0.0
    out.sales_per_book = {}
    out.ranking_per_marketplace = {}
    out.review_count = 0
    return out


def _json_env_dict(name: str) -> dict:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _report_path() -> Path:
    day = datetime.now(timezone.utc).date().isoformat()
    return DF_DIR / "reports" / f"df-170-{day}.json"


def main() -> int:
    locked = acquire_lock_with_identity()
    if not locked:
        return 3

    try:
        pav = k17_pre_action_verification([])
        if not pav.get("ok"):
            return 3

        tracker = collect_tracker_output()
        payload = asdict(tracker)
        payload["k17_pre_action_verification"] = pav

        assert_no_decision_keywords(payload)

        report_path = _report_path()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return 0
    except Exception as exc:
        err = {
            "df": "DF-170",
            "iso_timestamp": iso_now(),
            "source": "error",
            "error_type": exc.__class__.__name__,
            "error": str(exc),
        }
        try:
            assert_no_decision_keywords(err)
            report_path = _report_path()
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(
                json.dumps(err, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        except Exception:
            pass
        return 3
    finally:
        release_lock()


if __name__ == "__main__":
    sys.exit(main())