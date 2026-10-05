// perfect-freehand -> SVG brush strokes (vector paths): underline swoosh, circle, arrow.
import { getStroke } from 'perfect-freehand';
import fs from 'node:fs';
const toD = (pts) => {
  if (!pts.length) return '';
  const d = pts.reduce((acc, [x0, y0], i, a) => { const [x1, y1] = a[(i + 1) % a.length]; acc.push(x0, y0, (x0 + x1) / 2, (y0 + y1) / 2); return acc; }, ['M', ...pts[0], 'Q']);
  return d.join(' ') + ' Z';
};
// pseudo "hand" input: points with varying pressure
const swoosh = Array.from({ length: 60 }, (_, i) => { const t = i / 59; return [10 + t * 520, 30 + Math.sin(t * 3.1) * 6 - t * 10, 0.3 + Math.sin(t * Math.PI) * 0.7]; });
const circle = Array.from({ length: 80 }, (_, i) => { const t = i / 79 * Math.PI * 2.15; return [150 + Math.cos(t) * 130 * (1 + 0.04 * Math.sin(5 * t)), 60 + Math.sin(t) * 46, 0.5 + 0.4 * Math.sin(t)]; });
const arrow = Array.from({ length: 50 }, (_, i) => { const t = i / 49; return [10 + t * 240, 80 - Math.sin(t * Math.PI) * 60 + t * 10, 0.6]; });
const opt = (size) => ({ size, thinning: 0.65, smoothing: 0.5, streamline: 0.4, simulatePressure: false, start: { taper: 40 }, end: { taper: 60 } });
fs.writeFileSync('svg/freehand_swoosh.svg', `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 540 60"><path d="${toD(getStroke(swoosh, opt(14)))}" fill="#E8772E"/></svg>`);
fs.writeFileSync('svg/freehand_circle.svg', `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 120"><path d="${toD(getStroke(circle, opt(7)))}" fill="#C8372D"/></svg>`);
const end = arrow[arrow.length - 1];
fs.writeFileSync('svg/freehand_arrow.svg', `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 110"><path d="${toD(getStroke(arrow, opt(6)))}" fill="#1B1F24"/>` +
  `<path d="${toD(getStroke([[end[0] - 22, end[1] - 14, .5], [end[0], end[1], .8], [end[0] - 24, end[1] + 10, .5]], { ...opt(6), start: { taper: 10 }, end: { taper: 10 } }))}" fill="#1B1F24"/></svg>`);
console.log('freehand ok');
