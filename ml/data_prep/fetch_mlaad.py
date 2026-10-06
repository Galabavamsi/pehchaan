"""Download a small, fixed Indic-language subset of MLAAD (mueller91/MLAAD, CC BY-NC 4.0, published spoof data)
on the LAPTOP (the HF token never leaves it) and write a job file so build_corpus.py adds the clips as TEST-only
spoofs from generators the detector never saw. No bona fide audio comes from MLAAD (FLEURS supplies it).

  python ml/data_prep/fetch_mlaad.py --per_system 20 --out ml/work/mlaad
Then copy ml/work/mlaad/ to ~/work/gen/mlaad/ on the box, and mlaad_indic.jsonl to ~/work/jobs/.
"""
import argparse
import json
import os
import random

from dotenv import dotenv_values
from huggingface_hub import HfApi, hf_hub_download

# (lang, MLAAD system folder, our generator name). XTTS-v2 is left out on purpose (architecture seen in training).
SYSTEMS = [
    ("hi", "IndicF5", "indicf5"), ("ta", "IndicF5", "indicf5"), ("bn", "IndicF5", "indicf5"), ("mr", "IndicF5", "indicf5"),
    ("hi", "Indri-TTS-0.1", "mlaad_indri"), ("hi", "OmniVoice", "mlaad_omnivoice"), ("hi", "Ringg Squirrel TTS v1.0", "mlaad_ringg"),
    ("hi", "Veena", "mlaad_veena"), ("hi", "VoxCPM2", "mlaad_voxcpm2"), ("hi", "Voxtral", "mlaad_voxtral"),
    ("hi", "tts_models_multilingual_multi-dataset_bark", "mlaad_bark"), ("bn", "tts_models_bn_custom_vits-female", "mlaad_vits_bn"),
    ("kn", "Edge-TTS", "mlaad_edgetts"), ("ml", "Edge-TTS", "mlaad_edgetts"), ("kn", "SvaraTTS v1", "mlaad_svara"),
]
REPO = "mueller91/MLAAD"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per_system", type=int, default=20)
    ap.add_argument("--out", default="ml/work/mlaad")
    ap.add_argument("--box_root", default="/home/ubuntu/work/gen/mlaad")
    a = ap.parse_args()
    tok = dotenv_values(".env").get("HF_TOKEN")
    api = HfApi(token=tok)
    jobs = []
    for lang, sysdir, gen in SYSTEMS:
        path = f"fake/{lang}/{sysdir}"
        files = sorted(i.path for i in api.list_repo_tree(REPO, repo_type="dataset", path_in_repo=path, recursive=True)
                       if i.path.endswith(".wav"))
        pick = random.Random(f"{lang}|{sysdir}").sample(files, min(a.per_system, len(files)))
        ok = 0
        for f in pick:
            try:
                local = hf_hub_download(REPO, f, repo_type="dataset", token=tok, local_dir=a.out)
            except Exception as e:  # noqa: BLE001
                print("fail", f, type(e).__name__)
                continue
            rel = os.path.relpath(local, a.out).replace(os.sep, "/")
            uid = "mlaad__" + rel.replace("fake/", "").replace("/", "__").replace(" ", "_").rsplit(".", 1)[0]
            jobs.append(dict(id=uid, engine=gen, lang=lang, split="test", voice=f"mlaad_{sysdir}", speaker_id=f"mlaad_{gen}_{lang}",
                             mlaad_system=sysdir, out=f"{a.box_root}/{rel}", text="", gender=""))
            ok += 1
        print(lang, sysdir, gen, "files", len(files), "downloaded", ok, flush=True)
    with open(os.path.join(a.out, "mlaad_indic.jsonl"), "w", encoding="utf-8", newline="\n") as fh:
        for j in jobs:
            fh.write(json.dumps(j, ensure_ascii=False) + "\n")
    print("jobs", len(jobs))


if __name__ == "__main__":
    main()
