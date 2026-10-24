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


# 2026-10-24 (on site). Written before any of the clips below existed, but AFTER we had seen every model miss the
# Sarvam IVC clones, so any result that depends on this change must say so. A jury member confirmed that audio
# from paid APIs may be used for training. New TRAINING generators, split by voice PERSON (one person is in one
# split across every model and style) and by the FLEURS split of the sentence read:
#   sarvam_v3t   Sarvam Bulbul v3 stock voices          sarvam_v4f  Sarvam Bulbul v4 Flash stock voices
#   openai_t     OpenAI gpt-4o-mini-tts stock voices    deepgram_t  Deepgram Aura-2 stock voices (English)
#   sarvam_ivct  Sarvam instant voice clones of S01 only (consented); train split
# Unchanged: every clip made before today keeps its split, so the held-out "sarvam", "openai", "deepgram" and
# "sarvam_ivc" clips stay test-only; S02 stays held out; Gemini TTS stays a never-trained engine. The test persons
# below include every voice behind the old held-out commercial clips, so those clips stay unseen voices.
# A model trained on these generators reports Sarvam/OpenAI/Deepgram as "seen engine, unseen voices" and
# Sarvam IVC only on S02 ("seen engine, unseen speaker").
# Same day, before training: two candidates, neither replacing model A (ours_v3_rc) unless it beats A on the same
# fixed dev set (old corpus dev rows + real-call dev rows), test reported as it lands:
#   ours_a2      stock voices only (source api2); Sarvam IVC stays a never-trained cloner for it
#   ours_a2_ivc  stock voices + the S01 Sarvam clones (source api2_ivc); its Sarvam IVC result is "seen generator,
#                unseen speaker (S02)", never "generalises to an unseen cloner"
# Varun's decision, same day: Sarvam IVC ENTERS TRAINING on 2026-10-24, AFTER its 0/12 test result on real calls.
# Every Sarvam IVC number for a retrained model is labelled "seen cloner, unseen speaker (S02)"; the 0/12 of the
# older models (v1, A) stays as reported. ours_a2_ivc is trained first; ours_a2 is the control without it.
API2_GENERATORS = {"sarvam_v3t", "sarvam_v4f", "openai_t", "deepgram_t", "sarvam_ivct"}
API2_PERSONS = {
    "sarvam": {"test": {"shubh", "rahul", "amit", "rohan", "ritu", "priya", "kavya", "neha", "simran", "vijay",
                        "kavitha", "roopa"},
               "dev": {"aditya", "ishita", "kabir", "tanya", "mani", "chaitra", "bhavik", "sanchita"}},
    "openai": {"test": {"marin", "nova", "onyx"}, "dev": {"cedar", "shimmer"}},
    "deepgram": {"test": {"thalia", "andromeda", "helena", "apollo", "arcas", "aries", "asteria", "orion", "luna", "zeus"},
                 "dev": {"athena", "hermes", "iris", "juno"}},
}


def api2_split(generator: str, voice: str) -> str:
    """Split of a 2026-10-24 paid-API clip: by the voice's person (v4 Flash ids are person_lang_style)."""
    if generator == "sarvam_ivct":
        return "train"
    family = generator.split("_")[0]
    person = voice.replace("aura-2-", "").split("_")[0].split("-")[0]
    rule = API2_PERSONS[family]
    return "test" if person in rule["test"] else ("dev" if person in rule["dev"] else "train")


def is_heldout(generator: str, speaker: str = "") -> bool:
    return generator in HELDOUT_GENERATORS or (speaker in HELDOUT_SPEAKERS)


# 2026-10-24 (on site, evening): generalisation run "v5". Written before any IndicVoices clip was downloaded or
# cloned, but AFTER we had seen every model (v1, A, A2, A2-ivc) miss S02's Sarvam clones, and NII separate them on
# clean audio (AUC 1.00) but not on real calls. So every v5 result is reported as a follow-up to those results, never
# as a blind test. Rule change of the same day (CLAUDE.md): voices of an open dataset whose licence allows derivative
# use may be cloned with open-source cloners for detector research, declared in DATA_CARD.md and the deck.
# Data (source tags "iv" for real speech, "iv_clone" for its clones):
#   ai4bharat/IndicVoices (CC-BY-4.0), config hindi, train shards IV_SHARDS (fixed before download): raw field
#   recordings at 16 kHz. NOT IndicVoices-R: its audio went through VoiceFixer, which re-synthesises speech with a
#   neural vocoder, so as "bona fide" it would teach the detector that vocoder artefacts are real.
#   Per speaker, seeded: one reference utterance (6-15 s; its transcript is the reference text) and up to 3 target
#   utterances (3-12 s). Each target is a bona fide row; XTTS-v2 and F5-Hindi each read the target's transcript in
#   that speaker's voice from the reference, so every clone has a real twin of the same speaker and content.
#   Clones outside 0.5-2x their twin's duration are dropped and counted. Up to IV_MAX_SPEAKERS speakers with at least
#   4 usable utterances, lowest hash first.
#   Split by PERSON with iv_split (salted SHA-1): 70 train / 10 dev / 20 test; a speaker's real and cloned clips
#   always share it. xtts and f5hi stay seen generators, so iv test rows measure "seen cloner, unseen speaker".
#   Sarvam IVC, Chatterbox, Seed-VC, MLAAD and every other held-out generator stay never-trained. IndicF5 is not used
#   on dataset voices: its terms allow cloning only with the speaker's permission.
# Candidates: model A's recipe (aug v3, real-call rows at 0.25 of each class, 6 x 600 steps, bs 16, seed 0, the
# existing balanced sampling). Sarvam IVC is never trained, so S01's and S02's Sarvam clones are both "unseen cloner";
# S02 stays an unseen speaker.
#   ours_n1   NII mms-300m-anti-deepfake init (CC-BY-NC-SA-4.0, research and education only; the fine-tuned weights
#             inherit that licence) + the ours_a2 data (old corpus + paid-API stock voices)   -> backbone effect
#   ours_a3   model A's init (XLS-R + AASIST, LA) + the ours_a2 data + iv/iv_clone             -> many-speaker effect
#   ours_n3   NII init + the ours_a2 data + iv/iv_clone                                        -> both
# Promotion as for the api2 candidates: a candidate replaces model A only if it beats A on the same fixed dev set
# (scores_v4 dev_sim + dev_rc). Test results are reported whatever they show: the pre-registered real-call test, the
# clean/AMR bench (S01/S02 genuine vs every cloner, Sarvam IVC included), iv test speakers, the paid-API unseen
# voices and the simulated test sample. NII-initialised models are scored by NII's own protocol (whole clip up to
# 16 s, layer-normed), as the served NII is.
# Same evening, before launch, after access to the gated sets came through: a larger MLAAD test set, 200 clips per
# (language, system) of data_prep/fetch_mlaad.SYSTEMS (seeded), clean and through the AMR channel, scored by every
# model. Every one of those generators is registered held-out above, so they stay never-trained. Downloads use signed
# links made on the laptop (infra/sign_urls.py): the HF token never reaches the box.
IV_SHARDS = list(range(0, 82, 8))
IV_SALT = "pehchaan-iv-v5"
IV_MAX_SPEAKERS = 600
IV_GENERATORS = ("xtts", "f5hi")


def iv_bucket(speaker_id: str) -> int:
    import hashlib
    return int(hashlib.sha1(f"{IV_SALT}:{speaker_id}".encode()).hexdigest()[:8], 16) % 100


def iv_split(speaker_id: str) -> str:
    b = iv_bucket(speaker_id)
    return "train" if b < 70 else ("dev" if b < 80 else "test")
