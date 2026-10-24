"""Make time-limited download links for the gated files run "v5" needs, on the LAPTOP, so the HF token never reaches
the GPU box (as data_prep/fetch_mlaad.py does). Hugging Face answers an authorised request for a large file with a
redirect to a signed CDN link that carries no token and expires after about an hour; the box downloads from those.

  python ml/infra/sign_urls.py --out ml/work/urls_v5.txt
  scp it to ~/work/urls_v5.txt on the box and start infra/retrain_v5.sh within the hour.

Output is an aria2c input file; paths are relative to ~/data on the box:
  iv/hindi/train-000NN-of-00082.parquet      ai4bharat/IndicVoices, the shards in common/protocol.py IV_SHARDS
  mlaad_v5/<lang>/<generator>/<file>.wav     mueller91/MLAAD, MLAAD_PER_SYSTEM clips of every (language, system) in
                                             fetch_mlaad.SYSTEMS, seeded; test-only (registered held-out generators)
"""
import argparse
import os
import random
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

import requests
from dotenv import dotenv_values
from huggingface_hub import HfApi

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.protocol import IV_SHARDS  # noqa: E402
from data_prep.fetch_mlaad import REPO as MLAAD, SYSTEMS  # noqa: E402

MLAAD_PER_SYSTEM = 200


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="ml/work/urls_v5.txt")
    ap.add_argument("--mlaad_per_system", type=int, default=MLAAD_PER_SYSTEM)
    a = ap.parse_args()
    tok = dotenv_values(".env").get("HF_TOKEN")
    api = HfApi(token=tok)
    todo = [(f"datasets/ai4bharat/IndicVoices", f"hindi/train-{k:05d}-of-00082.parquet", f"iv/hindi/train-{k:05d}-of-00082.parquet")
            for k in IV_SHARDS]
    for lang, sysdir, gen in SYSTEMS:
        path = f"fake/{lang}/{sysdir}"
        files = sorted(i.path for i in api.list_repo_tree(MLAAD, repo_type="dataset", path_in_repo=path, recursive=True)
                       if i.path.endswith(".wav"))
        for f in random.Random(f"v5|{lang}|{sysdir}").sample(files, min(a.mlaad_per_system, len(files))):
            todo.append((f"datasets/{MLAAD}", f, f"mlaad_v5/{lang}/{gen}/{os.path.basename(f)}"))

    def sign(item):
        repo, f, out = item
        url = f"https://huggingface.co/{repo}/resolve/main/{urllib.parse.quote(f)}"
        r = requests.head(url, headers={"Authorization": f"Bearer {tok}"}, allow_redirects=False, timeout=60)
        loc = r.headers.get("Location", "")
        if r.status_code not in (301, 302, 307) or not loc.startswith("https://") or "huggingface.co" in loc:
            raise RuntimeError(f"no signed link for {f}: HTTP {r.status_code}")
        return loc, out

    with ThreadPoolExecutor(16) as ex:
        links = list(ex.map(sign, todo))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w") as fh:
        for loc, out in links:
            fh.write(f"{loc}\n  out={out}\n")
    n_iv = sum(o.startswith("iv/") for _, o in links)
    print(f"wrote {len(links)} signed links ({n_iv} IndicVoices shards, {len(links) - n_iv} MLAAD clips) to {a.out}; "
          "they expire in about an hour")


if __name__ == "__main__":
    main()
