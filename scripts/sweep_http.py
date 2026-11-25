"""Full HTTP sweep of the running Darshan Rush app: pages, assets, read APIs, pilgrim, care, staff, volunteer, add-ons."""
import json, re, sys, time, urllib.request, urllib.error, uuid
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8088"
res = []
def req(method, path, body=None, form=None, files=None, timeout=60):
    url = BASE + path
    data, headers = None, {}
    if body is not None:
        data, headers = json.dumps(body).encode(), {"Content-Type": "application/json"}
    elif form is not None or files is not None:
        b = "----sweep" + uuid.uuid4().hex
        parts = []
        for k, v in (form or {}).items():
            parts.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (b, k, v)).encode())
        for k, (fn, ct, blob) in (files or {}).items():
            parts.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\nContent-Type: %s\r\n\r\n" % (b, k, fn, ct)).encode() + blob + b"\r\n")
        data = b"".join(parts) + ("--%s--\r\n" % b).encode()
        headers = {"Content-Type": "multipart/form-data; boundary=" + b}
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as f:
            raw = f.read(); code = f.status; ct = f.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        raw = e.read(); code = e.code; ct = e.headers.get("Content-Type", "")
    except Exception as e:
        return 0, None, str(e)
    j = None
    if "json" in ct:
        try: j = json.loads(raw)
        except Exception: pass
    return code, j, raw
def check(name, ok, detail=""):
    res.append((name, bool(ok), detail)); print(("PASS " if ok else "FAIL ") + name + ((" | " + str(detail)[:230]) if (detail and not ok) or (detail and len(sys.argv) > 2) else ""))

# 1 pages and their assets
pages = ["/", "/start", "/volunteer", "/for-temples", "/sponsors", "/judge", "/graph", "/map"]
assets = set()
for p in pages:
    c, _, raw = req("GET", p)
    html = raw.decode("utf8", "ignore") if isinstance(raw, bytes) else ""
    check("page " + p, c == 200 and len(html) > 500, c)
    for m in re.findall(r'(?:src|href)="(/[^"#?]+\.(?:js|css|svg|png|woff2|json))', html):
        assets.add(m)
    for m in re.findall(r'(?:src|href)="((?!https?:|/|#|data:|mailto:)[^"#?]+\.(?:js|css|svg|png))', html):
        assets.add("/static/" + m if not p.startswith("/sponsors") else "/sponsors/" + m)
bad = []
for a in sorted(assets):
    c, _, _ = req("GET", a)
    if c != 200: bad.append((a, c))
check("all %d page assets load" % len(assets), not bad, bad)

# 2 read APIs
for p in ["/healthz", "/api/config", "/api/queue?uid=sw1&lang=en", "/api/map?uid=sw1&lang=te", "/api/flags?uid=sw1&lang=en", "/api/flags/decisions?uid=sw1&lang=en", "/api/slots?uid=sw1", "/api/state", "/api/ui-copy",
          "/api/rush/status", "/api/metrics-lite", "/api/experiment", "/api/rollout", "/api/sponsors/status", "/api/volunteer/state", "/api/care/open", "/api/care/roster", "/api/care/stats", "/api/staff/examples", "/api/staff/help", "/api/care/mine?uid=sw1"]:
    c, j, raw = req("GET", p)
    check("GET " + p, c == 200 and j is not None, (c, str(raw)[:120]))

# 3 sponsors status says all live
c, j, _ = req("GET", "/api/sponsors/status")
check("sponsors status detail", c == 200, json.dumps(j)[:400] if j else "")
print("   sponsors:", json.dumps(j, ensure_ascii=False)[:600])

# 4 booking by button, slots, cancel
u = "sw-" + uuid.uuid4().hex[:6]
c, j, raw = req("POST", "/api/slots/book", {"uid": u, "gate": "g2", "lang": "en"})
check("book slot (button)", c == 200 and j and (j.get("slot") or j.get("window") or j.get("ok")), (c, str(raw)[:200]))
c, j, raw = req("GET", "/api/slots?uid=" + u)
check("slot visible after booking", c == 200 and j and u and json.dumps(j).count("window") > 0, str(raw)[:200])
c, j, raw = req("POST", "/api/event", {"uid": u, "event": "reached_gate", "gate": "g2", "lang": "en"})
check("reached gate event", c == 200, (c, str(raw)[:150]))
c, j, raw = req("POST", "/api/slots/cancel", {"uid": u})
check("cancel slot", c == 200, (c, str(raw)[:150]))
c, j, raw = req("POST", "/api/slots/walkin", {"gate": "g1", "lang": "en"})
check("volunteer walk-in booking", c == 200 and j, (c, str(raw)[:200]))

# 5 complaint -> nearest volunteer -> ack -> on way -> resolve -> pilgrim sees it
u = "sw-" + uuid.uuid4().hex[:6]
req("POST", "/api/care/checkin", {"uid": u, "stop": "g3"})
c, j, raw = req("POST", "/api/care", {"uid": u, "lang": "en", "text": "The toilet near the forest path is very dirty and there is no water", "stop": "g3"})
ok = c == 200 and j and (j.get("request") or j.get("id") or j.get("rid"))
check("complaint raised", ok, (c, str(raw)[:300]))
rid = None
if j:
    r = j.get("request") or j
    rid = r.get("id") or r.get("rid")
    print("   complaint:", json.dumps({k: r.get(k) for k in ("id", "category", "stop", "status", "volunteer", "assigned_to", "volunteer_name", "eta_min", "reply")}, ensure_ascii=False)[:400])
c, j, raw = req("GET", "/api/care/open")
check("complaint on staff list", c == 200 and rid and rid in json.dumps(j), str(raw)[:200])
if rid:
    for step in ("ack", "onway", "resolve"):
        c, j, raw = req("POST", "/api/care/%s/%s" % (rid, step), {"volunteer": "v1", "note": "cleaned"})
        check("complaint " + step, c == 200, (c, str(raw)[:200]))
    c, j, raw = req("GET", "/api/care/mine?uid=%s&lang=en" % u)
    st = (j or {}).get("requests", [{}])[0].get("status")
    check("pilgrim sees complaint resolved", st in ("resolved", "done", "closed"), st)

# 6 distress by voice path (text) raises a request in Telugu
u = "sw-" + uuid.uuid4().hex[:6]
c, j, raw = req("POST", "/api/live/turn", form={"text": "నా అమ్మ పడిపోయింది, సహాయం కావాలి", "uid": u, "session_id": u, "lang": "en", "auto": "1"})
check("distress in Telugu answered in Telugu", c == 200 and j and re.search("[ఀ-౿]", j.get("reply_text") or ""), (c, (j or {}).get("reply_text")))
print("   distress reply:", (j or {}).get("reply_text"), "| intent", (j or {}).get("intent"))
c, j2, raw = req("GET", "/api/care/mine?uid=%s&lang=te" % u)
check("distress created a tracked request", c == 200 and (j2 or {}).get("requests"), str(raw)[:200])

# 7 staff assistant
for q, lang in (("which stop has the longest wait right now", "en"), ("how many open complaints are there", "en"), ("ఇప్పుడు ఎక్కడ ఎక్కువ రద్దీ ఉంది", "te"), ("इस समय सबसे ज़्यादा भीड़ कहाँ है", "hi")):
    c, j, raw = req("POST", "/api/staff/ask", {"text": q, "lang": lang, "staff_id": "v1"})
    rep = (j or {}).get("reply_text") or (j or {}).get("reply") or (j or {}).get("answer")
    check("staff ask [%s] %s" % (lang, q[:30]), c == 200 and rep and "do not have that information" not in rep, (c, str(raw)[:250]))
    print("   ->", str(rep)[:160])

# 8 volunteer crowd report
c, j, raw = req("POST", "/api/volunteer/crowd-report", {"text": "River Crossing, about 900 waiting", "lang": "en"})
check("volunteer crowd report", c == 200 and j, (c, str(raw)[:250]))
print("   crowd report:", json.dumps(j, ensure_ascii=False)[:250])
c, j, raw = req("GET", "/api/volunteer/state")
print("   volunteer state:", json.dumps(j, ensure_ascii=False)[:300])

# 9 add-ons
c, j, raw = req("POST", "/api/site-check", {"url": "http://sabarimala-online-booking.xyz/pay", "lang": "en", "uid": "sw1"})
check("site check (fake site)", c == 200 and j, (c, str(raw)[:250]))
print("   site check:", json.dumps(j, ensure_ascii=False)[:300])
try:
    blob = open("/Users/arun/hackathon/festive/repo/app/static/samples/signboard.png", "rb").read()
    c, j, raw = req("POST", "/api/read-photo", form={"lang": "en", "uid": "sw1"}, files={"image": ("signboard.png", "image/png", blob)}, timeout=90)
    check("read this for me (photo)", c == 200 and j and not j.get("error"), (c, str(raw)[:250]))
    print("   read photo:", json.dumps({k: v for k, v in (j or {}).items() if k != "audio_base64"}, ensure_ascii=False)[:300])
except Exception as e:
    check("read this for me (photo)", False, e)

f = [r for r in res if not r[1]]
print("\nTOTAL %d checks, %d failed" % (len(res), len(f)))
for n, _, d in f: print("  FAILED:", n, "|", str(d)[:300])
