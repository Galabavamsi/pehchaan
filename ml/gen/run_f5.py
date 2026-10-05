"""F5-TTS zero-shot cloning.

  default:   F5-TTS v1 Base (SWivid/F5-TTS; code MIT, weights CC-BY-NC-4.0), English
  --hindi:   SPRINGLab/F5-Hindi-24KHz (IIT Madras; CC-BY-4.0; F5 "small" 151M trained on IndicTTS-Hindi +
             IndicVoices-R Hindi), used as our Indic F5 cloner while ai4bharat/IndicF5 is gated.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402


def extra(ap):
    ap.add_argument("--model", default="F5TTS_v1_Base")
    ap.add_argument("--hindi", action="store_true")
    ap.add_argument("--nfe", type=int, default=32)


a = common.args(extra)
jobs = common.load_jobs(a)
if jobs:
    from f5_tts.api import F5TTS
    if a.hindi:
        from huggingface_hub import hf_hub_download
        ck = hf_hub_download("SPRINGLab/F5-Hindi-24KHz", "model_2500000.safetensors")
        vo = hf_hub_download("SPRINGLab/F5-Hindi-24KHz", "vocab.txt")
        tts = F5TTS(model="F5TTS_Small", ckpt_file=ck, vocab_file=vo)
    else:
        tts = F5TTS(model=a.model)

    def fn(j):
        wav, sr, _ = tts.infer(ref_file=j["ref_wav"], ref_text=j.get("ref_text", ""), gen_text=j["text"],
                               seed=int(j.get("seed", 0)), show_info=lambda *x: None, progress=None,
                               remove_silence=False, nfe_step=a.nfe)
        return wav, sr

    common.run(jobs, fn, "f5hi" if a.hindi else "f5")
