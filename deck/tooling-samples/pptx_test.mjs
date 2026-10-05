// Editable-PPTX escape hatch: native text boxes + our SVG diagram as an (SVG) image.
import pptxgen from 'pptxgenjs';
const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE'; // 13.333 x 7.5 in = our 1280x720 px
const s = pptx.addSlide();
s.background = { color: 'F6F1E7' };
s.addText('System architecture', { x: 0.55, y: 0.35, w: 9, h: 0.7, fontFace: 'Space Grotesk', fontSize: 30, bold: true, color: '1B1F24' });
s.addText('Raw audio never leaves the bank edge', { x: 0.55, y: 1.0, w: 9, h: 0.4, fontFace: 'Inter', fontSize: 14, color: '5A6270' });
s.addImage({ path: 'svg/elk_clean.svg', x: 0.4, y: 1.8, w: 12.5, h: 12.5 * 368 / 1462 });
s.addShape(pptx.ShapeType.roundRect, { x: 0.55, y: 6.4, w: 3.2, h: 0.6, fill: { color: 'E8772E' }, rectRadius: 0.1, line: { color: 'E8772E' } });
s.addText('native, editable shape', { x: 0.55, y: 6.4, w: 3.2, h: 0.6, align: 'center', fontFace: 'Inter', fontSize: 14, color: 'FFFFFF' });
await pptx.writeFile({ fileName: 'out/pptx_test.pptx' });
console.log('pptx ok');
