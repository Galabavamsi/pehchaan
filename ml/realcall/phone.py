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


def foreground(serial=None) -> str:
    out = adb("shell", "dumpsys", "window", serial=serial)
    m = re.search(r"mCurrentFocus=Window\{[^ ]+ [^ ]+ ([^}]+)\}", out)
    return m.group(1) if m else ""


def locked(serial=None) -> bool:
    return "isKeyguardShowing=true" in adb("shell", "dumpsys", "window", serial=serial)


def audio_route(serial=None) -> str:
    """Telecom's live audio route, e.g. ActiveSpeakerRoute / ActiveEarpieceRoute / QuiescentEarpieceRoute.
    This is the ground truth for 'is the call on speaker', independent of what the screen shows."""
    out = adb("shell", "dumpsys", "telecom", serial=serial)
    m = re.search(r"CallAudioRouteStateMachine:\s*\n\s*Current state:\s*(\w+)", out)
    if m:
        return m.group(1)
    m = re.search(r"Active communication device: AudioDeviceAttributes: role:output type:(\w+)", adb("shell", "dumpsys", "audio", serial=serial))
    return f"device:{m.group(1)}" if m else "unknown"


def on_speaker(serial=None) -> bool:
    return "speaker" in audio_route(serial).lower()


def bring_call_screen(serial=None) -> bool:
    """If the call runs as a floating window / notification (Xiaomi, Google Phone over another app), open the
    ongoing-call notification so the full call screen with the Speaker button is in front."""
    if "incall" in foreground(serial).lower():
        return True
    adb("shell", "cmd", "statusbar", "expand-notifications", serial=serial)
    time.sleep(0.8)
    hit = _find_button(serial, ["ongoing call", "return to call", "current call", "+91"])
    if hit:
        adb("shell", "input", "tap", *map(str, hit[1]), serial=serial)
        time.sleep(1.0)
    if "incall" not in foreground(serial).lower():
        adb("shell", "cmd", "statusbar", "collapse", serial=serial)
    return "incall" in foreground(serial).lower()


def speaker_on(serial=None, timeout_s=15) -> bool:
    """Turn the call onto speaker and VERIFY it via telecom's audio route; retry until timeout."""
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        if on_speaker(serial):
            return True
        if not bring_call_screen(serial):
            time.sleep(0.5)
        hit = _find_button(serial, ["speaker"])
        if hit:
            node, (x, y) = hit
            adb("shell", "input", "tap", str(x), str(y), serial=serial)
            for _ in range(6):
                time.sleep(0.4)
                if on_speaker(serial):
                    return True
        else:
            time.sleep(0.5)
    return on_speaker(serial)


def _digits(x) -> str:
    return "".join(ch for ch in str(x or "") if ch.isdigit())


def expected_caller() -> str:
    """Last 10 digits of our Vobiz caller ID: the only number this helper will ever answer."""
    from realcall.settings import config
    return _digits(config().get("vobiz_number"))[-10:]


def ringing_caller_matches(serial=None, expected=None) -> tuple:
    """(True, how) only if the ringing number is positively our test caller: from telephony's incoming number,
    or from the number shown on the ringing screen. Unknown or withheld counts as no match."""
    expected = expected or expected_caller()
    if len(expected) < 10:
        return False, "no expected caller configured"
    reg = adb("shell", "dumpsys", "telephony.registry", serial=serial)
    for num in re.findall(r"mCallIncomingNumber=([^\s]*)", reg):
        if _digits(num)[-10:] == expected:
            return True, "telephony"
    adb("shell", "uiautomator", "dump", "/sdcard/rc_ui.xml", serial=serial, timeout=30)
    xml = adb("shell", "cat", "/sdcard/rc_ui.xml", serial=serial)
    for label in re.findall(r'(?:text|content-desc)="([^"]*)"', xml):
        if len(_digits(label)) >= 10 and _digits(label)[-10:] == expected:
            return True, "screen"
    return False, "caller not confirmed"


def _wait_offhook(serial, wait_s=2.0) -> bool:
    t = time.time()
    while time.time() - t < wait_s:
        if call_state(serial) == 2:
            return True
        time.sleep(0.2)
    return False


def answer_and_speaker(serial=None, ring_timeout=60, call_id=None, lock_first=False) -> dict:
    """Wait for the ring, answer, put the call on speaker. Every step is checked against the phone's real state
    (call state from telephony, audio route from telecom); the result records which method worked and when.

    lock_first: switch the screen off before the ring, so the call arrives as the full-screen call UI with Answer
    and Speaker buttons. Needed on the Redmi (MIUI + Google Phone): unlocked, the call is only a banner, answering
    leaves it in the background and the Speaker button is never on screen (verified 23 Oct)."""
    log = {}
    if lock_first:
        if not locked(serial):
            adb("shell", "input", "keyevent", "KEYCODE_SLEEP", serial=serial)
            time.sleep(1.0)
    elif locked(serial):
        adb("shell", "input", "keyevent", "KEYCODE_WAKEUP", serial=serial)
        adb("shell", "wm", "dismiss-keyguard", serial=serial)
        time.sleep(0.8)
    log["locked_at_start"] = locked(serial)
    t0 = time.time()
    while time.time() - t0 < ring_timeout:
        st = call_state(serial)
        if st == 1:
            break
        if st == 2:
            return {"answered": False, "speaker": False, "reason": "already in a call"}
        time.sleep(0.3)
    else:
        return {"answered": False, "speaker": False, "reason": "no ring"}
    log["ring_s"] = round(time.time() - t0, 1)
    adb("shell", "input", "keyevent", "KEYCODE_WAKEUP", serial=serial)
    # Never answer anyone but our own test caller: an unrelated call must not be picked up on speaker.
    ok, how = False, ""
    for _ in range(6):
        ok, how = ringing_caller_matches(serial)
        if ok or call_state(serial) != 1:
            break
        time.sleep(0.5)
    log["caller_check"] = how
    if not ok:
        return {"answered": False, "speaker": False, "reason": "ringing caller is not our test number; not answered", **log}
    method = None
    # 1) the on-screen Answer button (heads-up banner or full-screen), 2) headset key, 3) call key, 4) swipe
    hit = _find_button(serial, ["answer", "accept"])
    if hit:
        adb("shell", "input", "tap", *map(str, hit[1]), serial=serial)
        if _wait_offhook(serial):
            method = "tap_answer"
    for key in ("KEYCODE_HEADSETHOOK", "KEYCODE_CALL"):
        if method:
            break
        adb("shell", "input", "keyevent", key, serial=serial)
        if _wait_offhook(serial):
            method = key
    if not method:
        hit = _find_button(serial, ["answer", "accept", "swipe"])
        if hit:
            x, y = hit[1]
            for dx, dy in ((0, -600), (500, 0), (-500, 0)):
                adb("shell", "input", "swipe", str(x), str(y), str(x + dx), str(y + dy), "350", serial=serial)
                if _wait_offhook(serial, 1.5):
                    method = f"swipe{dx},{dy}"
                    break
    answered = call_state(serial) == 2
    log["answer_method"] = method
    log["answered_s"] = round(time.time() - t0, 1)
    spk = speaker_on(serial) if answered else False
    log["speaker_s"] = round(time.time() - t0, 1)
    log["route"] = audio_route(serial)
    res = {"answered": answered, "speaker": spk, **log}
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
        print("screen locked:", locked(serial), "| foreground:", foreground(serial), "| audio route:", audio_route(serial))
    elif a.cmd == "answer":
        print(answer_and_speaker(serial))
    else:
        print("pulled:", pull(a.device, serial) or "nothing new")


if __name__ == "__main__":
    main()
