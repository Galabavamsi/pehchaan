"""Vega-Lite -> SVG offline via vl-convert (no browser, no network)."""
import json, pathlib, vl_convert as vlc
vlc.register_font_directory(str(pathlib.Path('fonts-ttf').resolve()))
INK, MUTE, SAF, TEAL, RED = '#1B1F24', '#5A6270', '#E8772E', '#127A72', '#C8372D'
stages = [("Feature extraction", 38, 61), ("Synthetic-voice detector", 74, 118), ("Intent model (ASR+LM)", 142, 230),
          ("Risk fusion", 6, 9), ("Step-up trigger", 21, 40)]
data = [{"stage": s, "p50": a, "p95": b} for s, a, b in stages]
spec = {
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "width": 470, "height": 210, "background": None, "data": {"values": data},
  "config": {"font": "Inter", "view": {"stroke": None},
             "axis": {"labelFont": "Inter", "labelFontSize": 13, "labelColor": INK, "titleFont": "JetBrains Mono", "titleFontSize": 11,
                      "titleColor": MUTE, "titleFontWeight": 400, "domain": False, "ticks": False, "gridColor": "#E3DED3"}},
  "encoding": {"y": {"field": "stage", "type": "nominal", "sort": None, "title": None, "axis": {"labelPadding": 8}}},
  "layer": [
    {"mark": {"type": "bar", "color": "#F3D2B4", "cornerRadiusEnd": 3, "height": 18},
     "encoding": {"x": {"field": "p95", "type": "quantitative", "title": "LATENCY (ms) — bar = p95, tick = p50", "axis": {"tickCount": 5}}}},
    {"mark": {"type": "tick", "color": SAF, "thickness": 3, "size": 18}, "encoding": {"x": {"field": "p50", "type": "quantitative"}}},
    {"mark": {"type": "text", "align": "left", "dx": 6, "font": "JetBrains Mono", "fontSize": 12, "color": MUTE},
     "encoding": {"x": {"field": "p95", "type": "quantitative"}, "text": {"field": "p95", "format": "d"}}},
    {"data": {"values": [{"x": 300}]}, "mark": {"type": "rule", "color": RED, "strokeDash": [4, 3], "strokeWidth": 1.5},
     "encoding": {"x": {"field": "x", "type": "quantitative"}, "y": {"value": 0}, "y2": {"value": 210}}},
  ],
}
pathlib.Path('svg/vl_latency.svg').write_text(vlc.vegalite_to_svg(json.dumps(spec)), encoding='utf-8')
print('vl ok')
