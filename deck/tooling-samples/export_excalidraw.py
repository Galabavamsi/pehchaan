"""Export svg/pipeline.excalidraw -> svg/excalidraw.svg using @excalidraw/utils exportToSvg in headless Chromium.

ES modules do not load from file:// in Chromium, so we serve tooling-samples/ over a throwaway localhost
http.server. Fully offline: fonts (Excalifont etc.) ship inside node_modules/@excalidraw/utils/dist/prod/assets.
"""
import functools
import http.server
import pathlib
import threading

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).parent
Handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
http.server.SimpleHTTPRequestHandler.log_message = lambda *a, **k: None
# Windows registry often maps .js to text/plain -> Chromium refuses ES modules; force correct MIME types.
http.server.SimpleHTTPRequestHandler.extensions_map.update({".js": "text/javascript", ".mjs": "text/javascript", ".wasm": "application/wasm", ".ttf": "font/ttf", ".woff2": "font/woff2"})
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_address[1]}"

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page()
    page.on("console", lambda m: print("[console]", m.type, m.text[:300]))
    page.on("pageerror", lambda e: print("[pageerror]", e))
    page.goto(f"{base}/svg/")  # any same-origin page
    svg = page.evaluate(
        """async (base) => {
          window.EXCALIDRAW_ASSET_PATH = base + '/node_modules/@excalidraw/utils/dist/prod/';
          const { exportToSvg } = await import(base + '/node_modules/@excalidraw/utils/dist/prod/index.js');
          const scene = await (await fetch(base + '/svg/pipeline.excalidraw')).json();
          const el = await exportToSvg({ data: { elements: scene.elements, appState: { ...scene.appState, exportEmbedScene: false }, files: null },
                                        config: { padding: 12 } });  // 0.1.x API: {data, config}
          return el.outerHTML;
        }""",
        base,
    )
    (ROOT / "svg" / "excalidraw.svg").write_text(svg, encoding="utf-8")
    print("excalidraw.svg", len(svg), "bytes")
    b.close()
srv.shutdown()
