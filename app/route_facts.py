"""One source of truth for the SIMULATED pilgrim route: minutes, metres, steps, climb, surface, difficulty.

Every number here is invented for the prototype (a made-up hill shrine). The map, the assistant, GET /api/map and the
knowledge pack all read these same figures. Stops: g1..g5 are the queue stops, "shrine" is the end of the route.
"""

STOPS = ["g1", "g2", "g3", "g4", "g5", "shrine"]
NAMES = {"g1": "Base Camp", "g2": "River Crossing", "g3": "Forest Path", "g4": "Queue Complex", "g5": "Main Steps", "shrine": "the shrine"}

# One entry per stretch, in order. shelters = rest shelters on that stretch (count).
STRETCHES = [
    {"from": "g1", "to": "g2", "minutes": 10, "distance_m": 500, "steps": 40, "climb_m": 10, "surface": "paved path with a few easy steps beside a ramp",
     "difficulty": "easy", "wheelchair": True, "shelters": 0},
    {"from": "g2", "to": "g3", "minutes": 20, "distance_m": 600, "steps": 60, "climb_m": 40, "surface": "footbridge, then gentle uphill",
     "difficulty": "moderate", "wheelchair": True, "shelters": 1},
    {"from": "g3", "to": "g4", "minutes": 30, "distance_m": 700, "steps": 200, "climb_m": 70, "surface": "steep stone steps with two sharp bends",
     "difficulty": "hard", "wheelchair": False, "shelters": 2},
    {"from": "g4", "to": "g5", "minutes": 20, "distance_m": 400, "steps": 120, "climb_m": 40, "surface": "covered railed queue lane",
     "difficulty": "moderate", "wheelchair": True, "shelters": 1},
    {"from": "g5", "to": "shrine", "minutes": 10, "distance_m": 200, "steps": 60, "climb_m": 20, "surface": "short stone stairway",
     "difficulty": "moderate", "wheelchair": False, "shelters": 0},
]
BY_PAIR = {(s["from"], s["to"]): s for s in STRETCHES}
RANK = {"easy": 0, "moderate": 1, "hard": 2}
# Stops that have a rest shelter (the knowledge pack lists the same ones).
SHELTER_STOPS = ["g2", "g3", "g4", "g5"]


def _idx(stop_id):
    return STOPS.index(stop_id) if stop_id in STOPS else None


def _sum(stretches):
    return {"minutes": sum(s["minutes"] for s in stretches), "distance_m": sum(s["distance_m"] for s in stretches),
            "steps": sum(s["steps"] for s in stretches), "climb_m": sum(s["climb_m"] for s in stretches),
            "shelters": sum(s["shelters"] for s in stretches)}


def totals():
    t = _sum(STRETCHES)
    t["hardest"] = hardest(STRETCHES)
    return t


def hardest(stretches):
    """The stretch with the most steps among the hardest difficulty, or None when there are none."""
    if not stretches:
        return None
    best = max(stretches, key=lambda s: (RANK[s["difficulty"]], s["steps"], s["climb_m"]))
    return dict(best)


def stretch(a, b):
    """Facts for the walk between two stops (either direction). Sums when they are not neighbours."""
    i, j = _idx(a), _idx(b)
    if i is None or j is None or i == j:
        return None
    lo, hi = sorted((i, j))
    parts = STRETCHES[lo:hi]
    out = _sum(parts)
    out.update({"from": STOPS[lo], "to": STOPS[hi], "difficulty": max((p["difficulty"] for p in parts), key=RANK.get),
                "wheelchair": all(p["wheelchair"] for p in parts), "hardest": hardest(parts)})
    if len(parts) == 1:
        out["surface"] = parts[0]["surface"]
    return out


def minutes(a, b):
    s = stretch(a, b)
    return s["minutes"] if s else 0


def remaining_from(stop_id, booked_gate=None):
    """What is still ahead of a pilgrim standing at stop_id (None means Base Camp), up to the shrine and up to the booked gate."""
    start = stop_id if stop_id in STOPS else "g1"
    i = STOPS.index(start)
    ahead = STRETCHES[i:]
    out = _sum(ahead)
    out.update({"from": start, "known_position": stop_id in STOPS, "at_shrine": not ahead, "hardest": hardest(ahead),
                "wheelchair": all(s["wheelchair"] for s in ahead),
                "shelter_stops": [g for g in SHELTER_STOPS if STOPS.index(g) > i]})
    out["to_gate"] = None
    if booked_gate in STOPS and STOPS.index(booked_gate) > i:
        out["to_gate"] = dict(_sum(STRETCHES[i:STOPS.index(booked_gate)]), gate=booked_gate)
    elif booked_gate in STOPS:
        out["to_gate"] = dict(_sum([]), gate=booked_gate)
    return out


def describe():
    """Language-neutral dict for the map and the model facts."""
    return {"stretches": [dict(s) for s in STRETCHES], "totals": totals(), "names": dict(NAMES)}


def facts_lines():
    """Plain-text lines for the chat model facts block (no internal ids)."""
    t = totals()
    lines = [f"Whole route (simulated): about {t['distance_m'] / 1000:.1f} km, {t['steps']} steps, {t['climb_m']} m of climb, "
             f"{t['minutes']} minutes of walking from Base Camp to the shrine."]
    for s in STRETCHES:
        ramp = "wheelchair route exists" if s["wheelchair"] else "no wheelchair route, carrying help only"
        lines.append(f"{NAMES[s['from']]} to {NAMES[s['to']]}: {s['minutes']} min, {s['distance_m']} m, {s['steps']} steps, "
                     f"{s['climb_m']} m climb, {s['difficulty']}, {s['surface']}, {ramp}, {s['shelters']} rest shelters.")
    h = t["hardest"]
    lines.append(f"The hardest stretch is {NAMES[h['from']]} to {NAMES[h['to']]} ({h['steps']} steps).")
    return lines
