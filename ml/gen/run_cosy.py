"""CosyVoice2-0.5B (Apache-2.0). Zero-shot cloning. No Hindi support, so it is used for English lines."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common  # noqa: E402

REPO = os.path.expanduser("~/repos/CosyVoice")
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "third_party/Matcha-TTS"))

a = common.args(lambda ap: ap.add_argument("--model_dir", default=os.path.expanduser("~/weights/CosyVoice2-0.5B")))
jobs = common.load_jobs(a)
if jobs:
    import torch
    if not os.path.exists(os.path.join(a.model_dir, "cosyvoice2.yaml")):
        from huggingface_hub import snapshot_download
        snapshot_download("FunAudioLLM/CosyVoice2-0.5B", local_dir=a.model_dir)
    from cosyvoice.cli.cosyvoice import AutoModel
    cv = AutoModel(model_dir=a.model_dir)

    def fn(j):
        torch.manual_seed(int(j.get("seed", 0)))
        outs = [o["tts_speech"] for o in cv.inference_zero_shot(j["text"], j.get("ref_text", ""), j["ref_wav"], stream=False)]
        return torch.cat(outs, dim=-1).squeeze(0).cpu().numpy(), cv.sample_rate

    common.run(jobs, fn, "cosyvoice2")
