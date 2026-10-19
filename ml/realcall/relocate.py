"""Point restored real-call data at this checkout.

  python -m realcall.relocate            # after: aws s3 sync s3://<bucket>/work/realcall_laptop ml/realcall/work

The ledger and the manifest store absolute paths from the laptop that recorded them (e.g. D:\\...\\realcall\\work\\...).
This rewrites every such path to the current work folder, so ingest, gate and stage find the files. It is idempotent
and only touches paths that contain a `realcall/work` component.
"""
import json
import re

import pandas as pd

from realcall.settings import LEDGER, MANIFESTS, WORK

_MARK = re.compile(r"^.*?[\\/]realcall[\\/]work[\\/]", re.IGNORECASE)


def relocate_path(p):
    """Rewrite one path to the current WORK folder; leave anything else unchanged."""
    if not isinstance(p, str) or not _MARK.match(p):
        return p
    rest = _MARK.sub("", p).replace("\\", "/")
    return str(WORK / rest)


def _fix(obj):
    if isinstance(obj, dict):
        return {k: _fix(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_fix(v) for v in obj]
    return relocate_path(obj)


def main():
    n_led = n_man = 0
    if LEDGER.exists():
        lines = LEDGER.read_text(encoding="utf-8").splitlines()
        out = []
        for line in lines:
            if not line.strip():
                continue
            e = json.loads(line)
            f = _fix(e)
            n_led += f != e
            out.append(json.dumps(f, ensure_ascii=False))
        LEDGER.write_text("\n".join(out) + "\n", encoding="utf-8")
    man = MANIFESTS / "realcall.csv"
    if man.exists():
        m = pd.read_csv(man)
        if "path" in m:
            new = m.path.map(relocate_path)
            n_man = int((new != m.path).sum())
            m["path"] = new
            m.to_csv(man, index=False)
    print(f"relocated to {WORK}: {n_led} ledger events, {n_man} manifest paths")


if __name__ == "__main__":
    main()
