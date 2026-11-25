# Darshan Rush: business case (25 Nov 2026)

Summary and pitch: see pitch_40s.md. Shrines pay about Rs 10 per voice booking (cost about Rs 3.5). Pilgrims never pay; no ads; no data sales. Exchange rate used: about Rs 88 per US dollar (assumption).

## 1. Unit economics (public prices, Sarvam page checked 25 Nov 2026)
Sarvam: speech-to-text Rs 30/hour; text-to-speech Rs 30 per 10,000 chars (Bulbul v3; Rs 15 for v2); translation Rs 20 per 10,000 chars; LLM Sarvam-30B Rs 2.5 in / Rs 10 out per million tokens (105B figures conflict across docs: Rs 4 to Rs 29 in, Rs 16 to Rs 73 out). Always check the live page.

One voice booking (our assumption: 3 turns):
| Item | Amount | Cost |
|---|---|---|
| Speech-to-text, 60 s | 1 minute | Rs 0.50 |
| Text-to-speech, ~600 chars (v3) | 0.06 x Rs 30 | Rs 1.80 (Rs 0.90 on v2; cache cuts it) |
| Translation, ~300 chars | | Rs 0.60 |
| LLM, 3k in / 1k out (30B) | | Rs 0.02 (105B at the highest price: about Rs 0.16) |
| Retries, compute, flag calls | | Rs 0.50 |
| **Total** | | **about Rs 3.5** |

Per 100,000 pilgrims a day, if 15% use voice: 15,000 x Rs 3.5 = Rs 52,500 a day of Sarvam cost (about $600); at Rs 10 that is Rs 1.5 lakh revenue a day, 65% gross margin before fixed costs. Cloud baseline is our guess: small Kubernetes cluster about Rs 30,000 a month plus peak-day burst. Flagsmith: free tier or self-host for a pilot; paid plans $45 to $300 a month, sources disagree; overage $50 per million API calls (evaluate flags server-side to avoid per-pilgrim calls). NudgeBee: no public price found.

## 2. Revenue models (mid = 5,000 pilgrims/day, 15% voice, 90 days: 67,500 bookings; mega = 80,000/day, 60 days: 720,000 bookings; both our assumptions)
| | Licence | Per voice booking + minimum | Managed service |
|---|---|---|---|
| Price | Rs 8L / 50L | Rs 10 each, Rs 1L minimum | Rs 12L / 90L |
| Revenue mid / mega | 8L / 50L | 6.8L / 72L | 12L / 90L |
| Cost mid / mega | 4.1L / 34L | 3.9L / 29L | 6.9L / 49L |
| Margin | 49% / 32% | 42% / 60% | 42% / 46% |
Cost = Sarvam at Rs 3.5 per booking + infra (1.2L mid, 4L mega) + support (0.5L mid, 5L mega); managed adds on-call (3L / 20L). Recommend per booking with minimum.

## 3. Buyers and budgets (sources)
- TTD budget 2026-27 Rs 5,456.26 crore (approved 28 Feb 2026): deccanherald.com/india/andhra-pradesh/ttd-approves-rs-5456-crore-budget-for-202627-upgrades-education-security-and-pilgrim-facilities-3915708. A Rs 10.75 crore command centre was reported, not tied to AI. No vendor found for the 25 Sep 2025 AI command centre.
- Sabarimala: Rs 440 crore (2024-25), onmanorama.com/news/kerala/2025/01/21/sabarimala-hits-record-revenue-80-crore-increase.html; Rs 332.77 crore by 26 Dec 2025 (Lokmat/ThePrint reports). Budget or crowd-spend line not found. TDB said it will use more technology next season.
- Shirdi: Rs 851.97 crore income 2025-26 (newsarenaindia.com/states/shirdi-sai-sansthan-gets-rs-660-cr-donations-in-2025-26/80238). Vaishno Devi: about Rs 683 crore 2023-24 (businesstoday.in, ranking; approximate). RFID yatra card contract values: not found.
- Kumbh 2025: overall Rs 7,000 crore plan (theprint.in/india/ai-chatbot-tethered-drones-to-robotic-buoys-yogi-govts-rs-7000-cr-plan-for-a-digital-mahakumbh/2424628); Sah'AI'yak in 11 languages (PIB, 15 Jan 2025). Technology-only budget not found.
- State boards: Tamil Nadu HR&CE 36,627 temples (policy note 2021-22; the "44,000" figure was not confirmed); Andhra Pradesh 47,152 temples in one table (not endowments only); Karnataka Muzrai count not found; Telangana not searched.
- Footfall: 1,439 million domestic religious trips and Rs 1,34,543 crore revenue in 2022 (Ministry of Tourism data via press); Vaishno Devi 9.5 million in 2023 (press).
- Not searched, unverified: Kashi Vishwanath, Kedarnath, Mansa Devi, GeM contract sizes, DigiYatra, hospital OPD, ration counters, railways.

## 4. Adjacent markets
Karnataka Crowd Control Bill 2025: permission for 5,000+ events, compensation regardless of fault, draft indemnity bond Rs 1 crore, penalties up to 3 years (PRS, barandbench, thenewsminute; committee stage, passage unconfirmed). Queue vendors: Qminder list $389 to $789 a month (conflicting third-party prices); Qmatic Indian reseller about Rs 1.2 lakh per unit (IndiaMART); SBI queue RFPs exist, values not seen. These are small tickets; our edge is rush behaviour in Indian languages, not queue counting.

## 5. Bottom-up market (our estimates)
15 mega x Rs 72L = Rs 10.8 cr; 300 mid x Rs 6.8L = Rs 20.2 cr; ceiling Rs 31 cr. Conservative Rs 0.65 cr, base Rs 3.5 cr, upside Rs 15 cr. Customers: Sabarimala/TDB, TTD, one state-board temple in Karnataka or Tamil Nadu.

## 6. Team, risks, trust
Two founders, 12 months, about Rs 35 lakh (assumption). Risks: procurement cycles, incumbents, reliability liability, religious politics; mitigations in business.md. Pilgrims never pay: trust, and no data sold.
