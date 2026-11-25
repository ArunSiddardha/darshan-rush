import os

SARVAM_API_KEY = lambda: os.environ.get("SARVAM_API_KEY", "").strip()
FLAGSMITH_ENV_KEY = lambda: os.environ.get("FLAGSMITH_ENV_KEY", "").strip()
FLAGSMITH_API_URL = lambda: os.environ.get("FLAGSMITH_API_URL", "https://edge.api.flagsmith.com/api/v1/").strip()
FLAGSMITH_ADMIN_KEY = lambda: os.environ.get("FLAGSMITH_ADMIN_KEY", "").strip()
NUDGEBEE_APPROVE_WEBHOOK = lambda: os.environ.get("NUDGEBEE_APPROVE_WEBHOOK", "").strip()
NUDGEBEE_CRASH_WEBHOOK = lambda: os.environ.get("NUDGEBEE_CRASH_WEBHOOK", "").strip()
INCIDENT_TOKEN = lambda: os.environ.get("INCIDENT_TOKEN", "").strip()
RUSH_TOKEN = lambda: os.environ.get("RUSH_TOKEN", "").strip()
HEAVY_MB = lambda: int(os.environ.get("HEAVY_MB", "12") or 12)
HEAVY_HOLD_S = lambda: float(os.environ.get("HEAVY_HOLD_S", "1.5"))
RUSH_RAMP_S = lambda: float(os.environ.get("RUSH_RAMP_S", "3"))  # seconds between each new rush worker starting
STATE_FILE = lambda: os.environ.get("STATE_FILE", "/tmp/darshan-state.json")
PUBLIC_URL = lambda: os.environ.get("PUBLIC_URL", "").strip().rstrip("/")
PORT = lambda: int(os.environ.get("PORT", "8080") or 8080)
SLOT_CAP = lambda: int(os.environ.get("SLOT_CAP", "30") or 30)
SLOT_WINDOW_MIN = lambda: int(os.environ.get("SLOT_WINDOW_MIN", "15") or 15)
RUSH_WORKERS = lambda: int(os.environ.get("RUSH_WORKERS", "16") or 16)


def BOOKINGS_FILE():
    """Bookings live next to STATE_FILE (the /data volume), in their own file so the volunteer state is untouched."""
    return os.path.join(os.path.dirname(STATE_FILE()) or ".", "bookings.json")

# Pilgrim languages (Sarvam codes)
LANGS = {"ml": "ml-IN", "ta": "ta-IN", "te": "te-IN", "kn": "kn-IN", "hi": "hi-IN", "en": "en-IN"}
