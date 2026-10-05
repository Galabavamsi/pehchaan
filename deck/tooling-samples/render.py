"""Render tooling-samples/<html> to PDF + per-slide PNG and report raster content per page.

Usage: python render.py [samples.html] [--scale 2]
Mirrors deck/build.py (1280x720 px sections, Playwright Chromium) but also waits for a
`window.__ready` flag (set by in-page JS renderers such as Mermaid/rough-notation) and
audits the PDF for embedded raster images so we know which tools stay vector.
"""
import argparse
import pathlib

from playwright.sync_api import sync_playwright
from pypdf import PdfReader

ROOT = pathlib.Path(__file__).parent
W, H = 1280, 720


def raster_report(pdf_path: pathlib.Path) -> list[str]:
    out = []
    for i, page in enumerate(PdfReader(str(pdf_path)).pages, 1):
        imgs = []
        try:
            for img in page.images:
                imgs.append(f"{img.name}({img.image.width}x{img.image.height})")
        except Exception as e:  # noqa: BLE001
            imgs.append(f"<err {e}>")
        out.append(f"page {i:02d}: {'VECTOR-ONLY' if not imgs else 'RASTER: ' + ', '.join(imgs)}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?", default="samples.html")
    ap.add_argument("--scale", type=float, default=1.5)
    a = ap.parse_args()
    src = ROOT / a.src
    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    stem = src.stem
    pdf = out / f"{stem}.pdf"
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=a.scale)
        page.on("console", lambda m: print("[console]", m.type, m.text) if m.type in ("error", "warning") else None)
        page.on("pageerror", lambda e: print("[pageerror]", e))
        page.goto(src.resolve().as_uri())
        page.wait_for_load_state("networkidle")
        page.wait_for_function("window.__ready === undefined || window.__ready === true", timeout=60000)
        page.evaluate("document.fonts.ready")
        page.pdf(path=str(pdf), width=f"{W}px", height=f"{H}px", print_background=True,
                 margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
        for i, el in enumerate(page.query_selector_all("section.slide"), 1):
            el.screenshot(path=str(out / f"{stem}_{i:02d}.png"))
        b.close()
    print(f"wrote {pdf}")
    print("\n".join(raster_report(pdf)))


if __name__ == "__main__":
    main()
