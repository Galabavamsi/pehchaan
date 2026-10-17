"""Drive the receiving Android phone over USB (adb): answer our test call, switch on speakerphone, and pull
dialer recordings. Only for the team's own consenting test phones, with USB debugging switched on by the owner.

  python -m realcall.phone status               # connected phone, call state, auto-record setting
  python -m realcall.phone answer               # wait for the next ring, answer, turn on speaker
  python -m realcall.phone pull --device D1     # copy new dialer recordings into work/device_uploads/D1/
"""
import argparse
import os
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from realcall.settings import UPLOADS, log_event

REC_DIRS = ["/sdcard/Recordings/Call", "/sdcard/Call", "/sdcard/Recordings/Call recordings"]
SKIP = {"S02-S01_E_cellular.m4a"}          # the Round 1 call, already in the corpus


def _adb_path() -> str:
    for c in (shutil.which("adb"), os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe")):
        if c and Path(c).exists():
            return c
    raise SystemExit("adb not found (install Android platform-tools)")


def adb(*args, serial=None, timeout=20) -> str:
    cmd = [_adb_path()] + (["-s", serial] if serial else []) + list(args)
    env = {**os.environ, "MSYS_NO_PATHCONV": "1"}
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env, encoding="utf-8", errors="replace")
    return r.stdout


def serials() -> list:
    return [l.split()[0] for l in adb("devices").splitlines()[1:] if l.strip().endswith("device")]


def call_state(serial=None) -> int:
    """0 idle, 1 ringing, 2 off-hook (in a call)."""
    out = adb("shell", "dumpsys", "telephony.registry", serial=serial)
    m = re.findall(r"mCallState=(\d)", out)
    return max(map(int, m)) if m else -1


def _find_button(serial, patterns):
    adb("shell", "uiautomator", "dump", "/sdcard/rc_ui.xml", serial=serial, timeout=30)
    xml = adb("shell", "cat", "/sdcard/rc_ui.xml", serial=serial)
    if "<hierarchy" not in xml:
        return None
    for node in ET.fromstring(xml[xml.index("<hierarchy"):]).iter("node"):
        label = (node.get("text", "") + " " + node.get("content-desc", "")).lower()
        if any(p in label for p in patterns):
            nums = list(map(int, re.findall(r"\d+", node.get("bounds", ""))))
            if len(nums) == 4:
                return node, ((nums[0] + nums[2]) // 2, (nums[1] + nums[3]) // 2)
    return None


def speaker_on(serial=None, tries=6) -> bool:
    """Tap the in-call Speaker button. The label is read from the screen, so no fixed coordinates."""
    for _ in range(tries):
        hit = _find_button(serial, ["speaker"])
        if hit:
            node, (x, y) = hit
            if node.get("checked") == "true" or node.get("selected") == "true":
                return True
            adb("shell", "input", "tap", str(x), str(y), serial=serial)
            time.sleep(0.8)
            hit = _find_button(serial, ["speaker"])
            if hit and (hit[0].get("checked") == "true" or hit[0].get("selected") == "true"):
                return True
            return True   # some dialers don't expose the checked state; the tap went to the Speaker button
        time.sleep(1.0)
    return False


def answer_and_speaker(serial=None, ring_timeout=60, call_id=None) -> dict:
    t0 = time.time()
    while time.time() - t0 < ring_timeout:
        st = call_state(serial)
        if st == 1:
            break
        if st == 2:
            return {"answered": False, "reason": "already in a call"}
        time.sleep(0.5)
    else:
        return {"answered": False, "reason": "no ring"}
    tried = []

    def offhook(wait_s=1.5):
        t = time.time()
        while time.time() - t < wait_s:
            if call_state(serial) == 2:
                return True
            time.sleep(0.25)
        return False

    adb("shell", "input", "keyevent", "KEYCODE_WAKEUP", serial=serial)
    for key in ("KEYCODE_HEADSETHOOK", "KEYCODE_CALL"):        # headset button answers on most dialers
        adb("shell", "input", "keyevent", key, serial=serial)
        tried.append(key)
        if offhook():
            break
    else:                                                     # Samsung: swipe the Answer button
        hit = _find_button(serial, ["answer", "accept"])
        adb("pull", "/sdcard/rc_ui.xml", str(UPLOADS.parent / "phone_ring_ui.xml"), serial=serial)
        if hit:
            x, y = hit[1]
            for dx, dy in ((500, 0), (0, -500), (-500, 0)):
                adb("shell", "input", "swipe", str(x), str(y), str(x + dx), str(y + dy), "300", serial=serial)
                tried.append(f"swipe{dx},{dy}")
                if offhook(1.2):
                    break
            else:
                adb("shell", "input", "tap", str(x), str(y), serial=serial)
                tried.append("tap")
                offhook(1.2)
    answered = call_state(serial) == 2
    spk = speaker_on(serial) if answered else False
    res = {"answered": answered, "speaker": spk, "after_s": round(time.time() - t0, 1), "tried": tried}
    if call_id:
        log_event("phone_auto", call_id=call_id, **res)
    return res


def auto_record_on(serial=None) -> bool:
    return adb("shell", "settings", "get", "system", "record_calls_automatically_on_off", serial=serial).strip() == "1"


def pull(device: str, serial=None) -> list:
    dst = UPLOADS / device
    dst.mkdir(parents=True, exist_ok=True)
    got = []
    for d in REC_DIRS:
        for name in adb("shell", "ls", d, serial=serial).splitlines():
            name = name.strip()
            if not name or name in SKIP or "No such file" in name or (dst / name).exists():
                continue
            adb("pull", f"{d}/{name}", str(dst / name), serial=serial, timeout=120)
            if (dst / name).exists():
                got.append(name)
    return got


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("answer")
    p = sub.add_parser("pull")
    p.add_argument("--device", required=True)
    a = ap.parse_args()
    s = serials()
    if not s:
        raise SystemExit("no phone connected over adb (USB debugging on? 'Allow' tapped?)")
    serial = s[0]
    if a.cmd == "status":
        print("phone:", adb("shell", "getprop", "ro.product.model", serial=serial).strip(), serial)
        print("call state:", {0: "idle", 1: "ringing", 2: "in call"}.get(call_state(serial), "?"))
        print("auto-record calls:", "ON" if auto_record_on(serial) else "OFF")
    elif a.cmd == "answer":
        print(answer_and_speaker(serial))
    else:
        print("pulled:", pull(a.device, serial) or "nothing new")


if __name__ == "__main__":
    main()
