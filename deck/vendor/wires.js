// Deck renderer: rough.js connectors + sketchy boxes over HTML layouts, rough-notation accents.
// Sets window.__ready = true when everything is drawn (build.py waits for it before printing).
(function () {
  window.__ready = false;
  const COLORS = {
    ink: '#1B1F24', mute: '#7A818C', saff: '#E8742A', teal: '#13796F', red: '#C8372D',
    amber: '#C98E12', lav: '#6B5CA5', line: '#B9B0A0',
  };
  const col = (c) => COLORS[c] || c || COLORS.ink;
  const NS = 'http://www.w3.org/2000/svg';

  function overlay(host) {
    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('class', 'wires-layer');
    svg.setAttribute('width', host.clientWidth);
    svg.setAttribute('height', host.clientHeight);
    svg.style.cssText = 'position:absolute;left:0;top:0;overflow:visible;pointer-events:none;z-index:0';
    host.insertBefore(svg, host.firstChild);
    return svg;
  }

  function rel(el, host) {
    const a = el.getBoundingClientRect(), b = host.getBoundingClientRect();
    return { x: a.left - b.left, y: a.top - b.top, w: a.width, h: a.height };
  }

  function anchor(r, side, off = 0) {
    switch (side) {
      case 'l': return [r.x, r.y + r.h / 2 + off];
      case 'r': return [r.x + r.w, r.y + r.h / 2 + off];
      case 't': return [r.x + r.w / 2 + off, r.y];
      case 'b': return [r.x + r.w / 2 + off, r.y + r.h];
    }
  }

  function route(S, E, fs, ts, mid = 0.5) {
    const hz = (s) => s === 'l' || s === 'r';
    if (hz(fs) && hz(ts)) {
      if (Math.abs(S[1] - E[1]) < 1.5) return [S, E];
      const x = S[0] + (E[0] - S[0]) * mid;
      return [S, [x, S[1]], [x, E[1]], E];
    }
    if (!hz(fs) && !hz(ts)) {
      if (Math.abs(S[0] - E[0]) < 1.5) return [S, E];
      const y = S[1] + (E[1] - S[1]) * mid;
      return [S, [S[0], y], [E[0], y], E];
    }
    return hz(fs) ? [S, [E[0], S[1]], E] : [S, [S[0], E[1]], E];
  }

  function along(pts, f) {
    const segs = [];
    let total = 0;
    for (let i = 1; i < pts.length; i++) {
      const L = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
      segs.push(L);
      total += L;
    }
    let d = total * f;
    for (let i = 0; i < segs.length; i++) {
      if (d <= segs[i] || i === segs.length - 1) {
        const t = segs[i] ? Math.min(1, d / segs[i]) : 0;
        return [pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t];
      }
      d -= segs[i];
    }
    return pts[pts.length - 1];
  }

  function drawWires(host) {
    const spec = host.querySelector('script.wires');
    if (!spec) return;
    const wires = JSON.parse(spec.textContent);
    const sketch = host.dataset.sketch !== 'false';
    const svg = host.querySelector(':scope > svg.wires-layer') || overlay(host);
    const rc = rough.svg(svg);
    for (const w of wires) {
      const a = host.querySelector(`[data-n="${w.f}"]`), b = host.querySelector(`[data-n="${w.t}"]`);
      if (!a || !b) { console.warn('wire endpoint missing', w.f, w.t); continue; }
      const ra = rel(a, host), rb = rel(b, host);
      const gap = w.gap ?? 3;
      let S = anchor(ra, w.fs || 'r', w.fo || 0), E = anchor(rb, w.ts || 'l', w.to || 0);
      const push = (p, side, g) => side === 'l' ? [p[0] - g, p[1]] : side === 'r' ? [p[0] + g, p[1]] : side === 't' ? [p[0], p[1] - g] : [p[0], p[1] + g];
      S = push(S, w.fs || 'r', gap); E = push(E, w.ts || 'l', gap + 1);
      const pts = w.pts ? [S, ...w.pts, E] : route(S, E, w.fs || 'r', w.ts || 'l', w.mid ?? 0.5);
      const c = col(w.c);
      const opts = { stroke: c, strokeWidth: w.sw || 1.7, roughness: sketch ? 0.8 : 0, bowing: sketch ? 0.6 : 0, seed: 3, disableMultiStroke: !sketch, preserveVertices: !sketch };
      if (w.d) opts.strokeLineDash = [6, 5];
      svg.appendChild(rc.linearPath(pts, opts));
      // arrowhead
      const [p, q] = [pts[pts.length - 2], pts[pts.length - 1]];
      const ang = Math.atan2(q[1] - p[1], q[0] - p[0]), L = 9;
      if (!w.noHead) {
        const head = document.createElementNS(NS, 'path');
        head.setAttribute('d', `M${q[0] - L * Math.cos(ang - 0.45)},${q[1] - L * Math.sin(ang - 0.45)}L${q[0]},${q[1]}L${q[0] - L * Math.cos(ang + 0.45)},${q[1] - L * Math.sin(ang + 0.45)}Z`);
        head.setAttribute('fill', c);
        svg.appendChild(head);
      }
      if (w.both) {
        const [p2, q2] = [pts[1], pts[0]];
        const ang2 = Math.atan2(q2[1] - p2[1], q2[0] - p2[0]);
        const head2 = document.createElementNS(NS, 'path');
        head2.setAttribute('d', `M${q2[0] - L * Math.cos(ang2 - 0.45)},${q2[1] - L * Math.sin(ang2 - 0.45)}L${q2[0]},${q2[1]}L${q2[0] - L * Math.cos(ang2 + 0.45)},${q2[1] - L * Math.sin(ang2 + 0.45)}Z`);
        head2.setAttribute('fill', c);
        svg.appendChild(head2);
      }
      if (w.lab) {
        const [lx, ly] = along(pts, w.lp ?? 0.5);
        const s = document.createElement('span');
        s.className = 'wlab' + (w.lc ? ' ' + w.lc : '');
        s.textContent = w.lab;
        s.style.color = w.c && w.c !== 'ink' ? c : '';
        host.appendChild(s);
        s.style.left = `${lx - s.offsetWidth / 2 + (w.lx || 0)}px`;
        s.style.top = `${ly - s.offsetHeight / 2 + (w.ly || 0)}px`;
      }
    }
  }

  // Sketchy outlines behind elements with class "rb" (data-stroke, data-fill, data-fs=hachure|solid|cross-hatch|zigzag, data-dash)
  function drawBoxes(slide) {
    const boxes = slide.querySelectorAll('.rb');
    if (!boxes.length) return;
    const svg = overlay(slide);
    svg.style.zIndex = 0;
    const rc = rough.svg(svg);
    let seed = 11;
    boxes.forEach((el) => {
      const r = rel(el, slide);
      const sketch = !el.closest('[data-sketch="false"]');
      const opts = {
        stroke: col(el.dataset.stroke || 'ink'), strokeWidth: +(el.dataset.sw || 1.6),
        fill: el.dataset.fill || undefined, fillStyle: el.dataset.fs || 'solid', hachureGap: +(el.dataset.hg || 7), fillWeight: 0.6,
        roughness: sketch ? +(el.dataset.rough || 1.1) : 0, bowing: sketch ? 0.8 : 0, seed: seed++, disableMultiStroke: !sketch, preserveVertices: !sketch,
      };
      if (el.dataset.dash) opts.strokeLineDash = [7, 6];
      const shape = el.dataset.shape === 'ellipse'
        ? rc.ellipse(r.x + r.w / 2, r.y + r.h / 2, r.w + 6, r.h + 6, opts)
        : rc.rectangle(r.x, r.y, r.w, r.h, opts);
      svg.appendChild(shape);
    });
  }

  function annotate() {
    if (!window.RoughNotation) return;
    const { annotate } = RoughNotation;
    document.querySelectorAll('[data-an]').forEach((el) => {
      const a = annotate(el, {
        type: el.dataset.an, color: el.dataset.ac || '#F6C79B', animate: false,
        strokeWidth: +(el.dataset.aw || 2), padding: +(el.dataset.ap || 3), iterations: +(el.dataset.ai || 2), multiline: true,
        brackets: el.dataset.ab ? el.dataset.ab.split(',') : undefined,
      });
      a.show();
    });
  }

  async function main() {
    await document.fonts.ready;
    document.querySelectorAll('section.slide').forEach(drawBoxes);
    document.querySelectorAll('.dia').forEach(drawWires);
    annotate();
    window.__ready = true;
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => main().catch((e) => { console.error(e); window.__ready = true; }));
  else main().catch((e) => { console.error(e); window.__ready = true; });
})();
