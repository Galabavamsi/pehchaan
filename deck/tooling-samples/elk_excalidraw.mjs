// ELK layout (svg/layout.json) -> editable .excalidraw scene. Exported to SVG by export_excalidraw.py
// (runs @excalidraw/utils exportToSvg in headless Chromium). The .excalidraw file opens on excalidraw.com
// for hand tweaks, so the team keeps an editable source of truth.
import fs from 'node:fs';
const L = JSON.parse(fs.readFileSync('svg/layout.json', 'utf8'));
let seed = 100;
const id = () => 'el' + (seed++);
const base = (o) => ({ angle: 0, strokeWidth: 2, strokeStyle: 'solid', roughness: 1, opacity: 100, groupIds: [], frameId: null,
  seed: seed * 7, version: 1, versionNonce: seed, isDeleted: false, boundElements: [], updated: 1, link: null, locked: false, ...o });
const kind = {
  boundary: { strokeColor: '#8E97A3', backgroundColor: '#EFE8DA', fillStyle: 'hachure', strokeStyle: 'dashed', strokeWidth: 1 },
  group: { strokeColor: '#E8772E', backgroundColor: '#FFF7EE', fillStyle: 'solid' },
  stage: { strokeColor: '#1B1F24', backgroundColor: '#FFFFFF', fillStyle: 'solid' },
  source: { strokeColor: '#1B1F24', backgroundColor: '#FFFFFF', fillStyle: 'solid', type: 'ellipse' },
  det: { strokeColor: '#E8772E', backgroundColor: '#FFE9D3', fillStyle: 'cross-hatch' },
  core: { strokeColor: '#1B1F24', backgroundColor: '#1B1F24', fillStyle: 'solid' },
  out: { strokeColor: '#127A72', backgroundColor: '#DDF0EC', fillStyle: 'zigzag' },
  store: { strokeColor: '#1B1F24', backgroundColor: '#E9E4F5', fillStyle: 'solid' },
};
const els = [];
for (const n of L.nodes) {
  const k = kind[n.kind];
  const shape = base({ id: id(), type: k.type || 'rectangle', x: n.x, y: n.y, width: n.w, height: n.h, roundness: { type: 3 }, ...k });
  delete shape.type; shape.type = k.type || 'rectangle';
  els.push(shape);
  const isTitle = n.kind === 'boundary' || n.kind === 'group';
  const fsz = isTitle ? (n.kind === 'group' ? 16 : 13) : (n.fs || 16);
  const lines = n.label.split('\n');
  const tw = Math.max(...lines.map(l => l.length)) * fsz * 0.55, th = lines.length * fsz * 1.25;
  els.push(base({ id: id(), type: 'text', text: n.label, originalText: n.label, fontSize: fsz, fontFamily: 5 /* Excalifont */,
    textAlign: isTitle ? 'left' : 'center', verticalAlign: 'middle', containerId: null, lineHeight: 1.25, autoResize: true,
    strokeColor: n.kind === 'core' ? '#FFFFFF' : n.kind === 'group' ? '#B4521A' : n.kind === 'boundary' ? '#5A6270' : '#1B1F24',
    backgroundColor: 'transparent', fillStyle: 'solid', roundness: null,
    x: isTitle ? n.x + 16 : n.x + n.w / 2 - tw / 2, y: isTitle ? n.y + 10 : n.y + n.h / 2 - th / 2, width: tw, height: th }));
}
for (const e of L.edges) {
  const [x0, y0] = e.pts[0];
  els.push(base({ id: id(), type: 'arrow', x: x0, y: y0, width: 1, height: 1, strokeColor: e.color || '#1B1F24', backgroundColor: 'transparent',
    fillStyle: 'solid', roundness: null, points: e.pts.map(([x, y]) => [x - x0, y - y0]), startBinding: null, endBinding: null,
    startArrowhead: null, endArrowhead: 'arrow', elbowed: false }));
  if (e.label) els.push(base({ id: id(), type: 'text', text: e.label, originalText: e.label, fontSize: 13, fontFamily: 5, textAlign: 'left',
    verticalAlign: 'top', containerId: null, lineHeight: 1.25, autoResize: true, strokeColor: e.color || '#5A6270', backgroundColor: 'transparent',
    fillStyle: 'solid', roundness: null, x: e.labelPos[0], y: e.labelPos[1] - 2, width: e.label.length * 7.2, height: 16 }));
}
const scene = { type: 'excalidraw', version: 2, source: 'raksham-tooling-samples', elements: els,
  appState: { viewBackgroundColor: '#F6F1E7', exportBackground: false, exportWithDarkMode: false }, files: {} };
fs.writeFileSync('svg/pipeline.excalidraw', JSON.stringify(scene, null, 1));
console.log('excalidraw scene:', els.length, 'elements');
