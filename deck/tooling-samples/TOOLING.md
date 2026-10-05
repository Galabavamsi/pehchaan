# RAKSHAM deck: tooling research notes

Tested 2026-10-05 on Windows 11, Git Bash, Node 24.19, Python 3.12.4, Go 1.25.6, Playwright-Python 1.59 (Chromium).
Everything here lives in `deck/tooling-samples/`. Nothing in `deck/` or `deck/build.py` was changed.

- Rebuild every sample: `cd deck/tooling-samples && npm run all` (runs D2, then the SVG generators, then inlines everything into `samples.html`, then renders the PDF and PNGs).
- Output: `out/samples.pdf` (14 pages) and `out/samples_NN.png`. `render.py` also prints a **raster audit**: the embedded images on each PDF page, so you can see whether a page stayed vector.
- Before submitting, run the deck PDF through `render.py`'s `raster_report()` (or copy it into build.py later) to confirm the slides stay vector.

---

## 1. Recommended toolkit (one per category)

| Category | Pick | Why | Runner-up |
|---|---|---|---|
| System / architecture diagram | **ELK.js + rough.js, rendered by our own `elk_rough.mjs`** | It is the most distinctive option and stays fully vector. Labels use the deck's own fonts (inline SVG, so it uses the page's `@font-face`). One layout gives two skins: sketch for the pitch slides and crisp (`roughness: 0`) for the architecture pages. Compound nodes show the data boundaries clearly ("raw audio stays here" / "features + scores only"). Samples: `samples_04.png`, `samples_05.png`. | **D2 (ELK)** for the secondary diagrams: sequence diagram, AWS deployment view, quick variants. It is text-first, very fast to iterate, embeds fonts, and has `--sketch`. Samples: `_02`, `_03`, `_14`. Also: **Excalidraw** (the `.excalidraw` scene is generated from the same ELK layout) if someone wants to hand-tweak on excalidraw.com. It has the best hand-drawn charm. Sample: `_06`. |
| Hand-drawn accents | **rough-notation** (highlight, underline, box, circle, bracket on headline words) + **perfect-freehand** (brush swooshes and arrows as filled SVG paths) | Both are vector in the PDF and need very little code. Sample: `samples_01.png`. | Excalifont (OFL), used sparingly for one handwritten aside per slide. |
| Charts | **Observable Plot** (Node + jsdom → static SVG) | It is short to write and inherits the deck fonts when inlined. The confusion matrix, DET curve and bars all look good. | **Vega-Lite via `vl-convert-python`** (offline, Python only). **matplotlib** with `svg.fonttype='none'` for plots that come straight from eval notebooks. **ECharts SSR** is good for the funnel. Sample: `_10`. |
| Icons | **Phosphor** (MIT). The duotone weight in the accent colour is more distinctive than plain line icons. | | **Lucide** (ISC) for neutral line icons. Sample: `_11`. |
| Illustrations (optional) | **Open Peeps** (CC0, hand-drawn people). It suits the sketch aesthetic. | | Humaaans (CC0), unDraw (free, no attribution) |
| AWS service marks | **Official AWS Architecture Icons package** (local SVGs referenced from D2 `icon:` or inlined) | They are allowed in presentations. Do not recolour or modify them. | icons.terrastruct.com works with D2 but may lag the official release |
| Slide framework | **Keep raw HTML/CSS → Playwright** | Full CSS control. Every tool above drops in as inline SVG. Vector output is proven. | **pptxgenjs** if an editable PPTX copy is needed (tested; PowerPoint renders the SVG) |

## 2. Install commands that worked

```bash
cd deck/tooling-samples
npm init -y
npm install roughjs rough-notation perfect-freehand elkjs mermaid @observablehq/plot d3 jsdom \
            vega vega-lite lucide-static @tabler/icons @phosphor-icons/core echarts
npm install @excalidraw/utils@0.1.5        # ~97 MB unpacked (includes the fonts and the harfbuzz subsetter)
npm install pptxgenjs                       # only for the PPTX escape hatch
go install github.com/d2lang/d2@v0.9.0      # NOT oss.terrastruct.com/d2@latest (that path is deprecated, gives v0.7.2)
pip install vl-convert-python               # 1.9.0, about 2 min (large wheel)
pip install fonttools brotli                # convert woff2 -> ttf for D2; subset Excalifont
# Graphviz 11 was already installed via chocolatey (dot.exe)
```

Versions tested:

- D2 v0.9.0 (the binary reports `v0.8.1-HEAD`)
- elkjs 0.12.0
- roughjs 4.6.6
- rough-notation 0.5.1
- perfect-freehand 1.2.3
- mermaid 12.1.0
- @observablehq/plot 0.6.17
- vega 6.4.0 / vega-lite 6.4.3 / vl-convert 1.9.0
- echarts 6.1.0
- jsdom 30.1.2
- lucide-static 1.52.0
- @tabler/icons 3.49.0
- @phosphor-icons/core 2.1.1
- @excalidraw/utils 0.1.5
- pptxgenjs 4.0.1
- matplotlib 3.9.3
- Graphviz 11.0.0

## 3. Files

| File | What it does |
|---|---|
| `elk_rough.mjs` | Pipeline graph as ELK JSON (compound nodes = data boundaries). Writes `svg/elk_rough.svg` (sketch), `svg/elk_clean.svg` (crisp) and `svg/layout.json`. Edit the `graph` object to change the diagram. |
| `elk_excalidraw.mjs` + `export_excalidraw.py` | Writes `svg/pipeline.excalidraw` from the ELK layout (open it on excalidraw.com to edit), then exports `svg/excalidraw.svg` headlessly through a localhost server. |
| `d2/*.d2`, `d2.sh` | D2 sources: the pipeline, a sequence diagram and an AWS view. Run with the deck fonts converted to TTF (`fonts-ttf/`). |
| `charts_node.mjs` | Observable Plot confusion matrix and DET curve, plus the ECharts funnel. |
| `charts_vl.py`, `charts_mpl.py` | Vega-Lite latency bars; matplotlib ROC. |
| `freehand.mjs` | perfect-freehand swoosh, circle and arrow. |
| `gv/pipeline.dot` | Graphviz version (for comparison). |
| `samples.template.html` → `build_samples.py` → `samples.html` | Inlines the SVGs (namespacing their ids) into 1280×720 sections. Mermaid and rough-notation run in the page. |
| `render.py` | Playwright render to PDF and PNG, plus the per-page raster audit. |
| `pptx_test.mjs` | pptxgenjs test: native text and shapes plus an SVG diagram. Output `out/pptx_test.pptx`, preview `out/pptx_test_slide1.png`. |

## 4. Vector vs raster (verified with the PDF raster audit)

| Output | In the Chromium PDF |
|---|---|
| Inline SVG from D2, ELK+rough.js, Excalidraw, Graphviz, Plot, Vega-Lite, ECharts SSR, matplotlib; icons; rough-notation; perfect-freehand | **Vector**, text kept as text |
| `<img src="x.svg">` | **Vector**. The SVG is sandboxed, though, so it cannot see the page fonts. Only use `<img>` for SVGs that embed their fonts (D2, Excalidraw). |
| SVG `<image href="data:image/svg+xml...">` (D2 AWS icons) | **Vector** |
| Anything with an SVG/CSS `filter` (feTurbulence/feDisplacementMap "paint" brush, drop-shadow, blur) | **Raster**. Page 12 got a 2421×328 PNG; the text on top stayed vector. Avoid `box-shadow` too, or test it with the audit. |
| Mermaid 12 default flowchart look ("neo") | **Raster**. It adds drop-shadow filters (12 PNGs on one page). Fix: per-diagram frontmatter `config: {look: classic, theme: base}`. |
| Canvas libraries (Chart.js, p5.js / p5.brush, paper.js canvas, Excalidraw `exportToCanvas`) | **Raster**. Do not use them for the PDF. |

## 5. Gotchas hit

1. **D2 install path.** `go install oss.terrastruct.com/d2@latest` installs the deprecated v0.7.2. Use `github.com/d2lang/d2@v0.9.0`.
2. **Space in `$HOME` on this machine** (`/c/Users/Galaba Vamsi`). Always quote `"$HOME/go/bin/d2.exe"`. Nested quoting inside npm scripts broke, so the commands are in `d2.sh`.
3. **D2 fonts.** D2 takes **TTF only** (`--font-regular/--font-bold/--font-semibold`). I converted the deck woff2 files with fontTools (needs `brotli`). D2 draws a white background by default; put `style.fill: transparent` at the root.
4. **Legibility of wide left-to-right pipelines.** These diagrams are 1460–2290 px wide, so they get scaled about 0.55× onto a 1280 slide. D2 at its default 13–18 px gave about 9 px effective text, which is too small. Size the source fonts at 20–24, or keep diagram width ≤ 1.3× the slot. Aim for at least 12 px effective label size.
5. **Mermaid 12 look and theme.** Per-diagram defaults are `look: 'neo'` and `theme: 'redux-color'`. Setting `look` in global `mermaid.initialize()` did **not** override them; frontmatter did. The `handDrawn` look dropped `>` from edge labels (`p > 0.6` became `p 0.6`).
6. **Mermaid adds a `.mermaidTooltip` div to `<body>`.** It pushed the page 6 px past the last slide and **added a blank trailing PDF page**. Hide it with `.mermaidTooltip{display:none}`.
7. **ES modules do not load from `file://`** in Chromium (Excalidraw utils is ESM-only). I served the folder with a throwaway `http.server`. On Windows the registry maps `.js` to `text/plain`, so I forced `text/javascript` (otherwise you get "Failed to fetch dynamically imported module"). Classic `<script>` builds (mermaid.min.js, rough-notation iife) load fine from file://.
8. **@excalidraw/utils 0.1.x API** is `exportToSvg({data:{elements, appState, files}, config:{padding}})`. The older docs show flat arguments, which throws `reading 'appState'`. The "workers for subsetting" console error is harmless.
9. **rough.js `generator.toPaths()` drops `strokeLineDash`.** Re-add `stroke-dasharray` yourself (done in `elk_rough.mjs`).
10. **Graphviz.** It uses Pango with system fonts. The deck fonts are not installed system-wide, so it sizes boxes with fallback metrics ("expect ugly output" warnings). Text still renders in the deck fonts when inlined, but the boxes may misfit. Install the fonts to Windows if you use dot.
11. **pptxgenjs.** The SVG embeds (with a PNG fallback slot) and PowerPoint 365 renders it. However, any font not installed on the viewing PC (Space Grotesk, JetBrains Mono) falls back to Arial. For a PPTX copy, install the fonts or use SVGs with embedded fonts or paths.
12. **Inlining several SVGs in one HTML file** can make `id`/`url(#id)` collide. `build_samples.py` namespaces them.
13. ELK compound edges sometimes jog at container borders. ELK `aspectRatio` and wrapping options exist if you need a 2-row layout for 16:9; I did not tune these.

## 6. Tools evaluated but not built (and why)

- **D2 TALA layout.** Proprietary. Unlicensed renders carry a watermark and commercial use needs a licence. Use ELK or dagre instead.
- **Mermaid** (tested). Fine for a quick sequence diagram. Theming is fiddly, it looks templated, and its small default type is hard to read. `architecture-beta` (tested, `_08`) has only 5 generic built-in icons in fixed blue. Not recommended for the hero diagram.
- **Graphviz** (tested, `_09`). Surprisingly clean and legible. It is the fallback if Node is unavailable.
- **tldraw.** The SDK needs a licence key for production use. The "made with tldraw" watermark applies to apps, and export is via the browser app. More friction than Excalidraw for our needs.
- **draw.io / diagrams.net CLI** (`draw.io.exe -x -f svg`). Needs the Electron desktop app installed. Its SVGs use `<foreignObject>` HTML labels unless you turn on "convert labels to SVG". It has good AWS shape libraries but is manual and GUI-driven.
- **Kroki** (Docker `yuzutech/kroki`). A wrapper around the same renderers, which we already have locally. **PlantUML** needs Java and looks dated. **Structurizr/C4** adds a heavy modelling layer for a 6-node diagram.
- **Isoflow.** The isometric look is eye-catching, but it is a React editor (the Community Edition is MIT) that exports raster. Not worth it 2 days out.
- **roughViz** (d3 + rough, SVG). Unmaintained; Plot + rough-notation covers it. **wired-elements**: web components, so UI rather than slides. **p5.brush / canvas paint libraries / paper.js canvas**: raster in the PDF.
- **Slidev / Marp / reveal.js+decktape / Spectacle / Quarto.** All are Markdown or JSX layers over the same Chromium print path. They would cost us CSS control and add a toolchain for no PDF-quality gain. Marp's and Slidev's PPTX export is image-per-slide, so not editable.
- **Typst + touying/polylux.** These produce excellent native vector PDF and SVG images work, but it means rewriting the deck in a new language. Not worth it 2 days out.
- **python-pptx.** No native SVG support (raster only), so pptxgenjs is the better PPTX route.

## 7. Licences and appendix attribution

Code libraries (attribution is courtesy, but list them in the appendix):

| Asset | Licence | Notes |
|---|---|---|
| ELK / elkjs | EPL-2.0 (or GPL-3.0+) | "Eclipse Layout Kernel, © Kiel University and contributors" |
| rough.js, rough-notation | MIT | © Preet Shihn |
| perfect-freehand | MIT | © Steve Ruiz |
| D2 | MPL-2.0 | © Terrastruct. Do not use TALA. |
| Excalidraw (@excalidraw/utils) | MIT | |
| Mermaid | MIT | only if used |
| Graphviz | EPL-1.0 | only if used |
| Observable Plot, d3 | ISC | © Observable, Inc. / Mike Bostock |
| Vega, Vega-Lite, vl-convert | BSD-3-Clause | UW Interactive Data Lab |
| Apache ECharts | Apache-2.0 | |
| matplotlib | Matplotlib licence (PSF-style) | |
| jsdom | MIT | |
| Playwright | Apache-2.0 | |
| pptxgenjs | MIT | only if used |

Fonts (all **SIL OFL-1.1**):

- Inter
- Space Grotesk
- JetBrains Mono
- Noto Sans Devanagari
- Excalifont (the Excalidraw build bundles LXGW/Google/Ascender glyph data, which is also OFL)
- Virgil (only if used)

Icons:

| Set | Licence | Attribution |
|---|---|---|
| Phosphor | MIT | |
| Lucide | ISC (parts from Feather, MIT) | |
| Tabler | MIT | |
| Heroicons | MIT | |
| Iconoir | MIT | |
| Material Symbols | Apache-2.0 | |

Licence notices are not required on the slide itself; listing them in the appendix is enough.

Illustrations:

| Set | Terms |
|---|---|
| Open Peeps | CC0. No attribution needed. |
| Humaaans | CC0 |
| unDraw | Free for commercial use, no attribution. You may not redistribute packs, build a competing service, or use the assets for AI/ML training. |
| Blush | Free, "without permission from or attributing". |
| DrawKit | Free packs, no attribution; royalty-free licence. |
| Storyset | **Attribution REQUIRED on free use** ("Illustrations by Storyset"), or buy a premium Flaticon/Freepik licence. Avoid unless credited. |

AWS Architecture Icons (aws.amazon.com/architecture/icons):

- AWS lets customers and partners use the icons to create architecture diagrams, including in presentations and whitepapers.
- Do **not** recolour, crop or modify them. Do not use them as our product logo or imply endorsement.
- Do not mix icon releases.

Suggested credit line:
`Architecture icons: AWS Architecture Icons (release MMDDYYYY), © Amazon Web Services, Inc. or its affiliates. Used to identify services; no endorsement implied.`

Suggested appendix block:

> **Third-party assets.**
> - Diagrams laid out with ELK (elkjs, EPL-2.0) and drawn with rough.js (MIT); annotations by rough-notation (MIT) and perfect-freehand (MIT).
> - Charts: Observable Plot (ISC).
> - Icons: Phosphor Icons (MIT).
> - Fonts: Inter, Space Grotesk, JetBrains Mono, Noto Sans Devanagari, Excalifont (SIL OFL-1.1).
> - AWS Architecture Icons © Amazon Web Services, used per AWS icon terms.
> - Rendered with Playwright/Chromium (Apache-2.0).
> - Illustrations: Open Peeps by Pablo Stanley (CC0).
