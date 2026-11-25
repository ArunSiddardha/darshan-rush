"""Knowledge pack + staff assistant tests. The chat model, translation and speech are mocked: no Sarvam calls."""
import json
import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import addons_staff as st
import kb
import queue_sim
import slots

# (question, lang, entry id that must be in the top 3 hits)
PILGRIM = [
    ("What time does the shrine open and close?", "en", "hours"),
    ("Where can I drink water?", "en", "water_where"),
    ("Where are the toilets?", "en", "toilet_where"),
    ("What can the medical post treat?", "en", "medical_post"),
    ("How do I get a wheelchair or a doli for my mother?", "en", "wheelchair_doli"),
    ("Where is the cloak room and what can I not carry?", "en", "cloak_room"),
    ("Where do I leave my chappals?", "en", "footwear"),
    ("Is there a free meal hall?", "en", "food_hall"),
    ("When is the last bus down?", "en", "transport"),
    ("Is photography allowed?", "en", "faq_photos"),
    ("Someone asked me to pay money to skip the queue", "en", "no_payment"),
    ("My child is lost", "en", "lost_child"),
    ("I feel dizzy and unwell", "en", "feeling_unwell"),
    ("I lost my phone", "en", "lost_phone_slot"),
    ("How many steps are there?", "en", "steps_overview"),
    ("How long does the walk from Forest Path to Queue Complex take?", "en", "walk_g3_g4"),
    ("What is rush mode?", "en", "rush_mode"),
    ("I have no smartphone, how do I book?", "en", "walk_ins"),
    ("Can I change or cancel my slot?", "en", "how_slots_work"),
    ("What should I wear in the cold at night?", "en", "weather_night"),
    ("neellu ekkada dorukutayi", "te", "water_where"),            # romanised Telugu
    ("నీళ్లు ఎక్కడ దొరుకుతాయి", "te", "water_where"),              # Telugu script
    ("kutti kaanunnilla", "ml", "lost_child"),                     # romanised Malayalam
    ("ഡോക്ടർ എവിടെ", "ml", "medical_post"),                       # Malayalam script
    ("pregnant ladies ke liye kya suvidha hai", "hi", "help_pregnant"),  # romanised Hindi
]
UNKNOWN = ["What is the capital of France?", "Who won the cricket world cup?", "Tell me a joke", "How do I fix my laptop screen", "asdf qwer zxcv"]


@pytest.mark.parametrize("q,lang,want", PILGRIM)
def test_pilgrim_question_answered_from_pack(q, lang, want):
    ids = [h["id"] for h in kb.search(q, lang, 3)]
    assert want in ids, (q, ids)
    block = kb.facts_for(q, lang)
    assert block and block.startswith("VENUE FACTS")


@pytest.mark.parametrize("q", UNKNOWN)
def test_unknown_returns_none(q):
    assert kb.facts_for(q, "en") is None


def test_position_adds_stop_context():
    assert "River Crossing" in kb.facts_for("is there a toilet here", "en", "g2")


def test_topics_and_pack_info():
    assert len(kb.topics()) >= 40 and kb.pack_info()["simulated"] is True


def test_every_entry_is_complete_and_simulated():
    p = json.load(open(os.path.join(kb.KNOWLEDGE_DIR, "venue_demo.json"), encoding="utf-8"))
    assert kb.validate(p) == []
    assert [s["id"] for s in p["stops"]] == [g["id"] for g in queue_sim.GATES]
    assert all(e["simulated"] is True and len(e["triggers"]) >= 5 for e in p["entries"])
    must = {"hours", "route_overview", "medical_post", "wheelchair_doli", "cloak_room", "food_hall", "transport", "no_payment", "lost_child", "feeling_unwell",
            "lost_phone_slot", "how_slots_work", "rush_mode", "app_access", "contacts", "help_elders", "help_children", "help_pregnant", "help_disability"}
    assert must <= {e["id"] for e in p["entries"]}


def test_stadium_pack_swaps_in(monkeypatch):
    monkeypatch.setenv("VENUE_PACK", "venue_stadium_demo")
    assert kb.pack_info()["entries"] == 8 and kb.venue_name() == "Demo Arena"
    assert "gate" in kb.facts_for("which gate for my seat", "en").lower()
    assert kb.facts_for("is there first aid", "en")
    monkeypatch.delenv("VENUE_PACK")
    assert kb.venue_name() == "Demo Hill Shrine"


def test_bad_pack_is_a_clear_error(monkeypatch):
    monkeypatch.setenv("VENUE_PACK", "no_such_pack")
    assert kb.search("water", "en") == []          # search never raises
    with pytest.raises(ValueError):
        kb.load()
    monkeypatch.delenv("VENUE_PACK")


# ------------------------------------------------------------------ staff
@pytest.fixture(autouse=True)
def fresh_staff():
    st.HELP.clear(); st.PENDING.clear(); st._RUSH["since"] = None
    yield


def ans(q, **kw):
    return st.answer(q, "en", "t1", use_llm=False, **kw)


def test_staff_twelve_questions():
    slots.book_walk_in("g2"); slots.book("u1", "g3"); st.add_help("g3", "elder breathless")
    queue_sim.report_crowd("g4", 2300)
    cases = [("Which stop is busiest?", "busiest", "Queue Complex"), ("How many bookings in this hour?", "bookings", "2"),
             ("How many walk-ins today?", "walkins", "1 walk-in"), ("Any pilgrim needing help?", "help_open", "Forest Path"),
             ("What did NudgeBee find?", "nudgebee", "NudgeBee"), ("Are we in rush mode?", "rush", "not in rush"),
             ("When is the next free slot?", "next_slot", "next free slot"), ("How long is the wait at Forest Path?", "wait", "Forest Path"),
             ("Is the system healthy?", "health", "Flags come from"), ("What should I tell a pilgrim who lost their child?", "pack", "announcement"),
             ("How many bookings today?", "bookings", "total"), ("Is it rush mode now, since when?", "rush", "rush")]
    for q, intent, frag in cases:
        r = ans(q)
        assert r["intent"] == intent and frag.lower() in r["reply"].lower(), (q, r)


def test_rush_status_since_when():
    queue_sim.set_rush(True); queue_sim.step(1)
    r = ans("are we in rush mode and since when")
    assert "rush mode is on since" in r["reply"]


def test_rush_switch_refused():
    for q in ["switch to staggered mode", "turn on rush mode", "change the map mode to lite"]:
        r = ans(q)
        assert r["intent"] == "rush_switch_refused" and "NudgeBee" in r["reply"]
    assert queue_sim.rush_on() is False


def test_walkin_action_needs_confirmation_then_books():
    r = ans("book a walk-in for two at River Crossing")
    assert r["needs_confirmation"] and r["action"] == {"type": "book_walkin", "stop": "g2", "party": 2} and slots.total() == 0
    r2 = ans("yes")
    assert r2["executed"] and slots.total() == 2 and "River Crossing" in r2["reply"]


def test_crowd_report_action_confirmed_by_flag():
    r = ans("report two thousand waiting at Queue Complex")
    assert r["needs_confirmation"] and r["action"]["count"] == 2000
    r2 = ans("", confirm="yes")
    assert "2000" in r2["reply"] and queue_sim.snapshot()["gates"][3]["load"] == 0.8


def test_help_handled_action_and_no_cancels():
    h = st.add_help("g1", "lost glasses")
    assert ans("mark the help request as handled")["needs_confirmation"]
    assert ans("no")["intent"] == "cancelled" and h["status"] == "open"
    ans("mark the help request as handled")
    assert ans("yes")["executed"] and h["status"] == "handled"
    assert ans("mark the help request as handled")["reply"].startswith("There is no open")


def test_action_without_stop_asks_which():
    assert "Which stop" in ans("book a walk-in for two")["reply"]


def test_malayalam_keyword_question():
    r = ans("ഏത് സ്റ്റോപ്പിലാണ് കൂടുതൽ തിരക്ക്")
    assert r["intent"] == "busiest"


def test_llm_path_validates_numbers(monkeypatch):
    import sarvam
    monkeypatch.setattr(sarvam, "chat_json", lambda s, u: ({"intent": "other", "reply": "There are 9999 pilgrims at the gate.", "action": None, "needs_confirmation": False}, 5))
    r = st.answer("tell me something odd about the queue", "en", "t1")
    assert r["via"] == "llm_rejected_numbers" and "9999" not in r["reply"]
    monkeypatch.setattr(sarvam, "chat_json", lambda s, u: ({"intent": "other", "reply": "Forest Path wait is about 31 minutes.", "action": None, "needs_confirmation": False}, 5))
    queue_sim.report_crowd("g3", 1200)
    w = queue_sim.snapshot()["gates"][2]["wait_min"]
    monkeypatch.setattr(sarvam, "chat_json", lambda s, u: ({"intent": "other", "reply": f"The queue is long, about {w} minutes.", "action": None, "needs_confirmation": False}, 5))
    r = st.answer("is the queue long anywhere", "en", "t1")
    assert r["via"] == "llm" and str(w) in r["reply"]


def test_llm_action_is_validated_and_confirmed(monkeypatch):
    import sarvam
    monkeypatch.setattr(sarvam, "chat_json", lambda s, u: ({"intent": "act", "reply": "ok", "action": {"type": "book_walkin", "stop": "g9", "party": 2}, "needs_confirmation": True}, 5))
    r = st.answer("put two people in", "en", "t1")
    assert not r["needs_confirmation"]                      # bad stop dropped
    monkeypatch.setattr(sarvam, "chat_json", lambda s, u: ({"intent": "act", "reply": "ok", "action": {"type": "book_walkin", "stop": "g1", "party": 3}, "needs_confirmation": True}, 5))
    r = st.answer("put three people in", "en", "t1")
    assert r["needs_confirmation"] and slots.total() == 0


def test_model_down_falls_back_to_pack_or_unknown(monkeypatch):
    import sarvam
    def boom(*a, **k): raise sarvam.SarvamError("down")
    monkeypatch.setattr(sarvam, "chat_json", boom)
    assert st.answer("where is the cloak room", "en", "t1")["via"] == "pack"
    assert st.answer("what is the capital of France", "en", "t1")["reply"] == st.UNKNOWN_MSG


def test_endpoint_json_translates_and_speaks(monkeypatch):
    import sarvam
    monkeypatch.setattr(sarvam, "translate", lambda t, tgt, src="auto": sarvam.TextResult("ML:" + t, 1))
    monkeypatch.setattr(st, "_speak", lambda text, lang: ("QUJD", 3, None))
    app = FastAPI(); app.include_router(st.router)
    c = TestClient(app)
    j = c.post("/api/staff/ask", json={"text": "which stop is busiest", "lang": "ml", "staff_id": "v1"}).json()
    assert j["reply_text"].startswith("ML:") and j["audio_base64"] == "QUJD" and j["intent"] == "busiest"
    j = c.post("/api/staff/ask", json={"text": "book a walk-in for one at Base Camp", "lang": "en", "staff_id": "v1"}).json()
    assert j["needs_confirmation"]
    j = c.post("/api/staff/ask", json={"text": "yes", "lang": "en", "staff_id": "v1"}).json()
    assert j["executed"] and slots.total() == 1
    assert c.get("/api/staff/examples").json()["examples"]
    c.post("/api/staff/help", json={"stop": "g2", "text": "needs doli"})
    assert c.get("/api/staff/help").json()["open"] == 1


def test_endpoint_audio_no_credits(monkeypatch):
    import sarvam
    def nocred(*a, **k): raise sarvam.SarvamNoCredits()
    monkeypatch.setattr(sarvam, "stt", nocred)
    app = FastAPI(); app.include_router(st.router)
    j = TestClient(app).post("/api/staff/ask", files={"audio": ("a.webm", b"x" * 100, "audio/webm")}, data={"lang": "ml"}).json()
    assert "credits" in j["reply_text"].lower() and j["audio_base64"] is None
