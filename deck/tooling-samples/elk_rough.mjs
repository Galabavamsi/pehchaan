// ELK.js computes the layout (compound nodes = data boundaries), rough.js draws it.
// Output: svg/elk_rough.svg (pure vector; <text> uses the deck's web fonts when inlined in HTML)
// and svg/elk_clean.svg (same layout, crisp non-sketch rendering) -- one layout, two skins.
import ELK from 'elkjs/lib/elk.bundled.js';
import rough from 'roughjs/bundled/rough.esm.js';
import fs from 'node:fs';

const C = { ink: '#1B1F24', mute: '#5A6270', paper: '#F6F1E7', saffron: '#E8772E', teal: '#127A72', red: '#C8372D', white: '#FFFFFF' };
// crude text metric for Inter ~0.56em per glyph; good enough to size boxes (we pad generously)
const tw = (s, fs) => Math.max(...s.split('\n').map(l => l.length)) * fs * 0.56;
const node = (id, label, kind = 'stage', fs = 16) => {
  const lines = label.split('\n');
  return { id, labels: [{ text: label }], kind, fs, width: Math.max(130, tw(label, fs) + 36), height: 26 + lines.length * fs * 1.3 };
};

const graph = {
  id: 'root',
  layoutOptions: {
    'elk.algorithm': 'layered', 'elk.direction': 'RIGHT', 'elk.hierarchyHandling': 'INCLUDE_CHILDREN',
    'elk.edgeRouting': 'ORTHOGONAL', 'elk.layered.spacing.nodeNodeBetweenLayers': '56', 'elk.spacing.nodeNode': '26',
    'elk.padding': '[top=16,left=16,bottom=16,right=16]', 'elk.layered.nodePlacement.strategy': 'NETWORK_SIMPLEX',
  },
  children: [
    { id: 'edge', kind: 'boundary', title: 'BANK / TELCO EDGE — raw audio stays here',
      layoutOptions: { 'elk.padding': '[top=44,left=20,bottom=20,right=20]' },
      children: [node('audio', 'Call audio\n8 kHz stream', 'source'), node('feat', 'Feature extraction\nlog-mel · prosody · codec')] },
    { id: 'cloud', kind: 'boundary', title: 'DETECTION CLOUD — features + scores only',
      layoutOptions: { 'elk.padding': '[top=44,left=20,bottom=20,right=20]' },
      children: [
        { id: 'ens', kind: 'group', title: 'Detector ensemble', layoutOptions: { 'elk.padding': '[top=40,left=16,bottom=16,right=16]', 'elk.spacing.nodeNode': '14' },
          children: [node('d1', 'Synthetic-voice\ndetector', 'det', 14), node('d2', 'Scam-script\nintent model', 'det', 14), node('d3', 'Caller-ID /\nSIM-swap signals', 'det', 14)] },
        node('fuse', 'Risk fusion\ncalibrated p(fraud)', 'core'),
        node('step', 'Step-up auth', 'out'), node('human', 'Human review\nanalyst queue', 'out'),
        node('vault', 'Evidence vault\nhash-chained · WORM', 'store'),
      ] },
  ],
  edges: [
    ['e1', 'audio', 'feat', '20 ms frames'], ['e2', 'feat', 'd1'], ['e3', 'feat', 'd2'], ['e4', 'feat', 'd3'],
    ['e5', 'd1', 'fuse'], ['e6', 'd2', 'fuse'], ['e7', 'd3', 'fuse'],
    ['e8', 'fuse', 'step', 'p > 0.6', C.teal], ['e9', 'fuse', 'human', 'p > 0.9', C.red], ['e10', 'fuse', 'vault', 'audit', C.mute],
  ].map(([id, s, t, label, color]) => ({ id, sources: [s], targets: [t], color, labels: label ? [{ text: label, width: tw(label, 12) + 8, height: 16 }] : [] })),
};

const elk = new ELK();
const laid = await elk.layout(graph);

function render(sketch) {
  const g = rough.generator();
  const out = [];
  const base = { roughness: sketch ? 1.3 : 0, bowing: sketch ? 1 : 0, seed: 7, preserveVertices: !sketch, disableMultiStroke: !sketch };
  // NB: generator.toPaths() drops strokeLineDash, so re-apply it as stroke-dasharray on the outline path (not on hachure fills)
  const paths = (drawable) => g.toPaths(drawable).map(p =>
    `<path d="${p.d}" stroke="${p.stroke}" stroke-width="${p.strokeWidth}" fill="${p.fill || 'none'}" stroke-linecap="round" stroke-linejoin="round"` +
    `${drawable.options.strokeLineDash && p.stroke === drawable.options.stroke && p.strokeWidth === drawable.options.strokeWidth ? ` stroke-dasharray="${drawable.options.strokeLineDash.join(' ')}"` : ''}/>`).join('');
  const text = (x, y, s, { fs = 16, fam = 'Inter', w = 500, fill = C.ink, anchor = 'middle', ls = 0 } = {}) => {
    const lines = s.split('\n');
    const y0 = y - ((lines.length - 1) * fs * 1.25) / 2;
    return `<text x="${x}" text-anchor="${anchor}" font-family="${fam}" font-size="${fs}" font-weight="${w}" fill="${fill}" letter-spacing="${ls}">` +
      lines.map((l, i) => `<tspan x="${x}" y="${y0 + i * fs * 1.25 + fs * 0.35}" ${i ? `font-weight="400" fill="${C.mute}" font-size="${fs * 0.82}"` : ''}>${l}</tspan>`).join('') + '</text>';
  };
  const style = {
    boundary: { stroke: '#8E97A3', strokeWidth: 1.6, strokeLineDash: [7, 6], fill: sketch ? '#EFE8DA' : '#F1ECE2', fillStyle: sketch ? 'hachure' : 'solid', hachureGap: 9, fillWeight: 0.6, hachureAngle: -41 },
    group: { stroke: C.saffron, strokeWidth: 1.8, fill: '#FFF7EE', fillStyle: 'solid' },
    stage: { stroke: C.ink, strokeWidth: 2, fill: C.white, fillStyle: 'solid' },
    source: { stroke: C.ink, strokeWidth: 2, fill: C.white, fillStyle: 'solid' },
    det: { stroke: C.saffron, strokeWidth: 1.8, fill: '#FFE9D3', fillStyle: sketch ? 'cross-hatch' : 'solid', hachureGap: 6, fillWeight: 0.5 },
    core: { stroke: C.ink, strokeWidth: 2.2, fill: C.ink, fillStyle: 'solid' },
    out: { stroke: C.teal, strokeWidth: 2, fill: '#DDF0EC', fillStyle: sketch ? 'zigzag' : 'solid', hachureGap: 7, fillWeight: 0.7 },
    store: { stroke: C.ink, strokeWidth: 2, fill: '#E9E4F5', fillStyle: 'solid' },
  };
  function walk(n, ox, oy) {
    const x = ox + (n.x || 0), y = oy + (n.y || 0);
    if (n.id !== 'root') {
      const s = { ...base, ...style[n.kind] };
      if (n.kind === 'source') out.push(paths(g.ellipse(x + n.width / 2, y + n.height / 2, n.width, n.height, s)));
      else if (n.kind === 'store') {
        out.push(paths(g.rectangle(x, y + 8, n.width, n.height - 8, s)));
        out.push(paths(g.ellipse(x + n.width / 2, y + 8, n.width, 16, s)));
      } else out.push(paths(g.rectangle(x, y, n.width, n.height, s)));
      if (n.kind === 'boundary') out.push(text(x + 18, y + 24, n.title, { fs: 12.5, fam: 'JetBrains Mono', w: 600, fill: C.mute, anchor: 'start', ls: 0.6 }));
      else if (n.kind === 'group') out.push(text(x + 16, y + 22, n.title, { fs: 15, fam: 'Space Grotesk', w: 700, fill: '#B4521A', anchor: 'start' }));
      else out.push(text(x + n.width / 2, y + n.height / 2 + (n.kind === 'store' ? 4 : 0), n.labels[0].text,
        { fs: n.fs, fam: 'Space Grotesk', w: 600, fill: n.kind === 'core' ? C.white : C.ink }));
    }
    (n.children || []).forEach(c => walk(c, x, y));
    (n.edges || []).forEach(e => {
      // with INCLUDE_CHILDREN, coordinates are relative to e.container's position
      const cont = e.container && e.container !== n.id ? find(laid, e.container) : null;
      const [cx, cy] = cont ? abs(cont.id) : [x, y];
      const color = e.color || C.ink;
      e.sections.forEach(sec => {
        const pts = [sec.startPoint, ...(sec.bendPoints || []), sec.endPoint].map(p => [cx + p.x, cy + p.y]);
        out.push(paths(g.linearPath(pts, { ...base, stroke: color, strokeWidth: 1.8, roughness: sketch ? 0.9 : 0 })));
        const [a, b] = [pts[pts.length - 2], pts[pts.length - 1]];
        const ang = Math.atan2(b[1] - a[1], b[0] - a[0]), L = 11;
        const head = [[b[0] - L * Math.cos(ang - 0.42), b[1] - L * Math.sin(ang - 0.42)], b, [b[0] - L * Math.cos(ang + 0.42), b[1] - L * Math.sin(ang + 0.42)]];
        out.push(sketch ? paths(g.linearPath(head, { ...base, stroke: color, strokeWidth: 1.8, roughness: 0.6 }))
          : `<path d="M${head[0]}L${head[1]}L${head[2]}Z" fill="${color}"/>`);
      });
      (e.labels || []).forEach(l => out.push(
        `<rect x="${cx + l.x - 2}" y="${cy + l.y - 1}" width="${l.width + 4}" height="${l.height + 2}" rx="3" fill="${C.paper}" opacity="0.92"/>` +
        text(cx + l.x + l.width / 2, cy + l.y + l.height / 2, l.text, { fs: 12, fam: 'JetBrains Mono', w: 400, fill: color === C.ink ? C.mute : color })));
    });
  }
  walk(laid, 0, 0);
  const W = Math.ceil(laid.width), H = Math.ceil(laid.height);
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">${out.join('\n')}</svg>`;
}
const index = {};
(function idx(n, ox, oy) { const x = ox + (n.x || 0), y = oy + (n.y || 0); index[n.id] = { n, x, y }; (n.children || []).forEach(c => idx(c, x, y)); })(laid, 0, 0);
function find(_, id) { return index[id].n; }
function abs(id) { return [index[id].x, index[id].y]; }

// flattened absolute layout, reused by elk_excalidraw.mjs
const flat = { nodes: Object.values(index).filter(o => o.n.id !== 'root').map(({ n, x, y }) => ({ id: n.id, kind: n.kind, x, y, w: n.width, h: n.height, label: n.title || n.labels?.[0]?.text, fs: n.fs })), edges: [] };
for (const e of laid.edges) {
  const [cx, cy] = e.container && e.container !== 'root' ? abs(e.container) : [0, 0];
  for (const sec of e.sections) flat.edges.push({ id: e.id, src: e.sources[0], dst: e.targets[0], color: e.color, label: e.labels?.[0]?.text,
    labelPos: e.labels?.[0] ? [cx + e.labels[0].x, cy + e.labels[0].y] : null,
    pts: [sec.startPoint, ...(sec.bendPoints || []), sec.endPoint].map(p => [cx + p.x, cy + p.y]) });
}
fs.writeFileSync('svg/layout.json', JSON.stringify(flat, null, 1));
fs.writeFileSync('svg/elk_rough.svg', render(true));
fs.writeFileSync('svg/elk_clean.svg', render(false));
console.log('layout', Math.round(laid.width), 'x', Math.round(laid.height));
