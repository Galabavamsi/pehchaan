"""AI4Bharat Indic Parler-TTS (Apache-2.0). Named stock speakers (description-controlled), no cloning."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

a = common.args(lambda ap: ap.add_argument("--repo", default="ai4bharat/indic-parler-tts"))
jobs = common.load_jobs(a)
if jobs:
    import torch
    from parler_tts import ParlerTTSForConditionalGeneration
    from transformers import AutoTokenizer
    model = ParlerTTSForConditionalGeneration.from_pretrained(a.repo).to("cuda").eval()
    tok = AutoTokenizer.from_pretrained(a.repo)
    dtok = AutoTokenizer.from_pretrained(model.config.text_encoder._name_or_path)

    def fn(j):
        torch.manual_seed(int(j.get("seed", 0)))
        d = dtok(j["description"], return_tensors="pt").to("cuda")
        p = tok(j["text"], return_tensors="pt").to("cuda")
        with torch.no_grad():
            g = model.generate(input_ids=d.input_ids, attention_mask=d.attention_mask,
                               prompt_input_ids=p.input_ids, prompt_attention_mask=p.attention_mask)
        return g.cpu().float().numpy().squeeze(), model.config.sampling_rate

    common.run(jobs, fn, "parler")
