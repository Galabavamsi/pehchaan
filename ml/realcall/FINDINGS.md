# Real-call findings (2026-10-17)

The served Round 1 detector (`pehchaan-xlsr-aasist-ft-v1`) was scored on consented tape calls over a real
Indian network: Vobiz number → Jio → Samsung M34 (D1) on speakerphone → laptop mic. Each tape mixes ~10 s
genuine items (S01, S02 team recordings) with content-matched clones of the same lines (XTTS-v2, F5,
F5-Hindi, CosyVoice2, Chatterbox, Seed-VC). Raw `p_synthetic` is reported because the service's quality gate
withholds most verdicts (see below). Nothing here has been trained on: this is the "before" measurement.

| Batch | Set-up | Calls | Items | QC ok | Median SNR | Genuine flagged (p ≥ 0.8) | Clones caught (p ≥ 0.8) | EER |
|---|---|---|---|---|---|---|---|---|
| B1 | phone at arm's length, quiet, items 3–9 s then ~10 s | 10 | 98 | 74 % | 14.8 dB | 3 % | 29 % | 34.2 % |
| B2 | phone 5 cm from mic, noisy room | 10 | 100 | 95 % | 25.4 dB | 4 % | 28 % | 27.4 % |
| B3 | 5 cm, quiet, hands-free (adb answer + speaker) | 21 | 210 | 100 % | 26.2 dB | **0 %** | **28 %** | **24.8 %** |
| All | | 41 | 378 QC-ok | | | | | 29.1 % |

Same detector on simulated channels: 4.8 % EER (Round 1). Two consented speakers, one handset, one carrier.

## What it means

1. **On real lines the problem is missed clones, not false alarms.** Genuine speech stayed at median
   p ≈ 0.001 for both speakers (0 of 105 flagged in B3). Clones drift towards "real": median p 0.31 and only
   28 % above 0.8. By generator (B3): Seed-VC 40 %, F5-Hindi 36 %, XTTS 28 %, CosyVoice2 25 %, F5 24 %,
   Chatterbox 18 %.
2. This differs from Round 1's single real call (genuine flagged 91–95 %). That was a dialer recording of
   two people talking; this is the speakerphone path the product actually uses. Both say the same thing:
   simulated codecs don't predict real-network behaviour.
3. **The service's quality gate (≥ 4 s speech, ≥ 10 dB SNR by Silero VAD) passes only 29 of 210 B3 clips**,
   even at 26 dB energy SNR. Silero under-detects narrowband speakerphone speech. Either the gate needs
   recalibrating on real captures, or the capture path needs to be closer (an in-app capture, not a laptop).
4. Capture matters as much as the model: arm's length cost about 10 dB of SNR and 9 EER points.

This supports the core design: voice stays a supporting clue (shadow mode, G2), and the decision rests on
verifying the person out of band.

## Method notes

- Alignment: start and end chirps by matched filter, drift-corrected; items placed by log-energy envelope
  correlation (median NCC ≈ 0.76). If speaker came on late and only one chirp is heard, ingest infers which
  one it was. The answer XML now waits 6 s before playing.
- QC: speech seconds and SNR are measured against the noise floor of the silent gaps between items.
- Dialer recordings: none. Samsung's auto-record never produced files on this phone
  (`settings system record_calls_automatically_on_off` stays 0).
- Splits are pre-registered (`protocol.py`): S02 and `sarvam_ivc` are test-only, everything else by call hash.
  Current QC-ok split: train 112, dev 30, test 236 items.
