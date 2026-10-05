"""Telugu clones of S01 (no open TTS we can run clones Telugu while IndicF5 is gated):
a Sarvam te-IN stock voice reads the Whisper transcript of each of S01's Telugu segments (laptop, gen/run_api.py),
then Seed-VC converts that speech into S01's voice. Content roughly matches S01's real Telugu line.
  python gen/make_team_te_vc.py   -> ~/work/jobs/team_seedvc_te.jsonl
"""
import json
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.protocol import team_split  # noqa: E402

H = Path.home()
b = pd.read_csv(H / "work/manifests/team_bona.csv")
c = b[(b.speaker == "S01") & (b.section == "C")]
ref = c.sort_values("dur").iloc[-1]
jobs = []
for line in open(H / "work/gen/api_te/jobs_sarvam_te.jsonl", encoding="utf-8"):
    j = json.loads(line)
    if j["line_id"] == ref.line_id:
        continue
    src = str(H / "work/gen/api_te/sarvam" / os.path.basename(j["out"]))
    jid = "seedvc__S01__" + j["line_id"] + "__sarvamte"
    jobs.append(dict(id=jid, text=j["text"], lang="te", src_wav=src, ref_wav=ref.path, speaker_id="S01", line_id=j["line_id"],
                     split=team_split("S01", j["line_id"], "C"), gender="unknown", seed=len(jobs),
                     out=str(H / "work/gen/team/seedvc" / (jid + ".wav"))))
with open(H / "work/jobs/team_seedvc_te.jsonl", "w", encoding="utf-8") as f:
    for j in jobs:
        f.write(json.dumps(j, ensure_ascii=False) + "\n")
print(len(jobs), "ref", ref.line_id, [j["split"] for j in jobs])
