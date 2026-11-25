# How a shrine or venue loads its own pack

The assistant never has venue facts in code. Everything it knows about a place lives in one JSON file in this folder, a **knowledge pack**. Swap the file and the same app serves a different shrine, stadium, fair or station.

## Steps

1. Copy `venue_demo.json` (a hill shrine) or `venue_stadium_demo.json` (a small 8-entry example) to `venue_<yourname>.json`.
2. Edit `venue`, `stops` (ids must match the stop ids your route and queue use) and `entries`.
3. Start the app with `VENUE_PACK=venue_<yourname>` (a name in this folder, without `.json`) or `VENUE_PACK=/absolute/path/pack.json`. The default is `venue_demo`.
4. Check it: `cd app && ../.venv/bin/python -c "import kb; print(kb.pack_info()); print(kb.facts_for('where is the toilet','en'))"`.

## An entry

```json
{
  "id": "water_where",
  "topic": "Drinking water",
  "tags": ["water", "facilities"],
  "triggers": ["water", "thirsty", "paani", "నీళ్లు", "தண்ணீர்", "വെള്ളം", "ನೀರು", "पानी"],
  "answer": "Free drinking water is available at all five stops.",
  "where": "all",
  "example_questions": ["Where can I drink water?"],
  "simulated": true
}
```

- `triggers`: words pilgrims say or a speech recogniser writes. Add the native script and the romanised spellings (neellu, neeru). The matcher also tolerates endings and small spelling differences, so you do not need every form.
- `answer`: short, factual, English. State only what is true for your venue. The chat model phrases and translates it, and is told to answer only from these facts. If nothing matches, the assistant says it does not know and points to the information counter.
- `where`: a stop id when the entry belongs to one place, else `all`. Entries for the pilgrim's current stop rank higher.
- Keep `"simulated": true` on any demo pack. Remove it for real data.

The schema is in `pack_schema.json`. No restart tooling is needed beyond setting the env var; the pack is read once per process.
