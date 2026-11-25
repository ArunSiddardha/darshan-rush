"""Build the audio test set. Usage: make_set.py [--force]  (needs SARVAM_API_KEY in env; ~47 TTS calls).
Output in voice_tests/audio/<id>/<condition>.{wav,webm}. Audio is gitignored (regenerate with this script)."""
import json, os, subprocess, sys, wave, struct, random
sys.path.insert(0, "/Users/arun/hackathon/festive/repo/app")
import sarvam

ROOT = "/Users/arun/hackathon/festive/repo/voice_tests"
FF = "/opt/homebrew/bin/ffmpeg"
SPEAKERS = ["shubh", "priya", "kavitha"]
PACES = [1.0, 1.3, 0.8]
SR = 16000


def ff(*args):
    subprocess.run([FF, "-y", "-loglevel", "error", *args], check=True)


def make_noise(path, seconds=15):
    """Crowd-like noise: brown noise + pink noise + low murmur (band-passed noise with slow tremolo)."""
    ff("-f", "lavfi", "-i", f"anoisesrc=d={seconds}:c=brown:r={SR}:a=0.6",
       "-f", "lavfi", "-i", f"anoisesrc=d={seconds}:c=pink:r={SR}:a=0.4",
       "-f", "lavfi", "-i", f"anoisesrc=d={seconds}:c=white:r={SR}:a=0.5",
       "-filter_complex", "[2]highpass=f=200,lowpass=f=900,tremolo=f=4:d=0.6[m];[0][1][m]amix=inputs=3:normalize=0,aformat=sample_fmts=s16:channel_layouts=mono",
       "-ar", str(SR), path)


def main():
    force = "--force" in sys.argv
    cases = json.load(open(f"{ROOT}/cases.json"))
    os.makedirs(f"{ROOT}/audio", exist_ok=True)
    noise = f"{ROOT}/audio/_noise.wav"
    if not os.path.exists(noise):
        make_noise(noise)
    meta = {}
    for i, c in enumerate(cases):
        d = f"{ROOT}/audio/{c['id']}"
        os.makedirs(d, exist_ok=True)
        clean = f"{d}/clean.wav"
        sp, pace = SPEAKERS[i % 3], PACES[(i // 3 + i) % 3]
        if c.get("silence"):
            ff("-f", "lavfi", "-i", f"anullsrc=r={SR}:cl=mono", "-t", "2.5", clean)
            sp, pace = "-", 0
        elif force or not os.path.exists(clean):
            import base64, httpx
            body = {"text": c["text"], "target_language_code": sarvam.LANG_CODES[c["lang"]], "model": "bulbul:v3",
                    "speaker": sp, "pace": pace, "speech_sample_rate": 16000}
            r = httpx.post(sarvam.BASE + "/text-to-speech", headers=sarvam._headers(), json=body, timeout=30)
            r.raise_for_status()
            open(clean, "wb").write(base64.b64decode(r.json()["audios"][0]))
        meta[c["id"]] = {"speaker": sp, "pace": pace}
        # field versions
        dur = float(subprocess.check_output(["/opt/homebrew/bin/ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", clean]))
        for name, snr in (("noise10", 10), ("noise5", 5)):
            # scale noise so that signal-to-noise = snr dB, using measured mean volumes
            sv = _mean_db(clean)
            nv = _mean_db(noise)
            gain = sv - snr - nv
            ff("-i", clean, "-stream_loop", "-1", "-i", noise, "-filter_complex",
               f"[1]volume={gain:.2f}dB[n];[0][n]amix=inputs=2:duration=first:normalize=0", "-ar", str(SR), "-ac", "1", f"{d}/{name}.wav")
        ff("-i", clean, "-af", "highpass=f=300,lowpass=f=3400", "-ar", "8000", f"{d}/phone.wav")
        ff("-ss", "0.2", "-i", clean, f"{d}/clipped.wav")
        for cond in ("clean", "noise10", "noise5", "phone", "clipped"):
            ff("-i", f"{d}/{cond}.wav", "-c:a", "libopus", "-b:a", "24k", "-ar", "48000", f"{d}/{cond}.webm")
    json.dump(meta, open(f"{ROOT}/audio/meta.json", "w"), indent=1)
    print("done", len(cases))


def _mean_db(path):
    p = subprocess.run([FF, "-i", path, "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True)
    for line in p.stderr.splitlines():
        if "mean_volume" in line:
            return float(line.split("mean_volume:")[1].split("dB")[0])
    return -30.0


if __name__ == "__main__":
    main()
