"""Meta MMS-TTS (VITS; facebook/mms-tts-<iso>; CC-BY-NC-4.0). Fixed stock voice per language, no cloning.
Used as (a) a generic Indic synthetic-speech class and (b) synthetic source speech for voice conversion."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

a = common.args()
jobs = common.load_jobs(a)
ISO = {"hi": "hin", "te": "tel", "ta": "tam", "en": "eng", "mr": "mar", "bn": "ben", "kn": "kan", "ml": "mal", "gu": "guj"}
if jobs:
    import torch
    from transformers import AutoTokenizer, VitsModel
    cache = {}

    def get(lang):
        if lang not in cache:
            rid = f"facebook/mms-tts-{ISO[lang]}"
            cache[lang] = (VitsModel.from_pretrained(rid).to("cuda").eval(), AutoTokenizer.from_pretrained(rid))
        return cache[lang]

    def fn(j):
        m, tok = get(j["lang"])
        torch.manual_seed(int(j.get("seed", 0)))
        inp = tok(j["text"], return_tensors="pt").to("cuda")
        with torch.no_grad():
            w = m(**inp).waveform[0].float().cpu().numpy()
        return w, m.config.sampling_rate

    common.run(jobs, fn, "mms")
