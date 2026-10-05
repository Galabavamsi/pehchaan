"""Inline every svg/*.svg into samples.template.html -> samples.html.

Placeholders: {{svg:name}} inlines svg/name.svg (prolog/doctype stripped, ids namespaced so several
SVGs can share one HTML document without url(#id) collisions). {{icon:path}} inlines an icon from node_modules.
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).parent


def clean(svg: str, ns: str) -> str:
    svg = re.sub(r"<\?xml[^>]*\?>", "", svg)
    svg = re.sub(r"<!DOCTYPE[^>]*>", "", svg, flags=re.S)
    svg = re.sub(r"<!--.*?-->", "", svg, flags=re.S)
    ids = set(re.findall(r'\bid="([^"]+)"', svg))
    for i in sorted(ids, key=len, reverse=True):
        svg = svg.replace(f'id="{i}"', f'id="{ns}-{i}"').replace(f"#{i})", f"#{ns}-{i})").replace(f'"#{i}"', f'"#{ns}-{i}"')
    return svg.strip()


def main() -> None:
    tpl = (ROOT / "samples.template.html").read_text(encoding="utf-8")
    tpl = re.sub(r"\{\{svg:([\w-]+)\}\}", lambda m: clean((ROOT / "svg" / f"{m[1]}.svg").read_text(encoding="utf-8"), m[1]), tpl)
    tpl = re.sub(r"\{\{icon:([^}]+)\}\}", lambda m: clean((ROOT / "node_modules" / m[1]).read_text(encoding="utf-8"), "ic"), tpl)
    (ROOT / "samples.html").write_text(tpl, encoding="utf-8")
    print("wrote samples.html", len(tpl) // 1024, "KB")


if __name__ == "__main__":
    main()
