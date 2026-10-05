// Speakerphone capture -> 16 kHz mono PCM16 WAV (what /v1/voice/score expects).
export async function recordWav(seconds: number, onTick?: (s: number) => void): Promise<Blob> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false } });
  const rec = new MediaRecorder(stream);
  const chunks: BlobPart[] = [];
  rec.ondataavailable = (e) => chunks.push(e.data);
  const done = new Promise<void>((res) => (rec.onstop = () => res()));
  rec.start();
  for (let i = 0; i < seconds; i++) { onTick?.(seconds - i); await new Promise((r) => setTimeout(r, 1000)); }
  rec.stop();
  await done;
  stream.getTracks().forEach((t) => t.stop());
  const buf = await new Blob(chunks).arrayBuffer();
  const ctx = new OfflineAudioContext(1, 16000 * seconds, 16000);
  const decoded = await ctx.decodeAudioData(buf);
  const src = ctx.createBufferSource();
  src.buffer = decoded;
  src.connect(ctx.destination);
  src.start();
  const out = await ctx.startRendering();
  return encodeWav(out.getChannelData(0), 16000);
}

export function encodeWav(samples: Float32Array, sr: number): Blob {
  const b = new ArrayBuffer(44 + samples.length * 2);
  const v = new DataView(b);
  const w = (o: number, s: string) => [...s].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)));
  w(0, "RIFF"); v.setUint32(4, 36 + samples.length * 2, true); w(8, "WAVE"); w(12, "fmt ");
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true); v.setUint32(24, sr, true);
  v.setUint32(28, sr * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true); w(36, "data");
  v.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) v.setInt16(44 + i * 2, Math.max(-1, Math.min(1, samples[i])) * 0x7fff, true);
  return new Blob([b], { type: "audio/wav" });
}
