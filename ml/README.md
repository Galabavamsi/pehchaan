# Pehchaan ML: voice-clone detector, red-team corpus and Voice Provenance Service

> Written for Round 1 (6 Oct 2026). Added since: real-call collection and retraining (`realcall/`, `realcall/FINDINGS.md`), the side-by-side detector panel (`serve/panel.py`) and the reference detector n3 (FINDINGS, v5 section).

What this folder proves, with measurements: off-the-shelf anti-spoofing models degrade on Indian-language,
phone-channel cloned speech; our fine-tuned XLS-R + AASIST does better but still misses unseen generators.
That is why the product treats voice as supporting evidence (SPEC section 4, G2/G3).
Results: `results/metrics.json`, `results/SUMMARY.md`, figures in `results/figures/`.
Licences of everything used: `DATA_CARD.md` (non-commercial items are flagged **NC**).

## Layout

| Path | What |
|---|---|
| `infra/` | AWS bootstrap (`user_data.sh`: idle watchdog + scratch disk), per-generator envs (`setup_envs.sh`), SSH config, code sync |
| `common/` | audio helpers, recording-kit script lines (`lines.py`), the fixed evaluation protocol (`protocol.py`) |
| `channel/channels.py` | clean / PSTN G.711 / AMR-NB 12.2k / Opus 16-24k + packet loss / loudspeaker->mic replay |
| `gen/` | one runner per generator (`run_*.py`, common JSONL job format) + job builders |
| `data_prep/` | public data manifests, team-recording segmentation + alignment, corpus assembly, Whisper QC |
| `models/` | XLS-R+AASIST ported to transformers (fairseq-free), NII AntiDeepfake port, detector wrappers |
| `train/finetune.py` | fine-tuning with on-the-fly channel augmentation + RawBoost |
| `eval/` | scoring, metrics (EER, FRR@FAR, AUC, ECE), calibration + bands + LRs, figures, latency |
| `serve/` | FastAPI `POST /v1/voice/score` (SPEC section 7) |

## Reproduce

1. **Box.** Launch template `pehchaan-ml` (DLAMI PyTorch, IMDSv2, stop-on-shutdown, 45-min idle watchdog).
   `bash infra/sync_up.sh` pushes code; on the box `bash setup_envs.sh all` builds the uv envs
   (`det`, `f5`, `xtts`, `chatterbox`, `seedvc`, `cosy`, `misc`).
2. **Public data.** `infra/dl_fleurs.sh`; ASVspoof 2019 LA from Edinburgh DataShare; IndicSynth shards
   (`data_prep/extract_indicsynth.py`); then `python data_prep/build_public.py`.
3. **Baselines' weights.** SSL_Anti-spoofing `LA_model.pth` / `Best_LA_model_for_DF.pth` (Google Drive, via `gdown`)
   into `~/weights/ssl_aasist/`; NII `mms-300m-anti-deepfake` downloads from HF.
   Sanity check (in-domain, ASVspoof 2019 LA eval subset): `python eval/score.py ... --detector ssl_la`.
4. **SynRef corpus** (synthetic stock voices as references, nobody real is cloned):
   `python gen/make_synref.py --stage refs|stock|clone` and the matching `gen/run_*.py --jobs ...`.
5. **Commercial stock voices** (laptop; keys from `.env`, never printed):
   `python ml/gen/run_api.py build --fleurs <fleurs.csv>` then `run --jobs data/generated/api/jobs_<engine>.jsonl`.
6. **Team recordings** (consent checked per speaker): copy `data/raw/recordings/*` to `~/work/team_raw/`,
   `python data_prep/segment_team.py`, `python gen/make_team_jobs.py --speakers S01 S02`, run the generators.
7. **Corpus + channels.** `python data_prep/asr_qc.py --jobs <jobs> --out ~/work/qc/<name>.csv` (drops broken clones),
   then `python data_prep/build_corpus.py` (dev/test pre-rendered through all 5 channels).
8. **Zero-shot baselines.** `bash eval/score_all.sh ssl_la ssl_df nii_mms300m`.
9. **Fine-tune.** `python train/finetune.py --src_manifest ~/work/manifests/corpus_src.csv --eval_manifest ~/work/manifests/corpus_eval.csv --out ~/runs/ours`
   then `bash eval/score_all.sh ckpt:$HOME/runs/ours/best.pt`.
10. **Evaluate.** `bash eval/final.sh` on the box (run_eval -> assemble_metrics -> write_summary; needs the score CSVs,
    `eval/latency.py` outputs, `eval/watermark_eval.py` and `eval/asv_sanity.py` JSONs in `~/work/results/`).
    Figures (laptop or box): `python eval/make_figures.py --metrics results/metrics.json --scores test_scores.csv --out results/figures`;
    spectrograms: `python eval/spectrograms.py --speaker S01 --lines E06 H05 E12 --channels clean amr --out results/figures`.
11. **Export + serve.** `python eval/export_serving.py --ckpt ~/runs/ours_v1/best.pt --metrics metrics.json --name ours --version pehchaan-xlsr-aasist-ft-v1 --out_dir serve`
    (also in `s3://pehchaan-ml-301745146083-use1/models/pehchaan-xlsr-aasist-ft-v1/`). Then `cd ml && uvicorn serve.app:app --port 8090`
    (`PEHCHAAN_DEVICE=cpu|cuda`; CPU uses int8 dynamic quantisation) and `curl -F file=@clip.wav localhost:8090/v1/voice/score`.
    Latency of the full service path: `python serve/bench.py --wav clip_10s.wav --out latency.json`.

Runs reported in `results/metrics.json`: `ours` = v1 (main, served); `ours_v2_telaug` = `--aug_set v2` (extra telephony
augmentation, designed after the real-call failure, stopped by OOM at epoch 3 of 6); `ours_v0_noteam` = no team audio.

## Protocol (fixed before fine-tuning; see `common/protocol.py`)

- Held-out generators (never trained on, never used for calibration or thresholds): **Seed-VC** (voice conversion),
  **Chatterbox** (also watermarked, so the model cannot learn the watermark), **Sarvam, OpenAI, Deepgram** (commercial),
  plus **Indic Parler-TTS** (added later, test only).
- Held-out speaker: **S02**. S01 lines 01-08 train, 09-10 dev, 11-15 test; real and cloned versions of a line share a split.
- Same silence trimming and loudness normalisation for real and fake audio; channels applied identically to both.
- Clones whose Whisper transcript misses the intended text (CER > 0.5) are dropped rather than counted as easy catches.

## Ethics

Only consenting team members are cloned (a consent scan must exist per speaker). Public datasets are used only
as bona fide audio or as already-published spoof data. Commercial APIs are used with stock voices only. No audio,
weights or keys are committed. Cloned audio stays in the private, encrypted bucket and is deleted by 31 Dec 2026.
