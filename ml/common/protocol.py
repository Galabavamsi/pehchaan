"""Evaluation protocol (fixed before any fine-tuning result was seen).

Held-out generators: never used for training, calibration or threshold choice.
  seedvc      voice conversion (the real-time clone attack)
  chatterbox  LLM-based zero-shot TTS (also carries a Perth watermark, so keeping it out of training
              prevents the detector from learning the watermark instead of synthesis cues)
  sarvam, openai, deepgram   commercial stock-voice TTS (unseen engines)
Extra held-out generators added after the first runs (so trivially never trained on): Indic Parler-TTS
(stock Indic speakers) and IndicF5 (if its gated weights become downloadable).
Held-out speaker: S02 (all of S02's real and cloned audio is test-only).
Seen team speaker S01: lines 01-08 -> train, 09-10 -> dev, 11-15 -> test (real and clone of a line
always share a split, so comparisons stay content-matched). Free speech (D) and real calls (E) are test.
Public data keeps its own split (FLEURS train/dev/test; ASVspoof19 train/dev/eval); SynRef spoofs inherit
the FLEURS split of the sentence they read.
"""

HELDOUT_GENERATORS = {"seedvc", "chatterbox", "sarvam", "openai", "deepgram",
                      # added later as EXTRA held-out generators (never in any training run):
                      "parler", "indicf5",
                      # MLAAD (published spoof data, test only): Indic TTS systems we never trained on
                      "mlaad_indri", "mlaad_omnivoice", "mlaad_ringg", "mlaad_veena", "mlaad_voxcpm2", "mlaad_voxtral",
                      "mlaad_bark", "mlaad_vits_bn", "mlaad_edgetts", "mlaad_svara"}
HELDOUT_SPEAKERS = {"S02"}
CHANNELS = ["clean", "pstn", "amr", "opus", "replay"]

GEN_FAMILY = {
    "f5": "zero-shot TTS (flow matching)", "f5hi": "zero-shot TTS (flow matching)", "indicf5": "zero-shot TTS (flow matching)",
    "xtts": "zero-shot TTS (GPT + HiFiGAN)", "cosyvoice2": "zero-shot TTS (LLM + flow)", "chatterbox": "zero-shot TTS (LLM + flow)",
    "seedvc": "voice conversion", "mms": "stock TTS (VITS)", "kokoro": "stock TTS (StyleTTS2-like)",
    "sarvam": "commercial TTS", "openai": "commercial TTS", "deepgram": "commercial TTS",
    "parler": "stock TTS (Parler, description-controlled)",
    "mlaad_indri": "MLAAD: Indri TTS", "mlaad_omnivoice": "MLAAD: OmniVoice", "mlaad_ringg": "MLAAD: Ringg Squirrel TTS",
    "mlaad_veena": "MLAAD: Veena", "mlaad_voxcpm2": "MLAAD: VoxCPM2", "mlaad_voxtral": "MLAAD: Voxtral TTS",
    "mlaad_bark": "MLAAD: Bark", "mlaad_vits_bn": "MLAAD: Coqui VITS (bn)", "mlaad_edgetts": "MLAAD: Microsoft Edge TTS",
    "mlaad_svara": "MLAAD: SvaraTTS",
}


def team_split(speaker: str, line_id: str, section: str) -> str:
    if speaker in HELDOUT_SPEAKERS or any(s in str(speaker) for s in HELDOUT_SPEAKERS):
        return "test"
    if section in ("D", "E"):
        return "test"
    import re
    m = re.search(r"(\d+)$", str(line_id))
    if not m:
        return "test"
    n = int(m.group(1))
    if section == "C":  # mother-tongue renditions of E01-E11, or unnumbered segments
        return "train" if n <= 6 else ("dev" if n <= 8 else "test")
    return "train" if n <= 8 else ("dev" if n <= 10 else "test")


def is_heldout(generator: str, speaker: str = "") -> bool:
    return generator in HELDOUT_GENERATORS or (speaker in HELDOUT_SPEAKERS)
