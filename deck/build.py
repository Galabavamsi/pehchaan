"""Render deck/slides.html to a vector PDF and per-page PNG previews.

Usage:
    python deck/build.py            # PDF + PNG previews
    python deck/build.py --no-png   # PDF only
"""
import argparse
import pathlib

from playwright.sync_api import sync_playwright
from pypdf import PdfReader

ROOT = pathlib.Path(__file__).parent
SRC = ROOT / "slides.html"
OUT = ROOT / "out"

# 16:9 slide at 13.333in x 7.5in (PowerPoint widescreen); 1in = 96 CSS px.
WIDTH_PX, HEIGHT_PX = 1280, 720


def build(pngs: bool) -> None:
    OUT.mkdir(exist_ok=True)
    pdf_path = OUT / "deck.pdf"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": WIDTH_PX, "height": HEIGHT_PX})
        page.goto(SRC.resolve().as_uri())
        page.wait_for_load_state("networkidle")
        page.evaluate("document.fonts.ready")
        page.pdf(
            path=str(pdf_path),
            width=f"{WIDTH_PX}px",
            height=f"{HEIGHT_PX}px",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        if pngs:
            slides = page.query_selector_all("section.slide")
            for i, el in enumerate(slides, 1):
                el.screenshot(path=str(OUT / f"slide_{i:02d}.png"))
        browser.close()
    n = len(PdfReader(str(pdf_path)).pages)
    print(f"wrote {pdf_path} ({n} pages)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-png", action="store_true")
    build(pngs=not ap.parse_args().no_png)
