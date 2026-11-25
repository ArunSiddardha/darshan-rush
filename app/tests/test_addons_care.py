"""Care requests. The Sarvam model is mocked; no network, no credits."""
import json
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import addons_care as care
import care_store as store


@pytest.fixture(autouse=True)
def fresh(tmp_path, monkeypatch):
    monkeypatch.setenv("STATE_FILE", str(tmp_path / "state.json"))
    store.reload()
    store.reset()
    store.NOW = time.time
    care.set_policy_source(None)
    care.set_hooks(None, None)
    # every network call fails loudly: the rules must carry the tests
    import sarvam

    def boom(*a, **k):
        raise sarvam.SarvamError("mocked: no network in tests")
    monkeypatch.setattr(sarvam, "chat_json", boom)
    monkeypatch.setattr(sarvam, "tts", boom)
    monkeypatch.setattr(sarvam, "stt", boom)
    yield
    store.NOW = time.time


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(care.router)
    return TestClient(app)


# (utterance, language, category, urgency, stop named)
CASES = [
    ("my father fainted", "en", "medical", "emergency", None),
    ("my wife is not breathing near forest path", "en", "medical", "emergency", "g3"),
    ("naa abbai kanipinchatledu", "te", "lost_person", "emergency", None),
    ("నా కొడుకు కనిపించడం లేదు", "te", "lost_person", "emergency", None),
    ("someone is asking 500 rupees for quick darshan", "en", "tout_payment", "urgent", None),
    ("ఎవరో డబ్బులు అడుగుతున్నారు దర్శనం కోసం", "te", "tout_payment", "urgent", None),
    ("toilet is dirty at river crossing", "en", "water_toilet_clean", "normal", "g2"),
    ("I lost my phone", "en", "lost_item", "normal", None),
    ("wheelchair kavali", "te", "accessibility", "urgent", None),
    ("எங்க அம்மாவுக்கு மயக்கம் வந்துடுச்சு", "ta", "medical", "emergency", None),
    ("என் மகன் காணவில்லை", "ta", "lost_person", "emergency", None),
    ("கழிப்பறை மிகவும் அழுக்காக இருக்கிறது", "ta", "water_toilet_clean", "normal", None),
    ("ഒരാൾ പണം ചോദിക്കുന്നു, ക്വിക്ക് ദർശനത്തിന് 500 രൂപ", "ml", "tout_payment", "urgent", None),
    ("എന്റെ മകനെ കാണുന്നില്ല", "ml", "lost_person", "emergency", None),
    ("അച്ഛൻ ബോധം കെട്ടു വീണു", "ml", "medical", "emergency", None),
    ("വീൽചെയർ വേണം", "ml", "accessibility", "urgent", None),
    ("ನನ್ನ ತಾಯಿಗೆ ಎದೆ ನೋವು", "kn", "medical", "emergency", None),
    ("ಶೌಚಾಲಯ ತುಂಬಾ ಕೊಳಕಾಗಿದೆ", "kn", "water_toilet_clean", "normal", None),
    ("ನನ್ನ ಮಗು ಕಾಣುತ್ತಿಲ್ಲ", "kn", "lost_person", "emergency", None),
    ("मेरे पिताजी बेहोश हो गए", "hi", "medical", "emergency", None),
    ("मेरा बेटा खो गया", "hi", "lost_person", "emergency", None),
    ("मेरा फोन खो गया", "hi", "lost_item", "normal", None),
    ("कोई पैसे मांग रहा है दर्शन के लिए", "hi", "tout_payment", "urgent", None),
    ("किसी ने मेरा पर्स चुरा लिया चोर", "hi", "harassment_theft", "urgent", None),
    ("बुजुर्ग को व्हीलचेयर चाहिए", "hi", "accessibility", "urgent", None),
    ("there is a stampede, we are getting crushed at queue complex", "en", "safety_crowd", "emergency", "g4"),
    ("the crowd is pushing a lot", "en", "safety_crowd", "urgent", None),
    ("a volunteer shouted at me and was very rude", "en", "staff_behaviour", "normal", None),
    ("my slot booking is not confirmed", "en", "slot_booking", "normal", None),
    ("I suggest you add more benches, feedback", "en", "suggestion", "normal", None),
    ("my daughter is missing, I cannot find her", "en", "lost_person", "emergency", None),
    ("my grandmother is lost and I cannot find her", "en", "lost_person", "urgent", None),
    ("someone is following me and harassing me", "en", "harassment_theft", "urgent", None),
    ("mera pita behosh ho gaya", "hi", "medical", "emergency", None),
    ("neellu ledu toilet lo", "te", "water_toilet_clean", "normal", None),
]


@pytest.mark.parametrize("text,lang,cat,urg,stop", CASES)
def test_classification_without_model(text, lang, cat, urg, stop):
    c, u, why, conf = care.classify_rules(text)
    assert (c, u) == (cat, urg), (text, c, u)
    assert why and conf
    import gatematch
    assert gatematch.best_gate(text) == stop


def test_unclear_text_is_other_and_not_confident():
    assert care.classify_rules("hello hello")[3] is False
    assert care.classify_rules("")[0] == "other"


def test_30_plus_cases():
    assert len(CASES) >= 30


# ------------------------------------------------------------------ routing
def _req(stop, lang="en", urg="normal"):
    return {"stop_id": stop, "language": lang, "urgency": urg}


def test_same_stop_first_then_adjacent():
    assert care.pick_volunteer(_req("g1", "en"))["stop"] == "g1"
    assert care.pick_volunteer(_req("g4", "en"))["stop"] == "g4"
    store.checkin("Zed", "g2", ["en"], on_duty=False)
    v = care.pick_volunteer(_req("g3", "ta", "normal"))          # Meera and Joseph at g3 (ml); Tamil speaker Lakshmi is 1 stop away
    assert v["name"] in ("Lakshmi", "Karthik", "Joseph")


def test_language_preference_within_slack():
    # g2 has Lakshmi (ta) and Karthik (te, ta); Telugu pilgrim at g2 gets Karthik
    assert care.pick_volunteer(_req("g2", "te"))["name"] == "Karthik"
    assert care.pick_volunteer(_req("g2", "ta"))["name"] in ("Lakshmi", "Karthik")
    # Malayalam pilgrim at g2: nearest Malayalam speaker is at g3, one stop away: allowed for normal, not for an emergency
    assert care.pick_volunteer(_req("g2", "ml", "normal"))["name"] in ("Meera", "Joseph")
    assert care.pick_volunteer(_req("g2", "ml", "emergency"))["stop"] == "g2"


def test_off_duty_skipped_and_nobody_left():
    for v in store.volunteers():
        store.checkin(v["name"], v["stop"], v["langs"], on_duty=False)
    assert care.pick_volunteer(_req("g3")) is None


def test_checkin_makes_real_volunteer():
    v = store.checkin("Arun", "g5", ["te", "en"])
    assert v["simulated"] is False and v["on_duty"]
    assert care.pick_volunteer(_req("g5", "te"))["name"] == "Arun"


# ------------------------------------------------------------------ emergency path and replies
def test_emergency_never_waits_for_model(monkeypatch):
    import sarvam
    called = []
    monkeypatch.setattr(sarvam, "chat_json", lambda *a, **k: called.append(1) or ({}, 1))
    r, asked, q, _ = care.open_request("my father fainted at forest path", "u1", "en")
    assert called == []
    assert r["urgency"] == "emergency" and r["category"] == "medical" and r["status"] == "assigned"
    assert r["assigned_to"]["stop"] == "g3" and r["duty_officer_notified"] is True
    reply = care.build_reply(r)
    assert "Forest Path" in reply and "stay with them" in reply.lower()
    low = reply.lower()
    assert "police" not in low and "ambulance" not in low


def test_reply_in_each_language_is_in_script_and_never_claims_ambulance():
    for lang in ("hi", "te", "ta", "ml", "kn"):
        r, *_ = care.open_request("I need medical help", f"u-{lang}", lang, choice="medical", stop_id="g3")
        reply = care.build_reply(r)
        assert sum(1 for ch in reply if ord(ch) > 0x2FF) > 20
        assert r["assigned_to"]["name"] in reply
        assert str(r["assigned_to"]["eta_min"]) in reply
        assert "C 1" in reply or "C 2" in reply or "C" in reply


def test_model_used_only_when_rules_unsure_and_is_validated(monkeypatch):
    import sarvam
    monkeypatch.setattr(sarvam, "chat_json", lambda s, u: ({"category": "water_toilet_clean", "urgency": "normal", "stop_id": "g5", "summary_en": "No water at the steps",
                                                            "question": ""}, 5))
    r, asked, q, _ = care.open_request("xyzzy blorp", "u1", "en")
    assert r["category"] == "water_toilet_clean" and r["stop_id"] == "g5" and r["via"] == "model" and not asked
    # garbage from the model is rejected and the rules decide
    monkeypatch.setattr(sarvam, "chat_json", lambda s, u: ({"category": "nonsense", "urgency": "extreme"}, 5))
    r2, *_ = care.open_request("xyzzy blorp two", "u2", "en")
    assert r2["category"] == "other" and r2["via"] == "rules_fallback"
    assert care.validate_model({"category": "medical", "urgency": "urgent", "stop_id": "g99", "summary_en": "x"})["stop_id"] is None


def test_unknown_stop_asks_for_it_and_stop_endpoint_reroutes(client):
    j = client.post("/api/care", json={"text": "I lost my phone", "uid": "u1", "lang": "en"}).json()
    assert j["needs_stop"] is True and j["stop"] is None and "stop" in j["reply_text"].lower()
    j2 = client.post(f"/api/care/{j['id']}/stop", json={"stop": "g4"}).json()
    assert j2["assigned_to"]["stop"] == "g4" and j2["stop_id"] == "g4"


# ------------------------------------------------------------------ escalation
def test_escalation_on_timeout_and_hooks():
    seen = {"emerg": [], "unack": []}
    care.set_hooks(lambda r: seen["emerg"].append(r["id"]), lambda r: seen["unack"].append(r["id"]))
    t0 = 1_000_000.0
    store.NOW = lambda: t0
    r, *_ = care.open_request("my father fainted", "u1", "en", stop_id="g3")
    first = r["assigned_to"]["id"]
    time.sleep(0.05)
    assert seen["emerg"] == [r["id"]]
    assert care.check_escalations(now=t0 + 60) == []                     # inside 2 minutes
    store.NOW = lambda: t0 + 130
    assert care.check_escalations(now=t0 + 130) == [r["id"]]
    assert r["escalated"] is True and r["assigned_to"]["id"] != first
    time.sleep(0.05)
    assert seen["unack"] == [r["id"]]
    # a normal request has 15 minutes
    n, *_ = care.open_request("I lost my phone", "u2", "en", stop_id="g1")
    assert n["id"] not in care.check_escalations(now=t0 + 130 + 600)
    assert n["id"] in care.check_escalations(now=t0 + 130 + 16 * 60)


def test_ack_stops_escalation():
    t0 = 2_000_000.0
    store.NOW = lambda: t0
    r, *_ = care.open_request("my father fainted", "u1", "en", stop_id="g3")
    r["acknowledged_at"] = t0 + 30
    assert care.check_escalations(now=t0 + 900) == []


def test_policy_from_flag_source():
    assert care.get_policy()["ack_minutes"]["emergency"] == 2
    care.set_policy_source(lambda: json.dumps({"ack_minutes": {"emergency": 1, "urgent": 99999, "normal": "x"}, "language_slack_stops": 3, "bogus": 1}))
    p = care.get_policy()
    assert p["ack_minutes"] == {"emergency": 1, "urgent": 5, "normal": 15} and p["language_slack_stops"] == 3
    care.set_policy_source(lambda: (_ for _ in ()).throw(RuntimeError("flagsmith down")))
    assert care.get_policy()["ack_minutes"]["emergency"] == 2


def test_policy_changes_timeout():
    t0 = 3_000_000.0
    store.NOW = lambda: t0
    care.set_policy_source(lambda: {"ack_minutes": {"emergency": 10}})
    r, *_ = care.open_request("my father fainted", "u1", "en", stop_id="g3")
    assert care.check_escalations(now=t0 + 300) == []
    assert care.check_escalations(now=t0 + 601) == [r["id"]]


def test_nobody_on_duty_then_checkin_assigns():
    for v in store.volunteers():
        store.checkin(v["name"], v["stop"], v["langs"], on_duty=False)
    r, *_ = care.open_request("my father fainted", "u1", "en", stop_id="g3")
    assert r["status"] == "open" and r["assigned_to"] is None
    assert "duty officer" in care.build_reply(r).lower()
    store.checkin("Nila", "g2", ["en"])
    care.check_escalations()
    assert r["status"] == "assigned" and r["assigned_to"]["name"] == "Nila"


# ------------------------------------------------------------------ persistence
def test_persistence_across_restart():
    r, *_ = care.open_request("my father fainted", "u1", "en", stop_id="g3", audio=b"abc", audio_type="audio/webm")
    store.checkin("Arun", "g5", ["te"])
    rid = r["id"]
    store.reload()                                  # what a restart does
    r2 = store.get(rid)
    assert r2 and r2["category"] == "medical" and r2["assigned_to"]["name"] and r2["timeline"][0]["event"] == "created"
    assert store.volunteer("Arun")["simulated"] is False
    assert store.load_audio(rid) == b"abc"
    n, *_ = care.open_request("I lost my phone", "u1", "en", stop_id="g1")
    assert n["id"] != rid and int(n["id"][2:]) == int(rid[2:]) + 1     # ids keep counting


# ------------------------------------------------------------------ API contract
def test_api_flow_contract(client):
    j = client.post("/api/care", json={"text": "my father fainted", "uid": "u1", "lang": "en", "stop": "g3"}).json()
    for k in ("id", "category", "urgency", "stop", "assigned_to", "reply_text", "audio_base64", "status"):
        assert k in j
    assert j["id"].startswith("C-") and j["category"] == "medical" and j["urgency"] == "emergency"
    assert j["stop"] == {"id": "g3", "name": "Forest Path"} and j["status"] == "assigned"
    assert set(j["assigned_to"]) >= {"name", "stop", "distance_stops"} and j["assigned_to"]["distance_stops"] == 0
    assert j["audio_base64"] is None and j["notice"]            # TTS mocked off: a clear notice, not a fake result
    rid, vol = j["id"], j["assigned_to"]["name"]

    mine = client.get("/api/care/mine", params={"uid": "u1"}).json()["requests"]
    assert mine[0]["id"] == rid and "Forest Path" in mine[0]["status_text"] and mine[0]["audio_url"] is None

    a = client.get("/api/care/assigned", params={"volunteer": vol}).json()["requests"]
    assert [x["id"] for x in a] == [rid]
    o = client.get("/api/care/open", params={"volunteer": "Ravi"}).json()
    assert o["requests"][0]["id"] == rid and o["requests"][0]["distance_stops"] == 2 and o["stats"]["open_emergencies"] == 1

    assert client.post(f"/api/care/{rid}/ack", json={"volunteer": vol}).json()["acknowledged_at"]
    assert client.post(f"/api/care/{rid}/onway", json={"volunteer": vol}).json()["status"] == "on_the_way"
    st = client.get("/api/care/mine", params={"uid": "u1"}).json()["requests"][0]["status_text"]
    assert vol in st
    done = client.post(f"/api/care/{rid}/resolve", json={"volunteer": vol, "note": "Family reunited"}).json()
    assert done["status"] == "resolved" and done["resolution_note"] == "Family reunited"
    assert client.post(f"/api/care/{rid}/resolve", json={}).status_code == 409
    s = client.get("/api/care/stats").json()
    assert s["total"] == 1 and s["open"] == 0 and s["open_emergencies"] == 0 and s["by_category"] == {"medical": 1}
    assert s["median_ack_s"] is not None and s["median_resolve_s"] is not None and s["by_stop"] == {"Forest Path": 1}


def test_cannot_reroutes_then_closes(client):
    j = client.post("/api/care", json={"text": "I lost my phone", "uid": "u1", "lang": "en", "stop": "g1"}).json()
    rid, seen = j["id"], {j["assigned_to"]["name"]}
    for _ in range(20):
        r = client.post(f"/api/care/{rid}/cannot", json={"reason": "busy"}).json()
        if r["status"] == "could_not_resolve":
            break
        assert r["assigned_to"]["name"] not in seen
        seen.add(r["assigned_to"]["name"])
    assert r["status"] == "could_not_resolve" and r["escalated"] is True
    assert "counter" in client.get("/api/care/mine", params={"uid": "u1"}).json()["requests"][0]["status_text"].lower()


def test_checkin_api_and_audio_upload(client):
    r = client.post("/api/care/checkin", json={"volunteer": "Arun", "stop": "g5", "languages": ["te", "en"]}).json()
    assert r["volunteer"]["simulated"] is False and any(v["name"] == "Arun" for v in r["roster"])
    assert client.post("/api/care/checkin", json={"volunteer": "X", "stop": "nowhere"}).status_code == 400
    assert client.post("/api/care/nope/ack", json={}).status_code == 404


def test_voice_failure_is_a_clear_message(client):
    res = client.post("/api/care", files={"audio": ("a.webm", b"1234", "audio/webm")}, data={"uid": "u1", "lang": "te"}).json()
    assert res["status"] == "not_created" and res["notice"]


def test_audio_roundtrip_with_stt_mock(client, monkeypatch):
    import sarvam
    monkeypatch.setattr(sarvam, "stt", lambda *a, **k: sarvam.STTResult("naa abbai kanipinchatledu", "te", 5))
    monkeypatch.setattr(sarvam, "tts", lambda text, lang: sarvam.AudioResult(b"RIFFwav", 5))
    res = client.post("/api/care", files={"audio": ("a.webm", b"1234", "audio/webm")}, data={"uid": "u1", "lang": "te", "stop": "g2"}).json()
    assert res["category"] == "lost_person" and res["urgency"] == "emergency" and res["audio_base64"]
    assert client.get(f"/api/care/{res['id']}/audio").content == b"1234"


def test_button_choice_and_duplicate_guard(client):
    j = client.post("/api/care", json={"choice": "medical", "uid": "u1", "lang": "ml", "stop": "g3"}).json()
    assert j["category"] == "medical" and j["urgency"] == "emergency"
    j2 = client.post("/api/care", json={"choice": "medical", "uid": "u1", "lang": "ml", "stop": "g3"}).json()
    assert j2["id"] == j["id"] and j2["notice"] == "duplicate"


def test_from_assistant():
    assert care.from_assistant("what is the wait at forest path", "u1", "en", "g2") is None
    p = care.from_assistant("my mother fainted", "u1", "en", "g2")
    assert p["category"] == "medical" and p["stop"]["id"] == "g2" and p["assigned_to"]["stop_id"] == "g2" and p["reply_text"]
    assert care.from_assistant("naa abbai kanipinchatledu", "u2", "te", None)["needs_stop"] is True


def test_model_cannot_play_down_a_safety_category():
    v = care.validate_model({"category": "lost_person", "urgency": "normal", "stop_id": None, "summary_en": "x", "question": ""})
    assert v["urgency"] == "urgent"
    assert care.validate_model({"category": "lost_item", "urgency": "normal"})["urgency"] == "normal"
