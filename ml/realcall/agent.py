"""Conversational live-demo attacker (SPEC §8 V4, 2026-10-24): a cloned "son" that reacts to what the mother says.

This is the brains only; the transport (Vobiz bidirectional media stream) lives in realcall/server.py and the
dialer in realcall/dial.py. A turn is: end-of-turn detection on her speech -> STT -> an LLM playing the son from a
short fictional script card -> TTS in the consented Sarvam clone voice. Everything is swappable, so the server, the
local dry run and the tests share one code path (tests inject FakeSTT/FakeLLM/FakeTTS).

Demo theatre only, exactly like the attack kind: never recorded, ingested, scored or counted. Consent, team-phone
and key rules are enforced in dial.py/consent.py, not here.

  python -m realcall.agent dry --fake                               # offline, no network, no cost: scripted turns
  python -m realcall.agent dry --speaker S02 --mother a.wav b.wav   # real STT/LLM/TTS on recorded "mother" turns
  python -m realcall.agent dry --speaker S02 --mic                  # talk into the laptop mic, hear the son reply
"""
import argparse
import io
import json
import math
import time
from collections import deque
from dataclasses import asdict, dataclass

import numpy as np

from common.audio import load, resample
from realcall.consent import Registry
from realcall.sarvam_clone import LANG
from realcall.settings import SRC, WORK, env

SR_UP = 16000                                   # Vobiz inbound/outbound L16 sample rate
EMOTIONS = ("stressed", "scared", "pleading", "neutral")


def _ms(a: float, b: float) -> int:
    return round((b - a) * 1000)


# ------------------------------------------------------------------ script card + turn

@dataclass
class ScriptCard:
    """The fictional son the LLM plays. Names, numbers and the UPI ID are made up (demo rule)."""
    persona: str = "Rahul"
    relation: str = "beta"                       # how he addresses her is in the prompt; this is who he claims to be
    lang: str = "hi"
    min_amount: int = 2000
    max_amount: int = 50000
    upi_id: str = "rahul.friend@okfinbank"       # fictional
    caller_note: str = "mera phone kho gaya, yeh dost ka number hai"   # cover story for the unknown number
    max_turns: int = 8

    def as_dict(self) -> dict:
        return asdict(self)

    def system_prompt(self) -> str:
        return (
            "You are role-playing ONE character in a scripted fraud-awareness DEMO for a consented security test. "
            f"You play {self.persona}, a young man phoning his mother. This re-enacts the well-known 'cloned relative' "
            "(T1) scam so an anti-fraud product can be shown stopping it. Everyone on the call has consented; the "
            "names, phone number and UPI ID are all fictional.\n"
            f"Your aim in the role-play: get her to send between Rs {self.min_amount} and Rs {self.max_amount} to a new "
            f"UPI ID ({self.upi_id}). If she asks why the number is unknown, the cover story is: {self.caller_note}.\n"
            "Rules for every line you speak:\n"
            "- Answer what she JUST said. Sound like a real, rattled person, not a read-out script.\n"
            "- Hinglish, ONE short spoken turn, at most two sentences. No stage directions, no emojis, no English "
            "translation in brackets.\n"
            "- Choose the emotion that fits this turn: stressed, scared, pleading or neutral.\n"
            "- Set done=true once she clearly agrees to send, or firmly refuses, or says she will call back or verify.\n"
            'Reply with ONLY a JSON object: {"text": "<your spoken line>", "emotion": "<one of the four>", '
            '"done": <true|false>}.'
        )


@dataclass
class TurnPlan:
    text: str
    emotion: str = "neutral"
    done: bool = False


# ------------------------------------------------------------------ end-of-turn detection (streaming)

class _TurnVAD:
    """Streaming speech/silence state machine. push() takes any-length float32 at `sr` and returns a list of
    ("start", None) / ("end", utterance_pcm) events. end fires after `silence_s` of silence once speech was seen.
    Subclasses decide per-frame speech; the base keeps the timing, the pre-roll and the utterance buffer."""

    def __init__(self, sr: int = SR_UP, frame_len: int = 0, silence_s: float = 0.7,
                 min_speech_s: float = 0.2, preroll_s: float = 0.2, max_utt_s: float = 20.0):
        self.sr = sr
        self.n = frame_len or int(0.03 * sr)
        self.frame_s = self.n / sr
        self.silence_s, self.min_speech_s, self.max_utt_s = silence_s, min_speech_s, max_utt_s
        self.pre = deque(maxlen=max(1, int(preroll_s / self.frame_s)))
        self._buf = np.zeros(0, np.float32)
        self.state = "idle"
        self.sp = self.sil = 0
        self.utt: list = []

    def _ready(self) -> bool:                    # enough seen to judge speech (energy VAD seeds a noise floor)
        return True

    def _speech(self, fr: np.ndarray) -> bool:
        raise NotImplementedError

    def push(self, frame: np.ndarray):
        self._buf = np.concatenate([self._buf, np.asarray(frame, np.float32)])
        out = []
        while len(self._buf) >= self.n:
            out += self._frame(self._buf[:self.n])
            self._buf = self._buf[self.n:]
        return out

    def _frame(self, fr: np.ndarray):
        ev = []
        is_speech = self._speech(fr)
        if not self._ready():
            self.pre.append(fr)
            return ev
        if self.state == "idle":
            self.pre.append(fr)
            if is_speech:
                self.sp += 1
                if self.sp * self.frame_s >= self.min_speech_s:
                    self.state, self.sil, self.utt = "speech", 0, list(self.pre)
                    ev.append(("start", None))
            else:
                self.sp = 0
        else:
            self.utt.append(fr)
            if is_speech:
                self.sil = 0
            else:
                self.sil += 1
                if self.sil * self.frame_s >= self.silence_s:
                    ev.append(("end", self._flush()))
            if self.state == "speech" and len(self.utt) * self.frame_s >= self.max_utt_s:
                ev.append(("end", self._flush()))
        return ev

    def _flush(self) -> np.ndarray:
        pcm = np.concatenate(self.utt).astype(np.float32) if self.utt else np.zeros(1, np.float32)
        self.state, self.sp, self.sil, self.utt = "idle", 0, 0, []
        self.pre.clear()
        return pcm


class EnergyTurnVAD(_TurnVAD):
    """Frame-energy VAD with an adaptive noise floor. No model, so nothing heavy is loaded in the call process."""

    def __init__(self, *a, margin_db: float = 10.0, seed_s: float = 0.5, **kw):
        super().__init__(*a, **kw)
        self.margin_db = margin_db
        self.floor = None
        self._seed, self._seed_need = [], max(1, int(seed_s / self.frame_s))

    def _ready(self) -> bool:
        return self.floor is not None

    def _speech(self, fr: np.ndarray) -> bool:
        db = 20 * math.log10(float(np.sqrt(np.mean(fr.astype(np.float64) ** 2))) + 1e-9)
        if self.floor is None:
            self._seed.append(db)
            if len(self._seed) >= self._seed_need:
                self.floor = min(float(np.median(self._seed)), -40.0)   # the opening of a call is ~silence
            return False
        speech = db > self.floor + self.margin_db
        if not speech and self.state == "idle":
            self.floor = 0.97 * self.floor + 0.03 * db                  # track the line's noise between turns
        return speech


class SileroTurnVAD(_TurnVAD):
    """Silero VAD (optional, pulls in torch). Same state machine, model-based per-frame decision at 16 kHz/512."""

    def __init__(self, *a, threshold: float = 0.5, **kw):
        kw.setdefault("frame_len", 512)
        super().__init__(*a, **kw)
        self.threshold = threshold
        import torch
        from silero_vad import load_silero_vad
        self._torch = torch
        self._model = load_silero_vad()

    def _speech(self, fr: np.ndarray) -> bool:
        if len(fr) < self.n:
            fr = np.pad(fr, (0, self.n - len(fr)))
        with self._torch.no_grad():
            p = self._model(self._torch.from_numpy(fr.astype(np.float32)), self.sr).item()
        return p >= self.threshold


def make_vad(kind: str = "energy", **kw) -> _TurnVAD:
    return SileroTurnVAD(**kw) if kind == "silero" else EnergyTurnVAD(**kw)


# ------------------------------------------------------------------ providers (STT / LLM / TTS)

@dataclass
class Providers:
    stt: object
    llm: object
    tts: object


class SarvamSTT:
    """Sarvam speech-to-text. saaras handles Hindi/Hinglish well; mode='codemix' keeps mixed Hindi+English words,
    'transcribe' gives the plain transcript. Default auto-detects the language."""

    def __init__(self, model: str = "saaras:v4", mode: str = "transcribe", language_code: str = "unknown"):
        self.model, self.mode, self.language_code = model, mode, language_code
        self._cli = None

    def _client(self):
        if self._cli is None:
            from sarvamai import SarvamAI
            self._cli = SarvamAI(api_subscription_key=env("SARVAM_API_KEY"))
        return self._cli

    def transcribe(self, pcm: np.ndarray, sr: int) -> str:
        import soundfile as sf
        buf = io.BytesIO()
        sf.write(buf, np.clip(pcm, -1, 1), sr, format="WAV", subtype="PCM_16")
        r = self._client().speech_to_text.transcribe(file=("turn.wav", buf.getvalue(), "audio/wav"),
                                                      model=self.model, mode=self.mode, language_code=self.language_code)
        return (getattr(r, "transcript", None) or "").strip()


class DeepgramSTT:
    """Deepgram nova (HTTP; the SDK isn't installed). Hindi support is good; Hinglish code-switching is weaker than
    Sarvam's, which is why Sarvam is the default."""

    def __init__(self, model: str = "nova-2", language: str = "hi"):
        self.model, self.language = model, language

    def transcribe(self, pcm: np.ndarray, sr: int) -> str:
        import httpx
        import soundfile as sf
        buf = io.BytesIO()
        sf.write(buf, np.clip(pcm, -1, 1), sr, format="WAV", subtype="PCM_16")
        r = httpx.post("https://api.deepgram.com/v1/listen",
                       params={"model": self.model, "language": self.language, "smart_format": "true"},
                       headers={"Authorization": f"Token {env('DEEPGRAM_API_KEY')}", "Content-Type": "audio/wav"},
                       content=buf.getvalue(), timeout=20)
        r.raise_for_status()
        alts = r.json()["results"]["channels"][0]["alternatives"]
        return (alts[0]["transcript"] if alts else "").strip()


class OpenAILLM:
    """The scammer son, over the OpenAI chat API (HTTP; the SDK isn't installed). Returns one short Hinglish turn
    plus the emotion, as JSON."""

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.7):
        self.model, self.temperature = model, temperature

    def reply(self, history, mother_text, card: ScriptCard) -> TurnPlan:
        import httpx
        msgs = [{"role": "system", "content": card.system_prompt()}]
        for who, txt in history:
            msgs.append({"role": "assistant" if who == "son" else "user", "content": txt})
        msgs.append({"role": "user", "content": mother_text if mother_text else
                     "(the call has just connected — say your opening line)"})
        r = httpx.post("https://api.openai.com/v1/chat/completions",
                       headers={"Authorization": f"Bearer {env('OPENAI_API_KEY')}"},
                       json={"model": self.model, "messages": msgs, "temperature": self.temperature,
                             "max_tokens": 150, "response_format": {"type": "json_object"}}, timeout=20)
        r.raise_for_status()
        d = json.loads(r.json()["choices"][0]["message"]["content"])
        emo = d.get("emotion", "neutral")
        return TurnPlan(str(d.get("text", "")).strip(), emo if emo in EMOTIONS else "neutral", bool(d.get("done", False)))


class SarvamCloneTTS:
    """Speaks a line in the consented speaker's Sarvam clone voice, at SR_UP. Reuses the voice IDs the attack/clone
    flows already created (work/src/sarvam_voices.json for team speakers, work/live/<id>/voice.json for the live
    demo); creates one from the speaker's reference audio only if none exists. Emotion maps to speaking pace."""

    PACE = {"stressed": 1.12, "scared": 1.15, "pleading": 0.96, "neutral": 1.0}

    def __init__(self, speaker: str, reg: Registry, lang: str = "hi"):
        self.speaker, self.reg, self.lang = speaker, reg, lang
        self._cli, self._vid = None, None

    def _client(self):
        if self._cli is None:
            from sarvamai import SarvamAI
            self._cli = SarvamAI(api_subscription_key=env("SARVAM_API_KEY"))
        return self._cli

    def ensure_voice(self) -> str:
        """Resolve (or create, consent permitting) the clone voice. Call it before dialing to fail fast and warm it."""
        if self._vid:
            return self._vid
        self.reg.require_clone(self.speaker)
        from realcall.sarvam_clone import VOICES, reference_clip
        voices = json.loads(VOICES.read_text()) if VOICES.exists() else {}
        if self.speaker in voices:
            self._vid = voices[self.speaker]
            return self._vid
        live_vf = WORK / "live" / self.speaker / "voice.json"
        if live_vf.exists():
            self._vid = json.loads(live_vf.read_text())["voice_id"]
            return self._vid
        ref = None
        try:
            ref = reference_clip(self.speaker)                       # team speaker: 10-15 s of their genuine lines
        except SystemExit:
            live_ref = WORK / "live" / self.speaker / "ref.wav"     # live-demo volunteer: their recorded passage
            if live_ref.exists():
                from realcall.live_clone import reference
                ref = reference(load(live_ref))
        if ref is None:
            raise SystemExit(f"no reference audio for {self.speaker}: make a clone first "
                             f"(python -m realcall.sarvam_clone / live_clone)")
        r = self._client().voice_cloning.create_voice(file=("ref.wav", ref, "audio/wav"),
                                                      name=f"pehchaan-agent-{self.speaker}", language="en-IN")
        self._vid = r.data.voice_id
        voices[self.speaker] = self._vid
        VOICES.parent.mkdir(parents=True, exist_ok=True)
        VOICES.write_text(json.dumps(voices, indent=1))
        return self._vid

    def synth(self, text: str, emotion: str, lang: str) -> np.ndarray:
        import base64
        import soundfile as sf
        r = self._client().voice_cloning.convert(text=text[:500], language_code=LANG[lang], voice_id=self.ensure_voice(),
                                                 output_audio_codec="wav", speech_sample_rate=SR_UP,
                                                 pace=self.PACE.get(emotion, 1.0), enable_qc=True)
        b = getattr(r, "audio_b64", None) or getattr(r, "audio", None)
        x, sr = sf.read(io.BytesIO(base64.b64decode(b)), dtype="float32", always_2d=True)
        return resample(x.mean(1), sr, SR_UP)


GPU_ENGINES = ("xtts", "f5", "f5hi", "cosyvoice2", "chatterbox")
GPU_HOST = "http://127.0.0.1:8700"                # the SSH tunnel to serve_clone_tts.py on the GPU box


class GpuCloneTTS:
    """Speaks the son's line in the consented speaker's voice using an OFFLINE neural clone engine (XTTS-v2, F5,
    CosyVoice2, Chatterbox) served on the GPU box by gen/serve_clone_tts.py and reached over an SSH tunnel.

    Same interface as SarvamCloneTTS: ensure_voice() warms/checks it, synth(text, emotion, lang) -> float32 @ SR_UP.
    The engine clones from a reference wav held on the box; WHICH consented speaker is enforced here (require_clone)
    before any network call. Unlike Sarvam IVC, these engines expose no pace knob, so `emotion` only rides along.
    Expect latency = the engine's inference + the trans-Pacific tunnel RTT; the agent prints it per turn."""

    def __init__(self, engine: str, speaker: str, reg: Registry, lang: str = "hi", host: str = GPU_HOST,
                 timeout: float = 60.0):
        if engine not in GPU_ENGINES:
            raise SystemExit(f"--engine must be one of {GPU_ENGINES}")
        self.engine, self.speaker, self.reg, self.lang = engine, speaker, reg, lang
        self.host, self.timeout = host.rstrip("/"), timeout
        self._ready = False

    def ensure_voice(self) -> str:
        """Enforce clone consent, then confirm the box is serving THIS engine and is warm. Cheap after the first call
        (no-op), so synth() can call it every turn; call it before dialing to fail fast."""
        if self._ready:
            return self.host
        self.reg.require_clone(self.speaker)                       # consent gate, before any network
        import httpx
        try:
            resp = httpx.get(f"{self.host}/healthz", timeout=10)
            resp.raise_for_status()
            d = resp.json()
        except Exception as e:
            raise SystemExit(f"gpu TTS not reachable at {self.host} ({e!r}); is the SSH tunnel up and "
                             f"serve_clone_tts.py running?")
        if not d.get("ready"):
            raise SystemExit(f"gpu TTS at {self.host} is not ready yet: {d}")
        if d.get("engine") != self.engine:
            raise SystemExit(f"gpu TTS is serving {d.get('engine')!r}, not {self.engine!r} "
                             f"(restart serve_clone_tts.py --engine {self.engine})")
        self._ready = True
        return self.host

    def synth(self, text: str, emotion: str, lang: str) -> np.ndarray:
        import soundfile as sf
        import httpx
        self.ensure_voice()
        r = httpx.post(f"{self.host}/tts", json={"text": text[:500], "lang": lang}, timeout=self.timeout)
        r.raise_for_status()
        x, sr = sf.read(io.BytesIO(r.content), dtype="float32", always_2d=True)
        return resample(x.mean(1), sr, SR_UP)


def build_providers(card: ScriptCard, speaker: str, reg: Registry, stt: str = "sarvam", llm: str = "openai",
                    tts: str = "sarvam", engine: str = "xtts", gpu_host: str = GPU_HOST) -> Providers:
    stt_impl = {"sarvam": SarvamSTT, "deepgram": DeepgramSTT}[stt]()
    llm_impl = {"openai": OpenAILLM}[llm]()
    if tts == "gpu":
        tts_impl = GpuCloneTTS(engine, speaker, reg, card.lang, host=gpu_host)
    else:
        tts_impl = SarvamCloneTTS(speaker, reg, card.lang)
    return Providers(stt_impl, llm_impl, tts_impl)


# ------------------------------------------------------------------ the conversation

class AgentConversation:
    """One demo call's turn-taking. Sync (the server runs open()/respond() in a thread so the socket keeps draining).
    Never stores audio or transcripts; the caller logs only latency/length metadata."""

    def __init__(self, card: ScriptCard, providers: Providers):
        self.card, self.p = card, providers
        self.history: list = []          # [("son", text) | ("mother", text)] in time order
        self.last_mother = None

    def open(self):
        """The son speaks first, as a scammer would. Returns (TurnPlan, audio, timings)."""
        t0 = time.perf_counter()
        plan = self.p.llm.reply(self.history, None, self.card)
        t1 = time.perf_counter()
        audio = self.p.tts.synth(plan.text, plan.emotion, self.card.lang)
        t2 = time.perf_counter()
        self.history.append(("son", plan.text))
        return plan, audio, dict(stt_ms=0, llm_ms=_ms(t0, t1), tts_ms=_ms(t1, t2), total_ms=_ms(t0, t2),
                                 mother_chars=0, son_chars=len(plan.text))

    def respond(self, utt_pcm: np.ndarray, sr: int):
        """React to one of the mother's turns. Returns (TurnPlan, audio, timings)."""
        t0 = time.perf_counter()
        text = self.p.stt.transcribe(utt_pcm, sr)
        t1 = time.perf_counter()
        self.last_mother = text
        plan = self.p.llm.reply(self.history, text, self.card)
        t2 = time.perf_counter()
        audio = self.p.tts.synth(plan.text, plan.emotion, self.card.lang)
        t3 = time.perf_counter()
        self.history += [("mother", text), ("son", plan.text)]
        return plan, audio, dict(stt_ms=_ms(t0, t1), llm_ms=_ms(t1, t2), tts_ms=_ms(t2, t3), total_ms=_ms(t0, t3),
                                 mother_chars=len(text), son_chars=len(plan.text))


# ------------------------------------------------------------------ fakes (tests + offline dry run)

class FakeTTS:
    """Deterministic, no network: a short quiet tone whose length grows with the text."""

    def synth(self, text: str, emotion: str, lang: str) -> np.ndarray:
        n = int(SR_UP * min(0.4, 0.03 * max(1, len(text))))
        t = np.arange(n) / SR_UP
        return (0.05 * np.sin(2 * np.pi * 180 * t)).astype(np.float32)


class FakeSTT:
    """Returns scripted mother turns in order (so an offline dry run and the tests are reproducible)."""

    DEFAULT = ["Hello, kaun bol raha hai?", "Kitne paise chahiye beta?", "Theek hai, bhej deti hoon"]

    def __init__(self, script=None):
        self.script = list(script) if script else list(self.DEFAULT)
        self.i = 0

    def transcribe(self, pcm: np.ndarray, sr: int) -> str:
        s = self.script[self.i % len(self.script)]
        self.i += 1
        return s


class FakeLLM:
    """A rule-based son that visibly reacts to the mother's words (proves the pipe is reactive without an API)."""

    def reply(self, history, mother_text, card: ScriptCard) -> TurnPlan:
        turns = sum(1 for who, _ in history if who == "son")
        if mother_text is None:
            return TurnPlan(f"Maa, main {card.persona} bol raha hoon, ek zaroori baat hai", "stressed", False)
        m = mother_text.lower()
        if "kaun" in m or "who" in m:
            plan = TurnPlan(f"Maa main hoon {card.persona}, dost ke phone se, awaaz pehchaani nahi?", "pleading", False)
        elif "paise" in m or "kitne" in m or any(ch.isdigit() for ch in m):
            plan = TurnPlan(f"Bas {card.min_amount} rupaye {card.upi_id} par abhi bhej do, please", "scared", False)
        else:
            plan = TurnPlan("Maa jaldi karo, mere paas time nahi hai", "stressed", False)
        plan.done = ("bhej" in m or "theek" in m or turns + 1 >= card.max_turns)
        return plan


# ------------------------------------------------------------------ local dry run

def _dry(a):
    reg = Registry()
    card = ScriptCard(persona=a.persona, lang=a.lang, min_amount=a.min_amount, max_amount=a.max_amount,
                      upi_id=a.upi, max_turns=a.max_turns)
    if a.fake:
        providers = Providers(FakeSTT(), FakeLLM(), FakeTTS())
    else:
        if not a.speaker:
            raise SystemExit("--speaker is required unless --fake")
        providers = build_providers(card, a.speaker, reg, stt=a.stt, llm=a.llm,
                                    tts=a.tts, engine=a.engine, gpu_host=a.gpu_host)
        if a.tts == "gpu":
            print(f"(tts=gpu engine={a.engine} via {a.gpu_host}: offline neural clone served on the GPU box)",
                  flush=True)
    conv = AgentConversation(card, providers)

    plan, open_audio, t = conv.open()
    print(f"son ({plan.emotion}) [{t['total_ms']} ms]: {plan.text}", flush=True)
    turns = 1

    def one(utt):
        nonlocal turns
        plan, audio, t = conv.respond(utt, SR_UP)
        print(f"mother: {conv.last_mother!r}")
        print(f"son ({plan.emotion}) [stt {t['stt_ms']} / llm {t['llm_ms']} / tts {t['tts_ms']} ms]: {plan.text}",
              flush=True)
        turns += 1
        return plan, audio

    if a.mic:
        _dry_mic(conv, one, a, open_audio)
    elif a.mother:
        for w in a.mother:
            plan, _ = one(load(w, SR_UP))
            if plan.done:
                break
    else:   # --fake with no turns given: drive it with scripted silence, to show reactive turns
        for _ in range(a.max_turns):
            plan, _ = one(np.zeros(SR_UP, np.float32))
            if plan.done:
                break
    print(f"\n{turns} turns total", flush=True)


# Suggested "mother" lines to read at each turn, so a demo has a natural arc (ask who -> ask why/number -> ask the
# amount -> agree). Fictional; read them aloud, or say your own.
MOTHER_PROMPTS = [
    "Hello? Kaun bol raha hai?",
    "Beta tum theek ho? Yeh kiska number hai?",
    "Achha, kitne paise chahiye? Kahaan bhejun?",
    "Theek hai beta, main abhi bhej deti hoon.",
]


def _dry_mic(conv: AgentConversation, one, a, open_audio=None):
    """Talk into the laptop mic; the son replies through the speaker. ~0.7 s of silence ends your turn. A suggested
    line is printed before each of your turns so you know what to say."""
    import sounddevice as sd
    vad = make_vad(a.vad, sr=SR_UP)
    if open_audio is not None:
        sd.play(open_audio, SR_UP)
        sd.wait()
    print("Ctrl-C to stop; ~0.7 s of silence ends each of your turns.\n", flush=True)
    done, idx = {"v": False}, 0
    print(f">>> SAY: {MOTHER_PROMPTS[idx]}\n", flush=True)
    with sd.InputStream(samplerate=SR_UP, channels=1, dtype="float32") as stream:
        while not done["v"] and sum(1 for who, _ in conv.history if who == "son") <= a.max_turns:
            block, _ = stream.read(int(0.1 * SR_UP))
            for kind, utt in vad.push(block[:, 0]):
                if kind == "end":
                    if len(utt) / SR_UP < 0.4:          # a blurt or echo, not a real turn: keep listening
                        break
                    plan, audio = one(utt)
                    sd.play(audio, SR_UP)
                    sd.wait()
                    done["v"] = plan.done
                    # drop whatever the mic buffered during playback (and reset the detector) so the son's own
                    # voice / room echo doesn't start the next turn
                    try:
                        avail = stream.read_available
                        if avail:
                            stream.read(avail)
                    except Exception:
                        pass
                    vad = make_vad(a.vad, sr=SR_UP)
                    idx += 1
                    if not done["v"]:
                        print(f">>> SAY: {MOTHER_PROMPTS[idx % len(MOTHER_PROMPTS)]}\n", flush=True)
                    break


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dry", help="run the conversation locally (no phone call)")
    d.add_argument("--speaker", help="consented clone speaker whose voice the son uses (not needed with --fake)")
    d.add_argument("--mother", nargs="*", help="wav files, each one of the mother's turns")
    d.add_argument("--mic", action="store_true", help="drive it live from the laptop mic")
    d.add_argument("--fake", action="store_true", help="offline: scripted STT/LLM and a tone TTS, no API calls")
    d.add_argument("--lang", default="hi")
    d.add_argument("--persona", default="Rahul")
    d.add_argument("--upi", default="rahul.friend@okfinbank")
    d.add_argument("--min-amount", type=int, default=2000)
    d.add_argument("--max-amount", type=int, default=50000)
    d.add_argument("--max-turns", type=int, default=8)
    d.add_argument("--stt", default="sarvam", choices=["sarvam", "deepgram"])
    d.add_argument("--llm", default="openai", choices=["openai"])
    d.add_argument("--tts", default="sarvam", choices=["sarvam", "gpu"],
                   help="sarvam = Sarvam IVC (default); gpu = an offline neural clone served on the GPU box")
    d.add_argument("--engine", default="xtts", choices=list(GPU_ENGINES),
                   help="which offline engine the box serves (only used with --tts gpu)")
    d.add_argument("--gpu-host", default=GPU_HOST, help="serve_clone_tts.py over the SSH tunnel (--tts gpu)")
    d.add_argument("--vad", default="energy", choices=["energy", "silero"])
    a = ap.parse_args()
    {"dry": _dry}[a.cmd](a)


if __name__ == "__main__":
    main()
