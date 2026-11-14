"""Generate the demo voices with ElevenLabs stock voices.

Dana (the retiring expert) and Sam (the successor) are fictional, so the demo uses two stock ElevenLabs voices.
Nobody's real voice is cloned. In production, the expert's clips are their real recordings.

Run from the repo root:
    ELEVENLABS_API_KEY=... python demo/generate_audio.py            # everything
    ELEVENLABS_API_KEY=... python demo/generate_audio.py c_2 sam_q2_backup   # only these ids

Writes:
    backend/seed_audio/c_1.mp3 ... c_7.mp3   (Dana's seed clips, read by backend/seed.py)
    demo/audio/dana_answer_g1.mp3            (live fallback answer)
    demo/audio/sam_q*.mp3                    (Sam's questions)

Override voices with DANA_VOICE_ID / SAM_VOICE_ID. The interviewer uses a third voice, set in the backend.
"""
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from seed_content import CLIPS, DANA_LIVE_ANSWERS, SAM_QUESTIONS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SEED_AUDIO = ROOT / "backend" / "seed_audio"
DEMO_AUDIO = ROOT / "demo" / "audio"

DANA_VOICE = os.getenv("DANA_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # stock "Rachel"
SAM_VOICE = os.getenv("SAM_VOICE_ID", "pNInz6obpgDQGcFmaJgB")    # stock "Adam"
MODEL = os.getenv("ELEVENLABS_TTS_MODEL", "eleven_multilingual_v2")


def load_key() -> str:
    key = os.getenv("ELEVENLABS_API_KEY")
    if not key:
        env = ROOT / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                if line.startswith("ELEVENLABS_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"')
    if not key:
        sys.exit("Set ELEVENLABS_API_KEY (env var or repo-root .env)")
    return key


def speak(key: str, voice: str, text: str, out: Path) -> None:
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
        headers={"xi-api-key": key, "accept": "audio/mpeg"},
        json={"text": text, "model_id": MODEL, "voice_settings": {"stability": 0.45, "similarity_boost": 0.8}},
        timeout=60,
    )
    r.raise_for_status()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(r.content)
    print(f"wrote {out.relative_to(ROOT)}  ({len(r.content) // 1024} KB)")


def main() -> None:
    key = load_key()
    jobs = (
        [(cid, DANA_VOICE, text, SEED_AUDIO / f"{cid}.mp3") for cid, text in CLIPS.items()]
        + [(aid, DANA_VOICE, text, DEMO_AUDIO / f"{aid}.mp3") for aid, text in DANA_LIVE_ANSWERS.items()]
        + [(qid, SAM_VOICE, text, DEMO_AUDIO / f"{qid}.mp3") for qid, text in SAM_QUESTIONS.items()]
    )
    only = set(sys.argv[1:])
    for job_id, voice, text, out in jobs:
        if not only or job_id in only:
            speak(key, voice, text, out)


if __name__ == "__main__":
    main()
