# Judge Q&A: twelve likely questions, honest two-sentence answers

Answer in this voice: plain, "we", no hedging, no overclaiming. If a judge asks something not here, say what we know and what we do not.

**1. Is this real or staged?**
The crowd is a load generator and Lakshmamma and Meera are our team speaking their lines. The Kubernetes out-of-memory kill, NudgeBee's investigation and approval, the Flagsmith flag changes and every Sarvam speech call in the video are real and happened in that take.

**2. Why Kubernetes?**
A memory limit and an OOM kill are a real, observable failure that a shrine's cloud would actually hit on a peak day, and NudgeBee watches Kubernetes events directly. We made the full map deliberately memory hungry so the failure reproduces on demand, but the kill itself is Kubernetes' own decision, not a switch we flip.

**3. Why three sponsor tools? Is one not enough?**
Each does a separate job: Sarvam lets a pilgrim and a volunteer use their own language by voice, NudgeBee sees the failure, explains it and gates the fix behind a human approval, and Flagsmith changes the app's behaviour (light map, staggered slots, voice first for elders) without a redeploy. Take any one away and the story breaks: no voice for Lakshmamma, no cause and no approval, or a code deploy in the middle of a rush.

**4. Will it scale to a real festival?**
In lite mode one small pod on a laptop cluster served about 1,100 requests a second with 0 errors and a 15 ms slowest response, but this is a prototype: one replica, state in a JSON file on a volume. For real traffic we would run several replicas behind a database (Postgres or Redis), evaluate flags locally in the server, and put the map behind a CDN.

**5. How does it make money?**
The shrine pays about Rs 10 per voice booking (with a small minimum), and it costs us about Rs 3.5, mostly Sarvam speech at its published per-use prices (checked 25 Nov 2026, assuming three spoken turns). Pilgrims never pay, there are no ads and no data sales; we would start with one free pilot on one festival day (about Rs 25,000 of our cost).

**6. What exactly is simulated?**
The crowd, the gate wait times, the venue ("Demo Hill Shrine", a made-up knowledge pack), the volunteer roster and the people in the film. The failure, the root cause, the approval, the flag flips, the speech recognition and the spoken replies are real, and every simulated number is labelled SIMULATED on screen.

**7. How is this different from Sabarimala Virtual-Q and the Swami chatbot?**
Virtual-Q books slots and the Swami chatbot answers questions in text on WhatsApp in six languages; both are good, and we do not replace them. We are the layer for the moment everyone arrives at once: voice in your own language, a fair staggered slot, and a system that degrades safely with a volunteer's spoken approval instead of falling over.

**8. How is this different from the other teams' travel and sweet-shop projects?**
Most other projects here serve shoppers or travellers; ours serves a pilgrim and a volunteer in a safety moment, where a slow page can push people into a crush. Our failure is a real OOM kill under load recorded with numbers before and after (3.1 s and a crash, then 15 ms and none), and the fix is approved by a person, by voice, through NudgeBee.

**9. What happens to people's voices?**
The pilgrim's audio is sent to Sarvam only to turn it into text; we keep the text of the conversation, not a recording, except when a pilgrim asks for help, where the clip is kept on our own server so the volunteer can hear it. Nothing is sold or used for ads, and a real deployment would add a retention limit and a consent line before the first tap.

**10. What happens when Sarvam is down or out of credits?**
The app switches to the second key, and if that also fails the pilgrim sees "Voice unavailable, type instead" and can still type, while common questions are answered by our own rules from the venue pack without any model call. Repeated spoken replies come from a cache, so the most frequent sentences keep playing even with no Sarvam access.

**11. Did you use AI to build this?**
Yes: Claude Code agents wrote most of the code, scripts and documents, directed and reviewed by our team, who chose the idea, ran the tests and recorded the video. Inside the product, Sarvam is the speech and language AI and NudgeBee's agent does the investigation; Flagsmith is plain feature flags, no AI.

**12. What stops the assistant from making things up, like a wrong gate or a fake fee?**
Answers come from rules and the venue's own knowledge pack first; the language model is used only when the rules find nothing, and any number in its reply must appear in the facts or the question, otherwise the app says "I do not have that". It never tells anyone to pay, it warns about touts, and the rush switch can only be approved through NudgeBee, never by the chatbot.
