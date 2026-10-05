"""Drive the live demo (API on :8400, web on :5173) with Playwright and save the
deck screenshots at deviceScaleFactor 2. Phone shots are cropped to the device frame.

    python app/screenshots/shoot.py            # all
    python app/screenshots/shoot.py 01 05 09   # some
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

WEB = "http://127.0.0.1:5173"
OUT = Path(__file__).resolve().parent
ONLY = set(sys.argv[1:])


def want(*ids: str) -> bool:
    return not ONLY or bool(ONLY & set(ids))


def settle(page: Page, ms: int = 750) -> None:
    page.wait_for_timeout(ms)


def shot(page: Page, name: str, testid: str | None = None, full: bool = False) -> None:
    path = OUT / name
    if testid:
        page.get_by_test_id(testid).screenshot(path=str(path), animations="disabled")
    else:
        page.screenshot(path=str(path), full_page=full, animations="disabled")
    print("saved", path.name)


def payer(page: Page):
    return page.get_by_test_id("payer-device")


def relative(page: Page):
    return page.get_by_test_id("relative-device")


def load(page: Page, scen: str) -> None:
    page.get_by_test_id(f"scen-{scen}").click()
    payer(page).get_by_test_id("screen-pay").wait_for()
    settle(page, 900)


def pay_and_claim(page: Page, claim: str, rel: str | None = None) -> None:
    p = payer(page)
    p.get_by_test_id("pay-btn").click()
    p.get_by_test_id("screen-who").wait_for()
    settle(page, 500)
    p.get_by_test_id(f"claim-{claim}").click()
    if claim == "family":
        p.get_by_test_id("screen-family").wait_for()
        p.get_by_test_id(f"rel-{rel}").click()


def main() -> None:
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        ctx = b.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=2)
        page = ctx.new_page()
        page.goto(f"{WEB}/#/demo?scenario=T1&scale=1")
        payer(page).get_by_test_id("screen-pay").wait_for()
        settle(page, 1200)

        # ---------------------------------------------------------------- T1
        if want("01", "02", "03", "04", "05", "06", "09", "10"):
            load(page, "T1")
            if want("01"):
                shot(page, "01_call_and_pay.png", "payer-device")
            p = payer(page)
            p.get_by_test_id("pay-btn").click()
            p.get_by_test_id("screen-who").wait_for()
            settle(page)
            if want("02"):
                shot(page, "02_pause_who.png", "payer-device")
            p.get_by_test_id("claim-family").click()
            p.get_by_test_id("screen-family").wait_for()
            p.get_by_test_id("rel-rel_rahul").click()
            p.get_by_test_id("screen-options").wait_for()
            settle(page)
            if want("03"):
                shot(page, "03_family_options.png", "payer-device")
            p.get_by_test_id("act-family_verify").click()
            p.get_by_test_id("screen-fv-wait").wait_for()
            r = relative(page)
            r.get_by_test_id("rel-notif").wait_for()
            settle(page, 600)
            r.get_by_test_id("rel-notif").click()
            r.get_by_test_id("rel-prompt").wait_for()
            settle(page, 900)
            if want("04"):
                shot(page, "04_relative_prompt.png", "relative-device")
            r.get_by_test_id("rel-no").click()
            p.get_by_test_id("screen-hold").wait_for()
            settle(page, 1500)
            if want("05"):
                shot(page, "05_red_hold.png", "payer-device")
            if want("10"):
                shot(page, "10_split_demo.png")
            if want("09"):
                cpage = ctx.new_page()
                cpage.set_viewport_size({"width": 1440, "height": 900})
                cpage.goto(f"{WEB}/#/console")
                cpage.get_by_test_id("case-detail").wait_for()
                settle(cpage, 1200)
                shot(cpage, "09_console_case.png", full=True)
                cpage.close()
            if want("06"):
                p.get_by_test_id("cancel-report").click()
                p.get_by_test_id("screen-report").wait_for()
                settle(page)
                shot(page, "06_evidence_pack.png", "payer-device")

        # ---------------------------------------------------------------- T2
        if want("07"):
            load(page, "T2")
            pay_and_claim(page, "bank")
            p = payer(page)
            p.get_by_test_id("screen-options").wait_for()
            settle(page, 500)
            p.get_by_test_id("act-bank_registry").click()
            p.get_by_test_id("screen-hold").wait_for()
            settle(page, 1200)
            shot(page, "07_bank_claim.png", "payer-device")

        # ---------------------------------------------------------------- T3
        if want("08"):
            load(page, "T3")
            pay_and_claim(page, "authority")
            payer(page).get_by_test_id("screen-hold").wait_for()
            settle(page, 1200)
            shot(page, "08_authority_fact.png", "payer-device")

        # ---------------------------------------------------------------- Hindi amber
        if want("11"):
            load(page, "T1")
            p = payer(page)
            p.get_by_test_id("lang-toggle").first.click()
            settle(page, 300)
            pay_and_claim(page, "family", "rel_rahul")
            p.get_by_test_id("screen-options").wait_for()
            settle(page)
            shot(page, "11_hindi_amber.png", "payer-device")

        # ---------------------------------------------------------------- L2 genuine
        if want("12"):
            load(page, "L2")
            pay_and_claim(page, "family", "rel_rahul")
            p = payer(page)
            p.get_by_test_id("screen-options").wait_for()
            settle(page, 400)
            p.get_by_test_id("act-family_verify").click()
            r = relative(page)
            r.get_by_test_id("rel-notif").wait_for()
            settle(page, 400)
            r.get_by_test_id("rel-notif").click()
            r.get_by_test_id("rel-yes").click()
            p.get_by_test_id("screen-green").wait_for()
            settle(page, 1200)
            shot(page, "12_green_legit.png", "payer-device")

        b.close()


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"done in {time.time() - t0:.1f}s")
