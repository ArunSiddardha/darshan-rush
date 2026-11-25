"""Run the set through the real endpoints. Usage: run_tests.py <conditions comma list> [--base URL] [--ids a,b] [--ext wav|webm]
Needs INCIDENT_TOKEN in env. Writes voice_tests/out/<tag>.json"""
import json, os, sys, time, re, argparse, base64, subprocess
import httpx

ROOT = "/Users/arun/hackathon/festive/repo/voice_tests"
ap = argparse.ArgumentParser()
ap.add_argument("conds"); ap.add_argument("--base", default="http://localhost:8088")
ap.add_argument("--ids", default=""); ap.add_argument("--ext", default="wav"); ap.add_argument("--tag", default="")
ap.add_argument("--kinds", default="directions,yesno,crowd")
a = ap.parse_args()
TOK = os.environ["INCIDENT_TOKEN"]
cases = json.load(open(f"{ROOT}/cases.json"))
if a.ids:
    cases = [c for c in cases if c["id"] in a.ids.split(",")]
cases = [c for c in cases if c["kind"] in a.kinds.split(",")]
H = {"X-Incident-Token": TOK}
cl = httpx.Client(timeout=60)
LANGNAME = {"ml": "ml", "ta": "ta", "te": "te", "kn": "kn", "hi": "hi", "en": "en"}


def script_lang(s):
    for lg, (lo, hi) in {"ml": (0x0D00, 0x0D7F), "ta": (0x0B80, 0x0BFF), "te": (0x0C00, 0x0C7F), "kn": (0x0C80, 0x0CFF), "hi": (0x0900, 0x097F)}.items():
        if any(lo <= ord(ch) <= hi for ch in s):
            return lg
    return "en"


def new_incident():
    cl.post(a.base + "/api/volunteer/reset", headers=H)
    cl.post(a.base + "/api/incident?force=1", headers=H, json={"summary": "Booking pod ran out of memory during a rush", "root_cause": "Map rendering holds large images per request", "proposed_fix": "Switch map to lite and stagger slots", "event_id": "vt-" + str(time.time())})


def wavinfo(b):
    p = "/tmp/_vt_reply.wav"; open(p, "wb").write(b)
    pr = subprocess.run(["/opt/homebrew/bin/ffmpeg", "-i", p, "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True)
    mean = None
    for l in pr.stderr.splitlines():
        if "mean_volume" in l: mean = float(l.split("mean_volume:")[1].split("dB")[0])
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", pr.stderr)
    dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 0
    return round(dur, 2), mean


res = []
for cond in a.conds.split(","):
    for c in cases:
        path = f"{ROOT}/audio/{c['id']}/{cond}.{a.ext}"
        ct = "audio/webm" if a.ext == "webm" else "audio/wav"
        data = open(path, "rb").read()
        r = {"id": c["id"], "lang": c["lang"], "kind": c["kind"], "cond": cond + ("" if a.ext == "wav" else "." + a.ext), "expect": c.get("intent") or c.get("decision") or c.get("count")}
        t0 = time.time()
        try:
            files = {"audio": (f"a.{a.ext}", data, ct)}
            if c["kind"] == "directions":
                form = {"uid": "vt-" + c["id"], "walkin": "1" if c.get("walkin") else "0"}  # language auto-detected, as the browser does for 'auto'
                j = cl.post(a.base + "/api/directions", files=files, data=form).json()
                r.update(transcript=j.get("transcript"), got=j.get("intent"), lang_out=j.get("lang"), reply=j.get("reply_text"),
                         audio=bool(j.get("audio_base64")), notice=j.get("notice"), lat=j.get("latency"))
                r["ok_intent"] = r["got"] == c["intent"]
                r["ok_lang"] = r["lang_out"] == c["lang"]
                if j.get("audio_base64"):
                    r["reply_dur"], r["reply_db"] = wavinfo(base64.b64decode(j["audio_base64"]))
                if c.get("age"):
                    r["ok_age"] = j.get("age") == c["age"]
            elif c["kind"] == "yesno":
                new_incident()
                j = cl.post(a.base + "/api/volunteer/reply", files=files).json()
                r.update(transcript=j.get("transcript"), got=j.get("decision"), lat=j.get("latency"), notice=j.get("notice"))
                r["ok_intent"] = r["got"] == c["decision"]
                if r["got"] != "yes":
                    st = cl.get(a.base + "/api/volunteer/state").json()
                    r["approved"] = st.get("status") == "approved"
                    r["safe"] = not r["approved"] if c["decision"] == "unclear" else True
                elif c["decision"] == "yes": r["safe"] = True
            else:
                j = cl.post(a.base + "/api/volunteer/crowd-report", files=files).json()
                rep = j.get("report") or {}
                r.update(transcript=j.get("transcript"), got=rep.get("count"), gate=rep.get("gate"), applied=rep.get("applied"), lat=j.get("latency"))
                r["ok_intent"] = rep.get("count") == c["count"]
        except Exception as e:
            r["error"] = repr(e)[:200]; r["ok_intent"] = False
        r["wall_ms"] = int((time.time() - t0) * 1000)
        res.append(r)
        print(r["cond"], r["id"], r.get("ok_intent"), repr(r.get("transcript"))[:60], r.get("got"), flush=True)
tag = a.tag or (a.conds.replace(",", "+") + "." + a.ext)
os.makedirs(f"{ROOT}/out", exist_ok=True)
json.dump(res, open(f"{ROOT}/out/{tag}.json", "w"), ensure_ascii=False, indent=1)
print("accuracy", sum(1 for r in res if r.get("ok_intent")), "/", len(res))
