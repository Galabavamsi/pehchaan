"""Assemble deck/slides.src.html -> slides.html, render a vector PDF and per-slide PNG previews.

Placeholders in slides.src.html:
    {{svg:relative/path.svg}}   inline an SVG file (ids namespaced so several SVGs can share the page)
    {{icon:name}}               inline a Phosphor duotone icon (node_modules/@phosphor-icons/core)
    {{include:relative/path}}   inline any text file (HTML fragments)

Usage:
    python deck/build.py              # PDF + PNG previews + raster audit
    python deck/build.py --no-png     # PDF only
    python deck/build.py --scale 2    # sharper PNG previews
"""
import argparse
import pathlib
import re

from playwright.sync_api import sync_playwright
from pypdf import PdfReader

ROOT = pathlib.Path(__file__).parent
SRC = ROOT / "slides.src.html"
HTML = ROOT / "slides.html"
OUT = ROOT / "out"
ICONS = ROOT / "node_modules" / "@phosphor-icons" / "core" / "assets"

# 16:9 slide at 13.333in x 7.5in (PowerPoint widescreen); 1in = 96 CSS px.
WIDTH_PX, HEIGHT_PX = 1280, 720


def clean_svg(svg: str, ns: str) -> str:
    svg = re.sub(r"<\?xml[^>]*\?>", "", svg)
    svg = re.sub(r"<!DOCTYPE[^>]*>", "", svg, flags=re.S)
    svg = re.sub(r"<!--.*?-->", "", svg, flags=re.S)
    for i in sorted(set(re.findall(r'\bid="([^"]+)"', svg)), key=len, reverse=True):
        svg = (svg.replace(f'id="{i}"', f'id="{ns}-{i}"')
                  .replace(f"#{i})", f"#{ns}-{i})")
                  .replace(f'"#{i}"', f'"#{ns}-{i}"'))
    return svg.strip()


def assemble() -> None:
    html = SRC.read_text(encoding="utf-8")
    counter = iter(range(10_000))

    def svg(m: re.Match) -> str:
        path = ROOT / m[1]
        return clean_svg(path.read_text(encoding="utf-8"), f"s{next(counter)}")

    def icon(m: re.Match) -> str:
        name, _, weight = m[1].partition(":")
        weight = weight or "duotone"
        suffix = "" if weight == "regular" else f"-{weight}"
        path = ICONS / weight / f"{name}{suffix}.svg"
        return clean_svg(path.read_text(encoding="utf-8"), f"i{next(counter)}").replace("<svg ", '<svg class="ic" ', 1)

    html = re.sub(r"\{\{svg:([^}]+)\}\}", svg, html)
    html = re.sub(r"\{\{icon:([^}]+)\}\}", icon, html)
    html = re.sub(r"\{\{include:([^}]+)\}\}", lambda m: (ROOT / m[1]).read_text(encoding="utf-8"), html)
    HTML.write_text(html, encoding="utf-8")


def raster_report(pdf_path: pathlib.Path) -> list[str]:
    out = []
    for i, page in enumerate(PdfReader(str(pdf_path)).pages, 1):
        try:
            imgs = [f"{im.name}({im.image.width}x{im.image.height})" for im in page.images]
        except Exception as e:  # noqa: BLE001
            imgs = [f"<err {e}>"]
        out.append(f"  page {i:02d}: {'vector' if not imgs else 'raster: ' + ', '.join(imgs)}")
    return out


def build(pngs: bool, scale: float) -> None:
    assemble()
    OUT.mkdir(exist_ok=True)
    pdf_path = OUT / "deck.pdf"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": WIDTH_PX, "height": HEIGHT_PX}, device_scale_factor=scale)
        page.on("console", lambda m: print("[console]", m.type, m.text) if m.type in ("error", "warning") else None)
        page.on("pageerror", lambda e: print("[pageerror]", e))
        page.goto(HTML.resolve().as_uri())
        page.wait_for_load_state("networkidle")
        page.evaluate("document.fonts.ready")
        page.wait_for_function("window.__ready === true", timeout=60_000)
        page.pdf(
            path=str(pdf_path),
            width=f"{WIDTH_PX}px",
            height=f"{HEIGHT_PX}px",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        if pngs:
            for old in OUT.glob("slide_*.png"):
                old.unlink()
            for i, el in enumerate(page.query_selector_all("section.slide"), 1):
                el.screenshot(path=str(OUT / f"slide_{i:02d}.png"))
        browser.close()
    n = len(PdfReader(str(pdf_path)).pages)
    print(f"wrote {pdf_path} ({n} pages)")
    print("\n".join(raster_report(pdf_path)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-png", action="store_true")
    ap.add_argument("--scale", type=float, default=1.5)
    a = ap.parse_args()
    build(pngs=not a.no_png, scale=a.scale)
