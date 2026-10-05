"""Telephony / replay channel simulation, applied identically to bona fide and spoofed audio.

Channels (all return 16 kHz mono float32, RMS-normalised):
  clean     16 kHz, untouched apart from level normalisation
  pstn      300-3400 Hz band-limit, 8 kHz, ITU G.711 mu-law (audioop), back to 16 kHz
  amr       300-3400 Hz band-limit, 8 kHz, AMR-NB 12.2 kbps (MR122) via libopencore-amrnb (ctypes),
            fallback: sox amr-nb -C 7. Optional frame erasures.
  opus      WhatsApp-like: Opus 16 kHz wideband VOIP at 16-24 kbps, 20 ms frames, 1-5 % bursty
            packet loss concealed by the decoder's PLC (libopus via ctypes)
  replay    loudspeaker->mic: small-loudspeaker EQ (HPF/LPF/resonance) + mild nonlinearity +
            room impulse response (pyroomacoustics shoebox bank) + coloured noise at 10-25 dB SNR
Randomness comes from the rng argument so every (utterance, channel) pair is reproducible.
"""
import ctypes
import ctypes.util
import os
import subprocess
import tempfile
import warnings

import numpy as np
from scipy.signal import butter, sosfilt, lfilter, fftconvolve

from common.audio import resample, normalize_rms

SR = 16000
CHANNELS = ["clean", "pstn", "amr", "opus", "replay"]

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    try:
        import audioop  # stdlib up to 3.12: exact ITU G.711
    except Exception:  # pragma: no cover
        audioop = None


def _to_i16(x):
    return (np.clip(x, -1, 1) * 32767).astype(np.int16)


def _from_i16(x):
    return x.astype(np.float32) / 32768.0


def _telephone_band(x8, rng=None):
    lo = 300 if rng is None else float(rng.uniform(250, 350))
    hi = 3400 if rng is None else float(rng.uniform(3300, 3500))
    sos = butter(4, [lo, min(hi, 3900)], btype="bandpass", fs=8000, output="sos")
    return sosfilt(sos, x8).astype(np.float32)


def _pre_level(x, rng):
    """Speech level into the codec varies on real calls; keep it in a sane range."""
    return normalize_rms(x, target_db=float(rng.uniform(-30, -20)) if rng is not None else -26.0)


# ---------------------------------------------------------------- G.711 mu-law
def _mulaw_numpy(x):
    mu = 255.0
    y = np.sign(x) * np.log1p(mu * np.abs(x)) / np.log1p(mu)
    q = np.round((y + 1) / 2 * 255) / 255 * 2 - 1
    return (np.sign(q) * ((1 + mu) ** np.abs(q) - 1) / mu).astype(np.float32)


def pstn(x, rng):
    x8 = _telephone_band(resample(_pre_level(x, rng), SR, 8000), rng)
    if audioop is not None:
        b = _to_i16(x8).tobytes()
        y8 = _from_i16(np.frombuffer(audioop.ulaw2lin(audioop.lin2ulaw(b, 2), 2), dtype=np.int16))
    else:
        y8 = _mulaw_numpy(x8)
    return resample(y8, 8000, SR)


# ---------------------------------------------------------------- AMR-NB
_amr = None


def _load_amr():
    global _amr
    if _amr is None:
        name = ctypes.util.find_library("opencore-amrnb") or "libopencore-amrnb.so.0"
        lib = ctypes.CDLL(name)
        lib.Encoder_Interface_init.restype = ctypes.c_void_p
        lib.Encoder_Interface_init.argtypes = [ctypes.c_int]
        lib.Encoder_Interface_Encode.restype = ctypes.c_int
        lib.Encoder_Interface_Encode.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_short),
                                                 ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int]
        lib.Encoder_Interface_exit.argtypes = [ctypes.c_void_p]
        lib.Decoder_Interface_init.restype = ctypes.c_void_p
        lib.Decoder_Interface_Decode.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ubyte),
                                                 ctypes.POINTER(ctypes.c_short), ctypes.c_int]
        lib.Decoder_Interface_exit.argtypes = [ctypes.c_void_p]
        _amr = lib
    return _amr


def _amr_ctypes(x8, mode=7, frame_loss=0.0, rng=None):
    lib = _load_amr()
    pcm = _to_i16(x8)
    n = int(np.ceil(len(pcm) / 160)) * 160
    pcm = np.pad(pcm, (0, n - len(pcm)))
    enc = lib.Encoder_Interface_init(0)
    dec = lib.Decoder_Interface_init()
    out = np.zeros(n, dtype=np.int16)
    buf = (ctypes.c_ubyte * 64)()
    try:
        for i in range(0, n, 160):
            fr = np.ascontiguousarray(pcm[i:i + 160])
            nb = lib.Encoder_Interface_Encode(enc, mode, fr.ctypes.data_as(ctypes.POINTER(ctypes.c_short)), buf, 0)
            lost = frame_loss > 0 and rng is not None and rng.random() < frame_loss
            o = np.zeros(160, dtype=np.int16)
            lib.Decoder_Interface_Decode(dec, buf, o.ctypes.data_as(ctypes.POINTER(ctypes.c_short)), 1 if lost else 0)
            out[i:i + 160] = o
    finally:
        lib.Encoder_Interface_exit(enc)
        lib.Decoder_Interface_exit(dec)
    return _from_i16(out[:len(x8)])


def _amr_sox(x8):
    import soundfile as sf
    with tempfile.TemporaryDirectory() as d:
        a, b, c = (os.path.join(d, f) for f in ("in.wav", "x.amr", "out.wav"))
        sf.write(a, x8, 8000, subtype="PCM_16")
        subprocess.run(["sox", a, "-C", "7", b], check=True, capture_output=True)
        subprocess.run(["sox", b, "-r", "8000", "-b", "16", c], check=True, capture_output=True)
        y, _ = sf.read(c, dtype="float32")
    return y[:len(x8)]


def amr(x, rng, frame_loss=None):
    x8 = _telephone_band(resample(_pre_level(x, rng), SR, 8000), rng)
    fl = float(rng.choice([0.0, 0.0, 0.01, 0.02])) if frame_loss is None else frame_loss
    try:
        y8 = _amr_ctypes(x8, mode=7, frame_loss=fl, rng=rng)
    except OSError:
        y8 = _amr_sox(x8)
    return resample(y8, 8000, SR)


# ---------------------------------------------------------------- Opus
_opus = None


def _load_opus():
    global _opus
    if _opus is None:
        name = ctypes.util.find_library("opus") or "libopus.so.0"
        lib = ctypes.CDLL(name)
        lib.opus_encoder_create.restype = ctypes.c_void_p
        lib.opus_encoder_create.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
        lib.opus_encode.restype = ctypes.c_int
        lib.opus_encode.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_short), ctypes.c_int,
                                    ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int]
        lib.opus_encoder_ctl.restype = ctypes.c_int
        lib.opus_decoder_create.restype = ctypes.c_void_p
        lib.opus_decoder_create.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
        lib.opus_decode.restype = ctypes.c_int
        lib.opus_decode.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int,
                                    ctypes.POINTER(ctypes.c_short), ctypes.c_int, ctypes.c_int]
        lib.opus_encoder_destroy.argtypes = [ctypes.c_void_p]
        lib.opus_decoder_destroy.argtypes = [ctypes.c_void_p]
        _opus = lib
    return _opus


def opus(x, rng, bitrate=None, loss=None):
    lib = _load_opus()
    br = int(rng.choice([16000, 20000, 24000])) if bitrate is None else int(bitrate)
    p_loss = float(rng.uniform(0.01, 0.05)) if loss is None else float(loss)
    pcm = _to_i16(_pre_level(x, rng))
    F = 320  # 20 ms at 16 kHz
    n = int(np.ceil(len(pcm) / F)) * F
    pcm = np.pad(pcm, (0, n - len(pcm)))
    err = ctypes.c_int(0)
    enc = lib.opus_encoder_create(SR, 1, 2048, ctypes.byref(err))  # OPUS_APPLICATION_VOIP
    dec = lib.opus_decoder_create(SR, 1, ctypes.byref(err))
    ci = ctypes.c_int
    lib.opus_encoder_ctl(ctypes.c_void_p(enc), ci(4002), ci(br))            # SET_BITRATE
    lib.opus_encoder_ctl(ctypes.c_void_p(enc), ci(4008), ci(1103))          # SET_BANDWIDTH wideband
    lib.opus_encoder_ctl(ctypes.c_void_p(enc), ci(4014), ci(int(p_loss * 100)))  # SET_PACKET_LOSS_PERC
    buf = (ctypes.c_ubyte * 1500)()
    out = np.zeros(n, dtype=np.int16)
    prev_lost = False
    try:
        for i in range(0, n, F):
            fr = np.ascontiguousarray(pcm[i:i + F])
            nb = lib.opus_encode(enc, fr.ctypes.data_as(ctypes.POINTER(ctypes.c_short)), F, buf, 1500)
            # Gilbert-style bursty loss: higher chance to lose right after a loss
            lost = rng.random() < (0.35 if prev_lost else p_loss)
            prev_lost = lost
            o = np.zeros(F, dtype=np.int16)
            if lost or nb <= 0:
                lib.opus_decode(dec, None, 0, o.ctypes.data_as(ctypes.POINTER(ctypes.c_short)), F, 0)  # PLC
            else:
                lib.opus_decode(dec, buf, nb, o.ctypes.data_as(ctypes.POINTER(ctypes.c_short)), F, 0)
            out[i:i + F] = o
    finally:
        lib.opus_encoder_destroy(enc)
        lib.opus_decoder_destroy(dec)
    return _from_i16(out[:len(x)])


# ---------------------------------------------------------------- loudspeaker -> mic replay
_rir_bank = None


def _make_rir_bank(n=120, seed=1234):
    import pyroomacoustics as pra
    r = np.random.default_rng(seed)
    bank = []
    while len(bank) < n:
        dims = np.array([r.uniform(2.5, 6), r.uniform(2.5, 6), r.uniform(2.4, 3.2)])
        rt60 = r.uniform(0.15, 0.6)
        try:
            e_abs, max_order = pra.inverse_sabine(rt60, dims)
        except ValueError:
            continue
        room = pra.ShoeBox(dims, fs=SR, materials=pra.Material(e_abs), max_order=min(max_order, 12))
        src = np.array([r.uniform(0.5, dims[0] - 0.5), r.uniform(0.5, dims[1] - 0.5), r.uniform(0.8, 1.5)])
        d = r.uniform(0.2, 1.0)
        ang = r.uniform(0, 2 * np.pi)
        mic = src + np.array([d * np.cos(ang), d * np.sin(ang), r.uniform(-0.2, 0.2)])
        mic = np.clip(mic, 0.2, dims - 0.2)
        room.add_source(src)
        room.add_microphone(mic)
        room.compute_rir()
        h = np.asarray(room.rir[0][0], dtype=np.float32)[: int(0.8 * SR)]
        bank.append(h / (np.max(np.abs(h)) + 1e-9))
    return bank


def _rir(rng):
    global _rir_bank
    if _rir_bank is None:
        cache = os.path.join(os.path.dirname(__file__), "rir_bank.npz")
        if os.path.exists(cache):
            z = np.load(cache, allow_pickle=True)
            _rir_bank = list(z["bank"])
        else:
            _rir_bank = _make_rir_bank()
            try:
                np.savez(cache, bank=np.array(_rir_bank, dtype=object))
            except OSError:
                pass
    return _rir_bank[int(rng.integers(0, len(_rir_bank)))]


def _peaking(f0, gain_db, q, fs=SR):
    A = 10 ** (gain_db / 40)
    w = 2 * np.pi * f0 / fs
    alpha = np.sin(w) / (2 * q)
    b = [1 + alpha * A, -2 * np.cos(w), 1 - alpha * A]
    a = [1 + alpha / A, -2 * np.cos(w), 1 - alpha / A]
    return np.array(b) / a[0], np.array(a) / a[0]


def _coloured_noise(n, rng):
    """Pink/brown-ish noise via spectral shaping."""
    beta = float(rng.uniform(0.5, 1.8))
    f = np.fft.rfftfreq(n, 1 / SR)
    spec = (rng.normal(size=len(f)) + 1j * rng.normal(size=len(f))) / np.maximum(f, 20) ** (beta / 2)
    y = np.fft.irfft(spec, n).astype(np.float32)
    return y / (np.std(y) + 1e-9)


def replay(x, rng, snr_db=None):
    y = normalize_rms(x, -20)
    # small loudspeaker: weak bass, rolled-off top, a resonance, mild saturation
    y = sosfilt(butter(2, float(rng.uniform(150, 350)), btype="highpass", fs=SR, output="sos"), y)
    y = sosfilt(butter(4, float(rng.uniform(5000, 7500)), btype="lowpass", fs=SR, output="sos"), y)
    b, a = _peaking(float(rng.uniform(1500, 4000)), float(rng.uniform(3, 8)), float(rng.uniform(0.8, 2.0)))
    y = lfilter(b, a, y)
    drive = float(rng.uniform(1.0, 3.0))
    y = np.tanh(drive * y / (np.max(np.abs(y)) + 1e-9)) / np.tanh(drive)
    # room
    y = fftconvolve(y, _rir(rng))[: len(x)]
    # microphone noise at 10-25 dB SNR + mic high-pass
    snr = float(rng.uniform(10, 25)) if snr_db is None else snr_db
    nz = _coloured_noise(len(y), rng)
    p_s = np.mean(y ** 2) + 1e-12
    y = y + nz * np.sqrt(p_s / (10 ** (snr / 10)))
    y = sosfilt(butter(2, 80, btype="highpass", fs=SR, output="sos"), y)
    return y.astype(np.float32)


def clean(x, rng):
    return x.astype(np.float32)


FUNCS = {"clean": clean, "pstn": pstn, "amr": amr, "opus": opus, "replay": replay}


def apply(x, channel, rng, target_db=-26.0):
    y = FUNCS[channel](np.asarray(x, dtype=np.float32), rng)
    return normalize_rms(y, target_db)


def seeded_rng(key: str, channel: str, base_seed: int = 7):
    import hashlib
    h = int(hashlib.md5(f"{base_seed}|{key}|{channel}".encode()).hexdigest()[:12], 16)
    return np.random.default_rng(h)
