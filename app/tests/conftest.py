import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.pop("FLAGSMITH_ENV_KEY", None)
os.environ["HEAVY_MB"] = "1"
os.environ["HEAVY_HOLD_S"] = "0"
os.environ["RUSH_TOKEN"] = "rt"
os.environ["INCIDENT_TOKEN"] = "it"

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def clean():
    import flags, queue_sim, slots
    flags.LOCAL.update(flags.DEFAULTS)
    flags.invalidate_cache()
    flags.EXPOSED["voice"].clear(); flags.EXPOSED["map"].clear()
    flags.REACHED["voice"].clear(); flags.REACHED["map"].clear()
    flags.EVENT_LOG.clear()
    slots.reset()
    queue_sim.reset()
    slots.NOW = __import__("time").time
    yield
