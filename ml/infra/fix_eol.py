"""Normalise text files under ml/ to LF (Python on Windows writes CRLF in text mode, which breaks bash on Linux)."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = {"work", ".venv", "weights", "__pycache__"}
n = 0
for d, dirs, files in os.walk(ROOT):
    dirs[:] = [x for x in dirs if x not in SKIP]
    for f in files:
        if f.endswith((".py", ".sh", ".md", ".txt", ".json", ".yaml", ".csv")):
            p = os.path.join(d, f)
            b = open(p, "rb").read()
            if b"\r\n" in b:
                open(p, "wb").write(b.replace(b"\r\n", b"\n"))
                n += 1
print("fixed", n)
