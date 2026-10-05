// Observable Plot (via jsdom) and ECharts (SSR SVG renderer, no DOM) -> static SVG files.
import * as Plot from '@observablehq/plot';
import { JSDOM } from 'jsdom';
import * as echarts from 'echarts';
import fs from 'node:fs';

const INK = '#1B1F24', MUTE = '#5A6270', SAF = '#E8772E', TEAL = '#127A72', RED = '#C8372D';
const { document } = new JSDOM('').window;

// ---- Observable Plot: confusion matrix (counts on held-out set) ----
const cm = [
  { truth: 'Fraud', pred: 'Fraud', n: 412 }, { truth: 'Fraud', pred: 'Legit', n: 23 },
  { truth: 'Legit', pred: 'Fraud', n: 31 }, { truth: 'Legit', pred: 'Legit', n: 4534 },
];
const cmSvg = Plot.plot({
  document, width: 300, height: 260, marginLeft: 70, marginTop: 40, padding: 0.06,
  style: { fontFamily: 'Inter', fontSize: '13px', color: INK, background: 'transparent' },
  x: { label: 'PREDICTED', axis: 'top', domain: ['Fraud', 'Legit'], tickSize: 0 },
  y: { label: 'ACTUAL', domain: ['Fraud', 'Legit'], tickSize: 0 },
  color: { type: 'log', range: ['#FBEBDC', SAF] },
  marks: [
    Plot.cell(cm, { x: 'pred', y: 'truth', fill: 'n', rx: 6 }),
    Plot.text(cm, { x: 'pred', y: 'truth', text: d => d.n.toLocaleString('en-IN'), fontSize: 22, fontWeight: 700,
      fill: d => (d.n > 300 ? 'white' : INK), fontFamily: 'Space Grotesk' }),
  ],
});
let s = cmSvg.outerHTML;
if (!s.includes('xmlns=')) s = s.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"');
fs.writeFileSync('svg/plot_confusion.svg', s);

// ---- Observable Plot: DET-style curve (log axes) ----
const det = (k) => Array.from({ length: 40 }, (_, i) => { const fpr = 10 ** (-3 + i * 3 / 39); return { fpr, fnr: Math.min(0.6, k / (fpr ** 0.55) / 100) }; });
const curves = [...det(0.9).map(d => ({ ...d, m: 'Ensemble' })), ...det(2.4).map(d => ({ ...d, m: 'Voice-only' }))];
const detSvg = Plot.plot({
  document, width: 360, height: 260, marginLeft: 50, marginBottom: 40,
  style: { fontFamily: 'Inter', fontSize: '12px', color: INK, background: 'transparent' },
  x: { type: 'log', label: 'False-alarm rate →', grid: true, tickFormat: '.1%' },
  y: { type: 'log', label: '↑ Miss rate', grid: true, tickFormat: '.0%' },
  color: { domain: ['Ensemble', 'Voice-only'], range: [SAF, '#9AA3AE'] },
  marks: [
    Plot.line(curves, { x: 'fpr', y: 'fnr', stroke: 'm', strokeWidth: 2.5 }),
    Plot.dot([{ fpr: 0.0068, fnr: 0.053 }], { x: 'fpr', y: 'fnr', r: 5, fill: RED }),
    Plot.text([{ fpr: 0.0068, fnr: 0.053 }], { x: 'fpr', y: 'fnr', text: () => 'operating point', dx: 8, dy: -10, textAnchor: 'start', fill: RED, fontFamily: 'JetBrains Mono' }),
    Plot.text(['Ensemble', 'Voice-only'].map((m, i) => ({ m, fpr: 0.25, fnr: i ? 0.05 : 0.018 })), { x: 'fpr', y: 'fnr', text: 'm', fill: 'm', fontWeight: 600 }),
  ],
});
s = detSvg.outerHTML;
if (!s.includes('xmlns=')) s = s.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"');
fs.writeFileSync('svg/plot_det.svg', s);

// ---- ECharts SSR: funnel ----
const chart = echarts.init(null, null, { renderer: 'svg', ssr: true, width: 380, height: 260 });
chart.setOption({
  animation: false, textStyle: { fontFamily: 'Inter' },
  series: [{ type: 'funnel', left: 10, right: 120, top: 10, bottom: 10, gap: 3, sort: 'descending', minSize: '18%',
    label: { position: 'right', color: INK, fontSize: 13, formatter: p => `{b|${p.name}}  {v|${p.value.toLocaleString('en-IN')}}`,
      rich: { b: { fontFamily: 'Inter', fontSize: 13, color: INK }, v: { fontFamily: 'JetBrains Mono', fontSize: 12, color: MUTE } } },
    labelLine: { show: false }, itemStyle: { borderWidth: 0 },
    data: [
      { name: 'Calls screened', value: 100000, itemStyle: { color: '#E3DED3' } },
      { name: 'Flagged', value: 4200, itemStyle: { color: '#F3D2B4' } },
      { name: 'Step-up sent', value: 2900, itemStyle: { color: SAF } },
      { name: 'Human review', value: 610, itemStyle: { color: TEAL } },
      { name: 'Fraud blocked', value: 412, itemStyle: { color: INK } },
    ] }],
});
fs.writeFileSync('svg/echarts_funnel.svg', chart.renderToSVGString());
chart.dispose();
console.log('charts ok');
