# Audio deepfake / voice-clone detection that generalises to unseen generators and real telephony (2025–2026): what a 2-person team can use on one A10G in ~1.5 days

Scope note: research pass done 24 Oct 2026. Most sources are arXiv preprints (2025–Oct 2026); venue is given only where the source states it. Items before 2025 are marked "(background)". Numbers are copied as published, with their test set. "EER" = equal error rate. Pehchaan context used for the inferences: XLS-R-300M + AASIST (TakHemlata LA init), Indic corpus with simulated PSTN/AMR-NB/Opus/speaker-to-mic channels, real Jio call clips, learned speakerphone channel; NII MMS-300M AntiDeepfake is already ported in `ml/models/nii_antideepfake.py` and reported in `ml/results/SUMMARY.md`.

## 1. Which SSL front-ends and back-ends lead on generalisation in 2025–2026, and which have public weights?

### Takeaway
The front-end and the training recipe matter far more than the back-end. Large multilingual SSL encoders lead: w2v-BERT 2.0 (MIT, 580M) is the strongest published encoder on the 14-set Speech-DF-Arena when trained with a strong recipe, and XLS-R (128 languages) beats both narrower and broader (MMS 1406-language) encoders out of domain at matched size. The only strong, *deepfake-post-trained* public weights are NII AntiDeepfake (7 checkpoints, CC BY-NC-SA 4.0) and DF Arena 500M/1B (non-commercial). New back-ends (Nes2Net, Mamba variants, MoE, Branchformer) give small In-the-Wild gains: about 5.5–6.9 % EER versus 7.46 % for XLSR-SLS, all trained on ASVspoof 2019 LA.

### Cited Findings
**Leaderboards and encoder comparisons**
- Speech-DF-Arena (14 test sets; ranking by pooled EER) public snapshot reported in the Teffic-Audio report (Amphion, arXiv tech report, v2 14 Aug 2026):
  - Teffic-Audio (w2v-BERT 2.0 encoder + multi-head attentive statistics pooling (MHASP), 590.0M, **licence "Proprietary"**) 1.454 % pooled.
  - Modulate-VELMA-2 (316M, proprietary) 1.586 %.
  - Resemble-Detect-3B-Omni (3B, proprietary) 2.099 %.
  - Hiya-Authenticity-Verification-Multi-v1 (1B, proprietary) 2.324 %.
  - DF_Arena_1B_V_1 (1B, open) 9.524 %; DF_Arena_500M_V_1 (500M, open) 10.880 %.
  - XLSR+SLS (340M, open) 16.079 %; TCM (319M, open) 16.691 %; BiCrossMamba-ST (318.2M, open) 17.154 %.
  - MoLEx (376.4M) 12.405 %.
  - — [Teffic-Audio, arXiv 2607.28351](https://arxiv.org/abs/2607.28351)
- Same report, fixed training recipe, swapping only the encoder (pooled EER on Speech-DF-Arena):
  - AASIST (0.3M) 15.668 %; Res2Net+MHASP 15.023 %.
  - WavLM Base+MHASP 9.446 %; WavLM Large+MHASP 4.332 %.
  - XLS-R 300M+MHASP 6.079 %; XLS-R 1B+MHASP 4.419 %.
  - w2v-BERT 2.0+MHASP 1.454 %.
  - The authors conclude performance "is not determined solely by parameter size" but by the pretraining objective. — [Teffic-Audio](https://arxiv.org/abs/2607.28351)
- Same report, truncating the w2v-BERT 2.0 encoder to its first N Conformer blocks (pooled EER):
  - N=3 (82.2M) 4.735 %; N=4 (106.4M) 3.346 %; N=6 (154.8M) 2.839 %; N=12 (299.9M) 2.317 %; full 24 layers 1.454 %.
  - Pooling: mean pooling 2.269 % and ASP 2.339 % against MHASP 1.454 %. — [Teffic-Audio](https://arxiv.org/abs/2607.28351)
- w2v-BERT 2.0 on Hugging Face: MIT licence, 580,493,120 parameters, language tags include hi, te, ta, bn, mr, kn, ml, gu, pa, ur. — [facebook/w2v-bert-2.0 model card](https://huggingface.co/facebook/w2v-bert-2.0)
- Controlled study of frozen ~315M wav2vec2-family encoders, MHFA back-end, ASVspoof 2019 LA training (Sep 2026; In-the-Wild (ITW) / ASVspoof 5 EER):
  - wav2vec2-LV60 (1 language) 46.77 / 41.88.
  - XLSR-53 (53 languages) 38.97 / 25.40.
  - XLS-R (128 languages) 18.30 / 21.18.
  - MMS-300M (1406 languages) 22.71 / 24.36.
  - "Coverage does not help monotonically." Masked prediction beats contrastive on identical data (HuBERT ITW 26.54 vs wav2vec2 46.77).
  - XLS-R had the best ASVspoof 5 min-DCF under both back-ends (0.56 MHFA, 0.49 AASIST). XLS-R per-seed ASV5 EER spans 15.0–32.9, which shows how much single-seed results vary. — [Is Broader Better?, arXiv 2609.29138](https://arxiv.org/abs/2609.29138)
- Spoof-SUPERB (20 SSL models): "large-scale discriminative models such as XLS-R, UniSpeech-SAT, and WavLM Large consistently outperform other models." — [arXiv 2603.01482](https://arxiv.org/abs/2603.01482)
- DeepFense toolkit, 400+ models: "the choice of pre-trained front-end feature extractor dominates overall performance variance"; it also reports severe biases by audio quality, speaker gender and language. — [arXiv 2604.08450](https://arxiv.org/abs/2604.08450)
- Lower SSL layers are the most discriminative, and competitive EER holds with fewer layers. — [Layer-wise analysis, arXiv 2502.03559](https://arxiv.org/abs/2502.03559)
- Selecting the best single layer or using MHFA layer pooling improves out-of-domain results for frozen SSL. — [arXiv 2509.12003](https://arxiv.org/abs/2509.12003)
- In an audio-visual pipeline, six-layer wav2vec 2.0 execution improved detection and cut latency against full depth. — [arXiv 2610.24138](https://arxiv.org/abs/2610.24138)

**NII AntiDeepfake (post-training family)**
- Post-training on 56k h genuine + 18k h artefact speech in 100+ languages. Data includes ASVspoof 2019/2021/5, MLAAD, CodecFake, SpoofCeleb, FLEURS/FLEURS-R, VoxCeleb2-Vocoded and LibriTTS-Vocoded. Post-trained on 8×H100, CE loss, RawBoost (Ge, Wang, Liu, Yamagishi, NII; arXiv 2506.21090, v4 21 Oct 2025). Zero-shot EER, with RawBoost / without:
  - In-the-Wild: XLS-R-2B 1.23 / 1.31; XLS-R-1B 1.35 / 1.36; MMS-300M 2.90 / 2.00; W2V-Large 1.91 / 2.25.
  - Deepfake-Eval-2024: XLS-R-1B 26.76 / 26.17; MMS-300M 32.84 / 31.39.
  - Literature zero-shot ITW for comparison: XLSR-Mamba 6.70, XLS-R+SLS 7.45, XLSR-Conformer+TCM 7.79, Resemble AI (2.1B) 3.94. — [Post-training for Deepfake Speech Detection, arXiv 2506.21090](https://arxiv.org/abs/2506.21090)
- Fine-tuned on Deepfake-Eval-2024 (6k steps, AdamW lr 1e-6, RawBoost). EER at 4 s / 10 s / 50 s inputs, with post-training against without:
  - XLS-R-1B 11.86 / 10.00 / 8.28 against 19.96 / 17.19 / 11.20.
  - MMS-1B 12.11 / 10.40 / 9.35 against 19.85 / 13.57 / 11.40.
  - MMS-300M 17.15 / 13.38 / 10.79 against 19.77 / 13.26 / 12.30.
  - References at 4 s: P3 15.38, AASIST 16.99, RawNet2 20.91.
  - "The benefits of post-training were most pronounced for shorter durations (4s and 10s)." — [arXiv 2506.21090](https://arxiv.org/abs/2506.21090)
- Weights: XLS-R-2B, XLS-R-1B, MMS-1B, MMS-300M, Wav2Vec2-Large, Wav2Vec2-Small and HuBERT-XL, each with and without augmentation.
  - Back-end is mean pool + FC; input 16 kHz.
  - Code at github.com/nii-yamagishilab/AntiDeepfake.
  - Licence **CC BY-NC-SA 4.0** ("research and educational purposes"). — [HF card xls-r-1b-anti-deepfake](https://huggingface.co/nii-yamagishilab/xls-r-1b-anti-deepfake); [HF card mms-300m-anti-deepfake](https://huggingface.co/nii-yamagishilab/mms-300m-anti-deepfake); [NII HF org](https://huggingface.co/nii-yamagishilab)
- NII SLT 2026 checkpoints (XLS-R-300M+FC, Whisper-large-v2+FC, Qwen2-Audio-7B+LoRA) were trained for CompSpoof V2 speech+event mixtures. Licence CC BY-NC 4.0. — [HF card slt2026-checkpoints](https://huggingface.co/nii-yamagishilab/slt2026-checkpoints)

**DF Arena checkpoints**
- DF_Arena_1B_V_1 (Idiap/Speech-Arena):
  - Trained on ASVspoof 2019/2024, Codecfake, LibriSeVoc, DFADD, CtrSVDD, SpoofCeleb, MLAAD and EnvSDD.
  - Card EER: in_the_wild 0.91 %, asvspoof_2024 17.25 %, codecfake 8.37 %, add_2022_track_1 22.21 %; pooled 9.52 %.
  - transformers pipeline with `trust_remote_code`. **Non-commercial licence** ("other"). — [HF card DF_Arena_1B_V_1](https://huggingface.co/Speech-Arena-2025/DF_Arena_1B_V_1); [DF_Arena_500M_V_1 metadata](https://huggingface.co/Speech-Arena-2025/DF_Arena_500M_V_1)
- RAPTOR (Idiap, cited as the DF Arena paper): "multilingual HuBERT pre-training is the primary driver of cross-domain robustness, enabling 100M models to match larger and commercial systems". It adds a perturbation-based test-time-augmentation uncertainty protocol. — [arXiv 2603.06164](https://arxiv.org/abs/2603.06164)

**Back-ends trained on ASVspoof 2019 LA (In-the-Wild EER)**
- Nes2Net / Nes2Net-X (Apr 2025), with the wav2vec 2.0 front-end:
  - ITW 5.80 (mean 7.06) and 5.52 (mean 6.60). Table entries: XLSR-Mamba 6.71, SLS 7.46 (mean 8.87), TCM 7.79, LSR+LSA 5.92.
  - ASVspoof 2021 DF: Nes2Net-X 1.65 (mean 1.91) against AASIST 2.85 (mean 3.69).
  - ASVspoof 5 with a WavLM front-end: Nes2Net-X EER 5.92 against AASIST 6.08; back-end MMACs 91.35 against 707.65.
  - Code and pretrained models at github.com/Liu-Tianchi/Nes2Net. Code links in the same table: XLSR-Mamba github.com/swagshaw/XLSR-Mamba; SLS github.com/QiShanZhang/SLSforASVspoof-2021-DF; TCM github.com/ductuantruong/tcm_add; SSL-AASIST github.com/TakHemlata/SSL_Anti-spoofing. — [Nes2Net, arXiv 2504.05657](https://arxiv.org/abs/2504.05657)
- Other back-ends (ASVspoof 2021 LA / DF / ITW EER):
  - Fake-Mamba (XLSR + bidirectional Mamba): 0.97 / 1.74 / 5.85 %; code github.com/xuanxixi/Fake-Mamba. — [arXiv 2508.09294](https://arxiv.org/abs/2508.09294)
  - E-Branchformer: 0.88 / 1.85 / 6.30 %. — [arXiv 2609.08948](https://arxiv.org/abs/2609.08948)
  - FGFM: 0.90 / 1.88 / 6.64 %. — [arXiv 2602.04702](https://arxiv.org/abs/2602.04702)
  - HierCon (DF21 / ITW only): 1.93 / 6.87 %. — [arXiv 2602.01032](https://arxiv.org/abs/2602.01032)
  - XLSR-MamBo (hybrid Mamba-attention scaling) is another 2026 option. — [arXiv 2601.02944](https://arxiv.org/abs/2601.02944)
- SpAArSIST (sparsified AASIST): In-the-Wild 2.82 % EER and 0.078 minDCF, against 4.64 % and 0.133 for the baseline. Back-end compute falls 20.7 %. — [arXiv 2606.11674](https://arxiv.org/abs/2606.11674)

**Mixture-of-experts and parameter-efficient adaptation**
- MoE converted from SSL feed-forward blocks: macro EER over 14 sets 5.46 % → 4.81 %. — [arXiv 2606.14639](https://arxiv.org/abs/2606.14639)
- Mixture of LoRA experts: average out-of-domain EER 8.55 % → 6.08 %. — [arXiv 2509.13878](https://arxiv.org/abs/2509.13878)
- MoLEx is LoRA+MoE PEFT. — [arXiv 2509.09175](https://arxiv.org/abs/2509.09175)
- DADGMoE: up to 40.8 % relative EER reduction out of dataset. — [arXiv 2609.33709](https://arxiv.org/abs/2609.33709)
- Wav2DF-TSL (adapter pre-training on 3000 h spoofed speech + hierarchical MoE): 27.5 % relative EER improvement on In-the-Wild. — [arXiv 2509.04161](https://arxiv.org/abs/2509.04161)
- MultiConvAdapter (3.17M trainable params) beats full fine-tuning on five datasets. — [arXiv 2510.24852](https://arxiv.org/abs/2510.24852)

**Single-model ASVspoof 5 results**
- Reference-Augmented Training: 2.57 % EER, 0.074 minDCF. — [RAT, arXiv 2606.10908](https://arxiv.org/abs/2606.10908)
- Supervised mix-frame post-training of an SSL model: 4.50 % EER without data augmentation. — [arXiv 2606.25328](https://arxiv.org/abs/2606.25328)
- Frozen W2V-BERT 2.0 + hybrid Wavelet Prompt Tuning (~7M trainable params): 3.60 % CM-EER using only provided data. — [arXiv 2610.08845](https://arxiv.org/abs/2610.08845)
- ArA-DF 2026 (Arabic) shared task: frozen W2V-BERT-2.0 + Wavelet Prompt Tuning (<1 % of params) with an ensemble. Track 1 (dialect) 1.96 % EER; Track 2 (acoustic robustness) 1.04 % EER, using "a compact, channel-matched, center-crop ensemble" for acoustic shift. — [UZH-CL, arXiv 2610.08844](https://arxiv.org/abs/2610.08844)

### Inferences
- The highest-value swap for Pehchaan is the *initial weights*, not the back-end. The candidates are AntiDeepfake MMS-300M / XLS-R-1B (post-trained on 18k h of artefacts, including MLAAD and FLEURS-R across 100+ languages) in place of the TakHemlata LA checkpoint, or w2v-BERT 2.0 (MIT) as the commercial-licence path.
- The team's own `ml/results/SUMMARY.md` records NII MMS-300M at 10.3 % EER against Pehchaan's 16.6 % on held-out speaker S02. That fits the published result that post-training mostly helps on unseen conditions.
- Back-end swaps are second order. Published ITW gains from Nes2Net, Mamba and Branchformer are about 1–2 EER points over SLS or AASIST, all on English ASVspoof 2019 LA training. None was shown on telephony or Indic data.
- A10G feasibility (my estimate, not from a source):
  - 300M-class encoders (XLS-R-300M, MMS-300M AntiDeepfake, WavLM-L) fine-tune comfortably in bf16 with 4 s crops.
  - XLS-R-1B (≈965M) full fine-tuning with AdamW needs ≈15 GB of weights and optimiser state before activations. It is borderline on 24 GB; use gradient checkpointing with batch 2–4, or LoRA.
  - w2v-BERT 2.0 (580M) full fine-tuning is feasible with checkpointing. A frozen encoder with a prompt or LoRA (as UZH-CL did) is safer.
- Licences:
  - AntiDeepfake (CC BY-NC-SA), DF Arena (non-commercial) and the NII SLT checkpoints (CC BY-NC) suit a hackathon demo, not a bank product.
  - w2v-BERT 2.0 (MIT) is the clean commercial path among the encoders checked.

### Gaps
- AASIST3 numbers were not retrieved directly. SEA-Spoof reports AASIST3 at 34 % EER on ASVspoof 5 (see Q4).
- XLSR-SLS, XLSR-Mamba and Nes2Net weight licences were not checked.
- The XLS-R base checkpoint licence was not verified in this pass.
- Teffic-Audio is "Proprietary", so the best-ranked recipe has no public weights.
- None of the leaderboard models report numbers on real telephony other than RealComm (Q2).

## 2. Which training recipes most improve robustness to unseen commercial cloners and real phone channels?

### Takeaway
Data realism and diversity beat clever losses:
- **Presented / real-call audio**: inject and play TTS through real phones.
- **Diverse augmentation** beyond RawBoost.
- **More and more varied bona fide speech**.
- **Balanced sampling** across attacks and sources.

Simulated channel augmentation and real-call training are complementary, and combining them was best for every detector in RealComm. Auxiliary losses (contrastive, consistency, adversarial/GRL) did not beat plain cross-entropy across seeds in a 113-run study. SAM helps weak models but adds little to XLS-R. Ensembling and score fusion are a cheap, consistent win.

### Cited Findings
**Real-call presentation and telephony**
- "On Deepfake Voice Detection – It's All in the Presentation" (arXiv 2509.26471, v2 13 Mar 2026; ethics statement refers to Microsoft-internal data):
  - Training categories:
    - "Base": ASVspoof 2019/5, plus Switchboard and MLS voices cloned with ElevenLabs, Play.ht, OpenAI Voice Engine, Mars5 and YourTTS.
    - "Presented": the same clips injected (Bluetooth or wired) or loudspeaker-played into real phone calls on a Samsung Galaxy A12 and a Redmi Note 8 Pro; ~70k samples.
    - "Augmented": bona fide speech passed through HiFi-GAN, WaveGrad, WaveNet, EnCodec and Vocos.
  - Real-world test "Fraud Academy": 80 participants, ≥16 calling devices, 5 loudspeaker types, 10 TTS engines, 2,263 call segments; fully held out.
  - All systems run at **8 kHz with VAD**. Metric: missed-detection rate at 1 % false alarm.
  - Reported gains: "improved deepfake detection accuracy by 39% in more robust and realistic lab setups, and by 57% on a real-world benchmark". Adding presentation realism "appears to be more impactful than other, larger-scale augmentation techniques".
  - Best system WavLM-LLGF: 88.2 % detection (Realworld/injection) and 76.3 % (Realworld/playback) at FAR = 1 %. A 3.55M-param logmel-ResNet-CoT with full augmentation was "highly competitive" and best on injection (89.4 %).
  - WavLM-LLGF Base-set pooled EER: 7.1 (Base training) → 4.8 (Base+Presented+Augmented). — [arXiv 2509.26471](https://arxiv.org/abs/2509.26471)
- RealComm (CUHK-Shenzhen/Amphion with Huawei; arXiv 2610.27459, 20 Oct 2026; an earlier version is stated as accepted at IEEE SLT):
  - Paired digital and real-mobile-call recordings across over-the-air handset, over-the-air speakerphone and line-to-mic injection, with phone denoising on, off or unavailable.
  - Devices: Mate70 Pro, iPhone, Samsung, Oppo and Vivo. The test ring holds out Vivo; train/dev holds out Oppo.
  - "Experiments with existing detectors reveal substantial degradation after call transmission, even for models with strong digital-domain performance; acoustic injection is particularly challenging."
  - "Quality degradation is associated with poorer detection... while high-frequency attenuation alone does not explain detection difficulty."
  - "Simulated augmentation and real-call training provide complementary benefits, with their combination achieving the lowest call-domain error for each of three evaluated detectors. For Teffic-Audio, the equal error rate decreases from 37.94% to 22.37%."
  - Detectors compared include XLSR-SLS, the released DF Arena model and Teffic-Audio. RealComm-Aug orders acoustic, device, coding and transmission perturbations along the signal path. Repo github.com/AmphionTeam/RealComm; paper licence CC BY-NC-SA 4.0. — [RealComm, arXiv 2610.27459](https://arxiv.org/abs/2610.27459)
- RTCFake: ~600 h of speech sent through social-media and conferencing platforms (e.g. Zoom), paired offline/online. The test set has unseen platforms and noise. A phoneme-guided consistency strategy improves cross-platform generalisation. Dataset at huggingface.co/datasets/JunXueTech/RTCFake. — [arXiv 2604.23742](https://arxiv.org/abs/2604.23742)
- ADD-C (EUSIPCO 2025): codec × packet-loss benchmark; baseline detectors decline significantly; proposes a communication-oriented augmentation. — [arXiv 2504.12423](https://arxiv.org/abs/2504.12423)
- Acoustic front-end processing (echo cancellation, noise suppression, AGC, VAD) "significantly degrade[s] detection performance". TFCL consistency learning mitigates it; code github.com/JunXue-tech/TFCL. — [arXiv 2607.17761](https://arxiv.org/abs/2607.17761)
- EchoFake: models trained on existing datasets drop to 59.6 % average accuracy on physically replayed audio. — [arXiv 2510.19414](https://arxiv.org/abs/2510.19414)
- Corruption study, 10 detectors × 18 corruptions: most models are robust to noise but "vulnerable to audio modifications and compression, especially neural codecs". Foundation models are more robust, with diminishing returns from size. — [arXiv 2503.17577](https://arxiv.org/abs/2503.17577)
- Low-bitrate neural codecs (DAC, EnCodec) "mainly degrade bona fide detection", i.e. they raise false alarms on genuine speech. — [FP-NAC, arXiv 2609.39651](https://arxiv.org/abs/2609.39651)
- Legitimately codec-compressed bona fide is "often misclassified as fake". Pairwise-consistency fine-tuning of XLS-R-300M (PCL-NET) cuts average EER under neural-codec compression from 28.67 % to 12.77 %. — [arXiv 2610.07216](https://arxiv.org/abs/2610.07216)

**Training recipe (data, sampling, augmentation)**
- Teffic-Audio recipe ablation (w2v-BERT 2.0 + MHASP fixed; pooled EER on Speech-DF-Arena):
  - Merged corpora with random sampling: 7.159 %.
  - \+ attack- and source-balanced sampling: 6.456 %.
  - \+ supplementary bona fide corpus: 5.435 %.
  - \+ RawBoost: 5.896 %, i.e. not consistent.
  - \+ "Diverse Audio Augmentation": **1.454 %**; ASVspoof 2024-Eval fell from 17.814 % to 1.405 %.
  - The recipe also lifts other encoders against their leaderboard entries: XLS-R 300M + MHASP 6.079 % against XLSR+SLS 16.079 %. — [arXiv 2607.28351](https://arxiv.org/abs/2607.28351)
- AntiDeepfake: RawBoost during post-training was "almost always beneficial" on ADD 2023, DEEP-VOICE and In-the-Wild, but hurt on FakeOrReal. — [arXiv 2506.21090](https://arxiv.org/abs/2506.21090)
- AUDETER: 4,500 h, 11 TTS + 10 vocoders. Binary training on very diverse fakes "can induce negative transfer"; curriculum learning helps. XLS-R detectors trained on AUDETER reach 1.87 % EER on In-the-Wild. — [arXiv 2509.04345](https://arxiv.org/abs/2509.04345)
- Fake Speech Wild: augmenting public data and adding the FSW (social media) training set gives 3.54 % average EER across evaluation sets. — [arXiv 2508.10559](https://arxiv.org/abs/2508.10559)
- Multi-condition noisy training reduces EER by 10–15 points at 10–0 dB SNR across WavLM, Wav2Vec2 and MMS. — [arXiv 2512.13744](https://arxiv.org/abs/2512.13744)
- Speaker entanglement: SSL detector features are "substantially influenced by speaker information". SNAP projects out a speaker subspace and reports state-of-the-art results. — [SNAP, arXiv 2603.20686](https://arxiv.org/abs/2603.20686)
- Identity leakage is analysed the same way in [Beyond Identity, arXiv 2505.06766](https://arxiv.org/abs/2505.06766).
- Dataset-aware gradient reversal on Speech-DF-Arena: multitask cuts average EER by 13.14 % relative; GRL cuts pooled EER by 5.32 % relative. — [arXiv 2607.23961](https://arxiv.org/abs/2607.23961)

**Optimiser and loss**
- SAM (Jun 2025): AdamW versus SAM, trained on ASVspoof 2019 LA. In-the-Wild EER, mean over 3 seeds:
  - AASIST 34.31 → 33.34.
  - W2V-Base+Linear 16.85 → 13.66.
  - W2V-XLSR+Linear 6.00 → 5.99.
  - W2V-XLSR+AASIST 6.89 → 6.34.
  - Some sets got worse with XLS-R: ADD 2022 19.67 → 21.36; SpoofCeleb 27.50 → 29.93 for XLSR+AASIST.
  - Authors: "for W2V-XLSR, the improvements are less pronounced". ρ ∈ {0.05, 0.01, 0.005, 0.001}. — [arXiv 2506.11532](https://arxiv.org/abs/2506.11532)
- SAM standard form needs a second forward-backward pass per step (background). — [Foret et al., SAM, arXiv 2010.01412](https://arxiv.org/abs/2010.01412)
- SZU-AFS (ASVspoof 5 open condition, background 2024): wav2vec2 + AASIST with augmentation, then a GAM (gradient-norm-aware minimisation) second fine-tune, then logit fusion of the two best models: minDCF 0.115, EER 4.04 %. — [arXiv 2408.09933](https://arxiv.org/abs/2408.09933)
- "Collapse, Not Invariance" (30 Sep 2026): 7 auxiliary objectives against cross-entropy over 113 runs, AASIST3 at 3 seeds plus 4 pretrained detectors including DF-Arena-500M and XLSR-SLS. Objectives: MSE/MAE/cosine consistency, NT-Xent contrastive, label smoothing, GRL, DANN.
  - "No auxiliary objective keeps an advantage over cross-entropy across architectures, corpora and seeds." Five-corpus mean EER: CE 0.349 against 0.379–0.444 for the auxiliaries.
  - Four of 24 runs collapsed. "single-seed rankings reverse." — [arXiv 2610.00539](https://arxiv.org/abs/2610.00539)
- Contradiction: consistency objectives *are* reported to help in specific settings. PCL-NET helps under neural-codec compression; RTCFake's PCL helps cross-platform; TFCL helps under acoustic front-end processing. These are single-recipe claims. — [arXiv 2610.07216](https://arxiv.org/abs/2610.07216); [arXiv 2604.23742](https://arxiv.org/abs/2604.23742); [arXiv 2607.17761](https://arxiv.org/abs/2607.17761)
- Meta-learned LoRA (MLDG): trains ~3.6M params (≈1.1 % of 318M). Average EER over six corpora falls from 8.84 % (full fine-tuning) to 5.30 %. — [arXiv 2502.10838](https://arxiv.org/abs/2502.10838)

**Fusion and calibration**
- Score fusion and ensembles:
  - ASVspoof 5 closed condition: 4.08 % single → 2.71 % fused across different pretrained feature extractors. — [arXiv 2501.05545](https://arxiv.org/abs/2501.05545)
  - BUT ESDD 2026: single 4.80 % → fusion 4.38 % on final eval. — [arXiv 2512.08319](https://arxiv.org/abs/2512.08319)
  - UZH-CL: different fusion regimes for dialect shift and channel shift. — [arXiv 2610.08844](https://arxiv.org/abs/2610.08844)
  - SAFE challenge 2nd place: WavLM-L + AASIST + RawBoost on 256,600 multilingual samples. — [arXiv 2508.20983](https://arxiv.org/abs/2508.20983)
- Calibration:
  - ADD-GP returns well-calibrated probabilities, unlike score-only baselines. — [arXiv 2505.23619](https://arxiv.org/abs/2505.23619)
  - Industry report (Phonexia, 3 years): "Real inputs are not four-second clean clips but long, codec-degraded... when a calibrated system returns a log-likelihood ratio of 2.5, no one can tell the customer what it means". — [arXiv 2608.17585](https://arxiv.org/abs/2608.17585)
  - Calibration before score fusion "is essential" (SASV, background 2024). — [arXiv 2406.10836](https://arxiv.org/abs/2406.10836)
- Test-time adaptation: T²A online TTA (uncertainty-aware negative learning) improves resilience to post-processing. Code github.com/HongHanh2104/T2A-Think-Twice-Before-Adaptation. — [arXiv 2505.18787](https://arxiv.org/abs/2505.18787)

### Inferences
- Pehchaan's two remaining failures are 8 % genuine flagged on the held-out handset and 11.7 % EER there. The literature's most direct fixes for this are bona fide diversity (Teffic's "supplementary bona fide corpus") and more real or presented call audio across devices (Microsoft, RealComm). A new loss is not the fix.
- RealComm's "high-frequency attenuation alone does not explain detection difficulty" fits Pehchaan's finding that simulated codecs flag 0–2 % while real calls flag 91 %. The missing pieces are the device and network stages: AGC, noise suppression, VoLTE codecs and acoustic coupling.
- Speakerphone / over-the-air injection is the hardest condition in both RealComm and the Microsoft paper (playback 76.3 % against injection 88.2 % detection). The "learned speakerphone channel" is the right target, but it needs real recordings from more handsets to generalise.
- Do not spend site time on contrastive, OC-softmax or GRL objectives. The 113-run study says gains do not survive seeds. Report multi-seed if any loss change is tried.
- SAM is cheap to code but about doubles step time. Published gains on XLS-R are within seed noise. It is low priority.
- Score fusion with a pre-calibrated second detector (NII) is the lowest-risk accuracy gain. It must be fitted on dev only, per the pre-registered protocol in `ml/realcall/protocol.py`.

### Gaps
- RealComm's per-detector table (digital-domain against call-domain EER, condition-level EER, Aug-only / real-only / both) could not be extracted. Only the Teffic-Audio 37.94 % → 22.37 % figure is verified.
- RealComm data licence and access terms were not checked beyond "access information through the project repository".
- No 2025–26 paper found evaluates on Indian mobile networks (Jio/Airtel VoLTE, AMR-WB/EVS) or Indian handset brands, apart from Oppo/Vivo/Samsung appearing in RealComm.
- No dedicated 2025–26 study of temperature or Platt scaling or ECE for speech deepfake detectors was found. Evidence is indirect (ADD-GP calibration, Phonexia report, SpAArSIST's composite accuracy/calibration/compute score).
- OC-softmax was not tested directly in the "Collapse" study; it is named as a further route to which its diagnostics apply.

## 3. How to catch a NEW commercial voice cloner (Sarvam, ElevenLabs IVC, ...) quickly?

### Takeaway
Zero-shot detection of a new commercial cloner is unreliable; published zero-shot EERs on ElevenLabs are 40–65 %. A handful of its clips plus a non-parametric or few-shot back-end fixes most of it without forgetting:
- ADD-GP: 5-shot 7.89 %, 20-shot 3.31 %, 100-shot 0.54 % EER on ElevenLabs.
- Old-generator EER stays at 0.1 %.

Plain fine-tuning on the new clips forgets old generators. For codec/LLM-based TTS (VALL-E, F5, CosyVoice), the two training-data levers are codec-resynthesised proxies (CodecFake+) and SSL post-training. Evidence also suggests the acoustic model, not the vocoder, carries most of the detectable trace.

### Cited Findings
**Few-shot adaptation**
- ADD-GP (May 2025). XLS-R front-end with only the last block trainable, plus a Dirichlet GP classifier with an RBF deep kernel. Adaptation = add new samples to the GP's reference set, with no gradient step. MixPro mixes embeddings of old fakes with new fakes.
  - LibriFake training set: YourTTS, WhisperSpeech, VALL-E-X, F5-TTS; ElevenLabs held out.
  - OOD ElevenLabs EER: SSL-AASIST-FT 42.48 %, ADD-GP 40.31 %.
  - k-shot EER for SSL-AASIST-FT / RWM+MixPro / **ADD-GP+MixPro**:
    - 5-shot 16.17 / 14.75 / **7.89**
    - 10-shot 15.55 / 12.30 / **4.86**
    - 20-shot 12.56 / 6.97 / **3.31**
    - 50-shot 11.73 / 4.92 / **1.14**
    - 100-shot 10.97 / 1.24 / **0.54**
  - EER on the originally seen TTS after 100-shot adaptation: SSL-AASIST-FT 2.3 % (5.42 % with MixPro) against ADD-GP 0.1 %. The paper notes all baselines lose performance on old TTS "even when using methods designed to mitigate 'catastrophic forgetting'".
  - Personalised (one target speaker, 10 real + 10 fake samples): 1-shot 0.61 % on LibriSpeech speakers; 5-shot 0.52 % on VoxCeleb speakers. — [Few-Shot Speech Deepfake Detection Adaptation with Gaussian Processes, arXiv 2505.23619](https://arxiv.org/abs/2505.23619)
- Self-attentive prototypical network: with "as few as 10 in-distribution samples", up to 32 % relative EER reduction on Japanese deepfakes and 20 % on ASVspoof 2021 DF. — [arXiv 2508.13320](https://arxiv.org/abs/2508.13320)
- Meta-learning (background, Oct 2024): In-the-Wild EER 21.67 % → 10.42 % "using just 96 samples from the unseen dataset". — [arXiv 2410.20578](https://arxiv.org/abs/2410.20578)
- Adapting a detector only on outputs of an adversarially tuned F5-TTS lowers its LibriSpeech EER from 19.42 % to 7.46 % and "improves detection of unseen base F5-TTS outputs". — [arXiv 2609.30983](https://arxiv.org/abs/2609.30983)
- Data-drift monitoring: drift caused by a new TTS on MLAAD "can be monitored using distances between the distributions of the new data and reference data". Fine-tuning on the new TTS data reduces drift and error. — [arXiv 2509.10086](https://arxiv.org/abs/2509.10086)
- TADA: training-free kNN on SSL embeddings groups samples by generator, F1 0.93 across five datasets, and does out-of-domain detection. — [arXiv 2506.05802](https://arxiv.org/abs/2506.05802)
- Zero-shot open-set source tracing: SSL-AASIST + AAM + RegMixup. Few-shot backends win in-distribution; zero-shot cosine scoring wins out of distribution (OOD EER 16.43 % against 21.57–23.47 %). — [arXiv 2509.24674](https://arxiv.org/abs/2509.24674)
- GenTraceBench: post-training a TTS (SFT) can shift its fingerprint. Multi-shot enrolment cut W2V-BERT verification EER for the SFT condition from 44.4 % to 11.0 %. — [arXiv 2609.21738](https://arxiv.org/abs/2609.21738)

**Commercial cloners**
- SEA-Spoof: commercial systems are harder than open-source ones. MoLEx zero-shot EER: open-source 35.80 %, commercial 61.40 %; ElevenLabs 65.50 %, ChatGPT-4o-mini-TTS 67.30 %, MiniMax 56.50 %, HeyGen 44.39 %. — [arXiv 2509.19865](https://arxiv.org/abs/2509.19865)
- Transcript-level adversarial attacks: one commercial detector's accuracy dropped "from 100% on synthetic audio to just 32%". — [arXiv 2505.17513](https://arxiv.org/abs/2505.17513)

**Codec-based and LLM-based TTS**
- CodecFake+:
  - Training set: resynthesis through 31 open codecs. Evaluation: web-sourced output of 17 codec-based speech generators.
  - Codec-resynthesised speech works as a training proxy. Detection is strongest when the resynthesis codec has "disentanglement auxiliary objectives or a frequency-domain decoder". — [arXiv 2501.08238](https://arxiv.org/abs/2501.08238)
- DSFA (domain-shift feature augmentation) with "a post-trained SSL backbone" narrows the proxy-to-wild gap. Evaluated on CoSG ExtEval (40 unseen generators, long-form). — [arXiv 2606.07494](https://arxiv.org/abs/2606.07494)
- MN-P adds pooled "no-vocals residual" statistics to XLS-R tokens: −54.2 % EER overall and −60.9 % on unseen codecs, relative to the best retrained baseline. — [arXiv 2609.33375](https://arxiv.org/abs/2609.33375)
- Quantizer-aware codec representations (frozen backbone, +4.4 % params): −46.2 % relative EER on ASVspoof 2019 and −13.9 % on ASVspoof 5. — [arXiv 2603.16914](https://arxiv.org/abs/2603.16914)
- Codec-resynthesised audio may be labelled bona fide or spoof; the paper extends ASVspoof 5 to study this "dual role". — [arXiv 2602.16343](https://arxiv.org/abs/2602.16343)
- Detectors effective against one TTS family "may fail against others, particularly LLM-based synthesis" (Dia2, Maya1, MeloTTS); multi-view detection is more robust. — [arXiv 2601.20510](https://arxiv.org/abs/2601.20510)

### Inferences
On-site recipe for "Sarvam caught 0/12". These are inferences built from the sources above.
- Generate Sarvam clones only of consented team voices, per `ml/realcall/consent.py`.
- Pass them through the **real** Jio call path. Presentation is what the detector sees (Microsoft, RealComm).
- Split by speaker and by session into shots and held-out test clips *before* looking at scores. Add a dated protocol note, because this is a new attack condition.
- Fit an ADD-GP-like non-parametric back-end on frozen embeddings with MixPro-style mixing of new fakes and old fakes. A GP or kNN with logistic calibration on 10–50 shots takes minutes on the A10G.
- Report k-shot curves (5/10/20/50) and the EER on old generators after adaptation, to show no forgetting.
- If any gradient update is used, replay old data: plain fine-tuning forgot old generators even with MixPro (0.2 % → 5.42 %).
- Frame this as an MLOps loop for the pitch: drift detector flags an unfamiliar cloner, the team collects N consented clips, re-fits the reference set, and re-checks the old-generator EER.

### Gaps
- No published results on Sarvam voice cloning.
- No published 2025–26 few-shot results under telephony channels; ADD-GP and the prototypical work are clean-audio.
- ADD-GP code release was not confirmed.
- The ADD-GP numbers are on LibriFake (English, read speech) and may not transfer to Indic phone speech.

## 4. Indian-language datasets, benchmarks and results

### Takeaway
Indic coverage now exists:
- IndicSynth (ACL 2025, 4,000 h, 12 languages including Hindi and Telugu, CC BY-NC 4.0).
- Indic-CodecFake (12 IndicSUPERB languages, neural-codec fakes).
- SEA-Spoof (Hindi and Tamil with commercial cloners, including ElevenLabs).
- IndieFake (Indian-accented English).

English-trained detectors collapse on all of them: 40–68 % EER zero-shot. In-domain fine-tuning restores near-zero EER, but that is same-generator evidence, not unseen-generator evidence. No Indic *telephony* benchmark was found.

### Cited Findings
- IndicSynth (Sharma, Ekbote, Gupta, IIIT-Delhi; ACL 2025 long, Outstanding Paper):
  - ~4,000 h of synthetic speech from 989 target speakers in 12 languages: Bengali, Gujarati, Hindi, Kannada, Malayalam, Marathi, Odia, Punjabi, Sanskrit, Tamil, Telugu, Urdu.
  - Built by TTS voice cloning and VC on IndicSUPERB (CC0).
  - "Mimicry subsets for Hindi and Sanskrit are absent." — [ACL Anthology 2025.acl-long.1070](https://aclanthology.org/2025.acl-long.1070/); [PDF](https://aclanthology.org/2025.acl-long.1070.pdf)
  - HF dataset licence CC BY-NC 4.0, ~845 GB. — [HF vdivyasharma/IndicSynth](https://huggingface.co/datasets/vdivyasharma/IndicSynth)
- Indic-CodecFake + SATYAM (Apr 2026):
  - Neural-codec fakes on IndicSUPERB, 12 languages.
  - AASIST trained on English CodecFake: in-domain 10.13 % EER → 40.32 % EER on Indic-CodecFake zero-shot.
  - SATYAM (Whisper + TRILLsson, hyperbolic ALM fusion): 7.43 % EER for CodecFake→ICF and 3.79 % for ICF→CodecFake. Language-family transfer 7.78 % (Dravidian→Indo-European) and 8.48 % (reverse), against AASIST 33.45–38.73 %.
  - Appendix "Language-wise EER (%)" table (the excerpt does not name the model; presumably SATYAM, in-domain): Hindi 2.34 %, Telugu 4.01 %, Tamil 4.11 %, Malayalam 3.64 %.
  - Zero-shot audio-LLMs (Qwen2-Audio etc.) perform "consistently poor[ly]". — [arXiv 2604.19949](https://arxiv.org/abs/2604.19949)
- SEA-Spoof (Sep 2025):
  - 711 h across Malay, Indonesian, Thai, Hindi, Tamil, Vietnamese.
  - Generators: 10 open-source (including Indic-TTS, F5-TTS, XTTS-v2, VITS-MMS) and 4 commercial (MiniMax, ChatGPT-4o-mini-TTS, ElevenLabs, HeyGen).
  - Zero-shot EER: AASIST 43.32 %, AASIST3 33.93 %, MoLEx 43.822 % (MoLEx: 1.25 % on ASVspoof 5).
  - MoLEx commercial-only EER, zero-shot → fine-tuned on SEA-Spoof: Hindi 64.50 % → 0.06 %; Tamil 68.60 % → 0.08 %; ElevenLabs 65.50 % → 0.17 %.
  - Fine-tuning raised ASVspoof 5 EER from 1.25 % to 5.6 % ("catastrophic forgetting").
  - Dataset at huggingface.co/datasets/Jack-ppkdczgx/SEA-Spoof. — [arXiv 2509.19865](https://arxiv.org/abs/2509.19865)
- IndieFake: 27.17 h of bona fide and deepfake audio from 50 Indian English speakers, described as more challenging than In-the-Wild. — [arXiv 2506.19014](https://arxiv.org/abs/2506.19014)
- HAV-DF: Hindi audio-video deepfake dataset (Nov 2024, background). — [arXiv 2411.15457](https://arxiv.org/abs/2411.15457)
- Frozen encoders (AST, Vaani-FastConformer, Wav2vec2, Whisper, BEATs) across 22 Indic languages: "out-of-domain generalisation is predicted by a training system's proximity to unseen TTS embeddings, not its distance from natural speech". This bears on training-data selection. — [arXiv 2608.12536](https://arxiv.org/abs/2608.12536)
- Multilingual training sets:
  - SpeechFake (ACL 2025): 3M+ fakes, 3,000+ h, 40 tools, 46 languages. — [arXiv 2507.21463](https://arxiv.org/abs/2507.21463)
  - MLAAD (v11 per abstract): 205 TTS models, 1153.6 h, 54 languages. — [arXiv 2401.09512](https://arxiv.org/abs/2401.09512)
  - ML-ITW: 14 languages, 7 platforms, 180 public figures, 28.39 h; detectors degrade significantly. — [arXiv 2603.05852](https://arxiv.org/abs/2603.05852)
- Deepfake-Eval-2024: 56.5 h of in-the-wild audio from 88 websites in 52 languages. Open-source audio models' AUC dropped by 48 % against previous benchmarks. — [arXiv 2503.02857](https://arxiv.org/abs/2503.02857)
- SONAR (background 2024): foundation models "maintain[ed] strong performance across diverse languages despite being fine-tuned solely on English", and the main challenge is synthesis quality rather than language. — [arXiv 2410.04324](https://arxiv.org/abs/2410.04324)
  - The newer Indic and SEA results above contradict this for Indic and South-East Asian commercial clones.

### Inferences
- The Indic datasets are useful for Pehchaan mainly as extra *spoof diversity*. IndicSynth is already used, as NC. SEA-Spoof Hindi commercial clones (ElevenLabs, ChatGPT-4o-mini-TTS, MiniMax) are worth adding as a held-out-generator test if downloadable on site.
- Indic-CodecFake adds codec-LM-style fakes.
- None of them contains telephony, so they do not address the real-call false-alarm problem.
- Language-wise results (SATYAM: Telugu and Tamil harder than Hindi; SEA-Spoof: Tamil among the hardest) match the pattern that Dravidian languages are harder. They are consistent with Pehchaan's NII per-language EERs (te 16.9 against hi 13.3) in `ml/results/SUMMARY.md`.

### Gaps
- No Indic real-phone-call deepfake benchmark was found.
- Whether MLAAD's current version has Hindi or Telugu was not verified; the team hit a 403 gate.
- Indic-CodecFake's release status and licence were not confirmed.
- The SEA-Spoof licence was not checked.

## 5. Short-utterance (4–10 s) and 8 kHz narrowband performance

### Takeaway
EER falls steadily with more speech. On Deepfake-Eval-2024, NII XLS-R-1B gets 11.86 % at 4 s, 10.00 % at 10 s and 8.28 % at 50 s, and post-training helps most at 4 s. Deployed systems therefore score many windows and aggregate across the call. The strongest telephony paper trains and tests every model at 8 kHz with VAD and averages decisions over 2–15 s of net speech. Bandwidth loss alone does not explain call-domain failure.

### Cited Findings
- AntiDeepfake on the Deepfake-Eval-2024 test set at input lengths 4 / 10 / 13 / 30 / 50 s, with post-training:
  - XLS-R-1B 11.86 / 10.00 / 9.27 / 8.49 / 8.28.
  - MMS-300M 17.15 / 13.38 / 12.32 / 11.18 / 10.79.
  - At 4 s, post-training cut EER "by 8.1% for XLS-R-1B and 7.7% for MMS-1B". Trained on ≤13 s, yet 30–50 s inputs still lowered EER. — [arXiv 2506.21090](https://arxiv.org/abs/2506.21090)
- Microsoft telephony study:
  - "audio is sampled at 8 kHz and a voice activity detection module (VAD) is used to drop non-speech frames".
  - Training crops 0.9–1.2 s (logmel) and 1.8–2.4 s (WavLM) of net speech.
  - Realworld metrics are averaged over decision checkpoints at 2, 3, 6, 9, 12 and 15 s of net speech. Segments under 0.5 s of net speech are discarded.
  - Test protocol released at github.com/CavoloFrattale/deepfake-detection-test-protocol. — [arXiv 2509.26471](https://arxiv.org/abs/2509.26471)
- RealComm: "high-frequency attenuation alone does not explain detection difficulty". — [arXiv 2610.27459](https://arxiv.org/abs/2610.27459)
- "Hi!" (S-MGAA): targets 0.5–2.0 s inputs under communication degradations (codecs, packet loss). It "consistently surpasses nine state-of-the-art baselines" with low RTF and few parameters. Its parent MGAA covers six speech codecs and five packet-loss levels. — [arXiv 2601.19573](https://arxiv.org/abs/2601.19573); [arXiv 2508.01467](https://arxiv.org/abs/2508.01467)
- XMUspeech (ASVspoof 5): "merely adjusting the input audio length can substantially improve system performance". — [arXiv 2509.18102](https://arxiv.org/abs/2509.18102)
- Nes2Net on In-the-Wild scores the full duration, not the first 4 s, to avoid missing partial spoofs. — [arXiv 2504.05657](https://arxiv.org/abs/2504.05657)
- Classical features on FoR give the same 7 % EER at 44.1 kHz and 16 kHz ("telephone-quality"). — [arXiv 2604.13400](https://arxiv.org/abs/2604.13400)

### Inferences
- Pehchaan's latency budget forces short windows. Score 4 s windows with hop, aggregate by mean of logits or LLR across the first N windows of the call, and report EER against seconds of net speech (2/4/6/10 s), as Microsoft does. This is code-only and needs no GPU time.
- VAD before scoring is cheap and removes a known shortcut (silence).
- Training directly at 8 kHz (as Microsoft does) is an alternative to 16 kHz upsampled narrowband. With an SSL encoder pretrained at 16 kHz, keep 16 kHz input and band-limit during augmentation.

### Gaps
- No controlled 2025–26 study of the same SSL detector at 8 kHz against 16 kHz input was found.
- S-MGAA EER numbers were not retrieved.

## 6. Ranked shortlist: do on site (≤1.5 days, one A10G) vs post-hackathon

### Takeaway
On site, prefer actions that reuse existing code and weights and take minutes to a few GPU-hours:
1. Calibrated score fusion with the already-ported NII detector.
2. Re-start the fine-tune from AntiDeepfake post-trained weights.
3. A few-shot GP/prototype "new cloner" adapter shown on held-out Sarvam clips.
4. Bona fide and augmentation diversity in one retrain.
5. Multi-window call-level scoring.

Leave encoder changes (w2v-BERT 2.0), RealComm-style multi-handset collection, MoE/LoRA continual learning and codec-specific modules for after the hackathon.

### Cited Findings
- Fusion across different pretrained extractors: ASVspoof 5 4.08 % → 2.71 % EER. — [arXiv 2501.05545](https://arxiv.org/abs/2501.05545)
- Post-training before fine-tuning: XLS-R-1B 19.96 → 11.86 % and MMS-300M 19.77 → 17.15 % EER at 4 s on Deepfake-Eval-2024, with a 6k-step lr 1e-6 fine-tune schedule. — [arXiv 2506.21090](https://arxiv.org/abs/2506.21090)
- Few-shot GP adaptation: ElevenLabs 20-shot 3.31 % EER, no forgetting (0.1 %). — [arXiv 2505.23619](https://arxiv.org/abs/2505.23619)
- Recipe ablation: supplementary bona fide 6.456 → 5.435 %; diverse augmentation → 1.454 % pooled. — [arXiv 2607.28351](https://arxiv.org/abs/2607.28351)
- Real-call plus simulated augmentation is best for all three RealComm detectors. — [arXiv 2610.27459](https://arxiv.org/abs/2610.27459)
- Presentation realism outranks model size. — [arXiv 2509.26471](https://arxiv.org/abs/2509.26471)
- Auxiliary losses do not beat cross-entropy across seeds. — [arXiv 2610.00539](https://arxiv.org/abs/2610.00539)
- SAM gives a marginal gain on XLS-R. — [arXiv 2506.11532](https://arxiv.org/abs/2506.11532)

### Inferences
**Do on site (≤1.5 days, one A10G). Ranked by value per hour; estimates are mine.**
1. **Calibrated score fusion: Pehchaan v-current + NII MMS-300M AntiDeepfake (already ported).**
   - Method: logistic-regression fusion, effectively Platt scaling on two scores, fitted on the *dev* real-call split only; then report on the pre-registered test set.
   - Cost: minutes, CPU.
   - Why: the team's own numbers show NII is stronger on the held-out speaker (10.3 % against 16.6 % EER). Fusion of different front-ends is consistently positive in published work.
   - Risk: low. NC licence on NII weights; demo only.
2. **Re-initialise the fine-tune from AntiDeepfake MMS-300M (same size as now) instead of the TakHemlata LA checkpoint.**
   - Keep the same corpus, real-call clips, learned speakerphone channel and AASIST or mean-pool head. Use the paper's gentle schedule (lr ~1e-6, a few thousand steps).
   - Cost: roughly 2–5 A10G hours for a 300M model (estimate). Try XLS-R-1B AntiDeepfake only if time allows: bf16, gradient checkpointing, batch 2–4 or LoRA.
   - Why: the post-training gain is largest at 4 s windows and on unseen conditions.
   - Risk: NC licence; must be scored under the unchanged pre-registered protocol.
3. **"New cloner in N clips" few-shot adapter for Sarvam.**
   - Use consented voices only. Route the clips through the real Jio call.
   - Model: frozen embeddings (current detector's penultimate layer, or NII) feeding a GP or prototype classifier with MixPro-style mixing.
   - Show k-shot EER on held-out Sarvam clips and unchanged EER on old generators.
   - Cost: under 1 h after clip collection (collection is the bottleneck).
   - Why: it directly answers the 0/12 finding with a credible ops story.
   - Risk: small n. Report counts, not just %, and add a dated protocol note for the new split.
4. **One retrain with bona fide diversity plus broader augmentation.**
   - More genuine speech from more handsets and speakerphone, to target the 8 % genuine-flag rate on the new handset.
   - Attack- and source-balanced sampling.
   - Augmentation beyond RawBoost, covering device AGC, noise suppression, VoLTE codecs and acoustic coupling, ordered along the signal path as in RealComm-Aug.
   - Cost: one overnight-scale run, if started early on day 1.
   - Risk: must not touch the test handset's audio.
5. **Call-level multi-window scoring and VAD.**
   - Report EER and genuine-flag rate against seconds of net speech.
   - Cost: code only. Why: published EER falls monotonically with duration.
6. Optional, if GPU is idle:
   - DF_Arena_1B_V_1 as a third zero-shot scorer for the comparison table (NC).
   - SAM on the retrain: expect ≤0.5-point changes on XLS-R, about 2× step time.
7. Do **not** do on site:
   - New auxiliary losses (contrastive, OC-softmax, GRL).
   - Back-end swaps (Nes2Net, Mamba).
   - Test-time adaptation.
   - Audio-LLM detectors (7B, poor zero-shot on Indic codec fakes).

**Post-hackathon (ranked)**
1. RealComm-style paired real-call corpus for India: multiple handsets and brands in a ring partition, operators (Jio/Airtel/Vi), VoLTE/AMR-WB/EVS, handset against speakerphone against over-the-air injection, denoising on and off. Train on simulated plus real.
2. Commercial-licence backbone: w2v-BERT 2.0 (MIT) with MHASP and the Teffic-style recipe (balanced sampling, supplementary bona fide, diverse augmentation). A truncated 4–6-layer encoder (106–155M) suits latency. A PEFT variant (Wavelet Prompt Tuning or LoRA) keeps the backbone frozen.
3. Continual-learning loop: drift monitoring plus few-shot GP reference-set updates, with meta-learned LoRA, MoE-LoRA or RWM for periodic retrains without forgetting.
4. Speaker-entanglement fixes (SNAP speaker nulling), aimed at the held-out-speaker gap.
5. Codec/LLM-TTS coverage: CodecFake+ codec-resynthesis proxies, DSFA, the MN-P residual view and Indic-CodecFake data. Use consistency objectives only with multi-seed checks.
6. Proper calibration and abstention for shadow mode: per-channel calibration, GP or uncertainty outputs, and LLR-to-action mapping that bank staff can read.
7. Replace all NC assets (AntiDeepfake, DF Arena, IndicSynth, NC generators) before any commercial pilot.

### Gaps
- All A10G time and memory figures above are estimates, not measured. Verify with one short timing run before committing to the XLS-R-1B or w2v-BERT 2.0 paths.
- ADD-GP code availability is unconfirmed; a minimal re-implementation (GP or kNN on frozen embeddings) may be needed.
- RealComm's detailed per-condition numbers and dataset access terms remain to be read from the repository.
