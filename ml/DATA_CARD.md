# Pehchaan - DATA_CARD (licences, access, loading facts)

Verified 2026-10-06 against HF API (`/api/models|datasets/<id>`: `gated`, `cardData.license`, `siblings`), HF/GitHub cards and source, PyPI JSON, Zenodo API, Edinburgh DataShare, and vendor docs.
**NC** = non-commercial licence. "unverified" = could not confirm from a primary source.
Gated values: `false` = open; `auto` = must log in, accept the conditions on the HF page, then use an HF token (approval is automatic); `manual` = the authors approve each request.

> Before using any **NC** item: a hackathon demo is usually research or evaluation use, but anything shipped commercially (including an Amazon-facing product) must leave out NC data, weights, and outputs. This is not legal advice.

## 1. Datasets

| Name | Source URL | Licence | Gated? | Commercial use? | How we use it | Notes |
|---|---|---|---|---|---|---|
| FLEURS | https://huggingface.co/datasets/google/fleurs | CC-BY-4.0 | false | Yes | Bona fide read speech: hi/te/ta/mr/bn/kn/ml/gu + en_us | Layout: `data/<lang>/audio/{train,dev,test}.tar.gz` + `data/<lang>/{train,dev,test}.tsv`. Parquet copies sit in `parquet-data/<lang>/{train,validation,test}-00000-of-00001.parquet`, and `load_dataset` reads those. Sizes (train/dev/test tar, MB): hi_in 1257/132/249, te_in 1503/167/270, ta_in 1639/239/407, en_us 1381/171/290, mr_in 2199/293/720, bn_in 2035/279/660, kn_in 1560/251/615, ml_in 1842/310/722, gu_in 1721/226/551. TSV layout is in Loading notes. Audio is 16 kHz. |
| IndicVoices | https://huggingface.co/datasets/ai4bharat/IndicVoices | CC-BY-4.0 | **auto** | Yes | Bona fide spontaneous and conversational speech in 22 languages | Parquet: `<language>/train-*.parquet` plus `valid`. 745 GB in total. Per language: hindi 49.8 GB, telugu 33.5, tamil 49.8, marathi 37.5, bengali 40.6, kannada 39.1, malayalam 41.3, gujarati 27.5. Full-length originals: `https://iv-release.objectstore.e2enetworks.net/dmu_release/v{1..5}_<Language>_train.tgz`. Column names unverified (gated). |
| Kathbath | https://huggingface.co/datasets/ai4bharat/Kathbath (`ai4bharat/kathbath` redirects here) | Metadata says CC-BY-4.0, but the card text says **CC0** ("packaging of IndicSUPERB") | **auto** | Yes | Bona fide read speech, 12 languages, 1,684 h | Parquet: `<language>/{train,valid,...}-*.parquet`. 174 GB in total. hindi 16.6 GB, tamil 21.4, telugu 17.1, marathi 18.0, bengali 10.6, kannada 17.4, malayalam 16.5, gujarati 13.6. Columns unverified. |
| Lahaja | https://huggingface.co/datasets/ai4bharat/Lahaja | Card text says CC BY 4.0, but the metadata tag says MIT (they conflict) | **auto** | Yes | Multi-accent Hindi test set, 12.5 h, 132 speakers | `data/test-0000{0-3}-of-00004.parquet`, 1.42 GB. Load with `load_dataset("ai4bharat/Lahaja", split="test")`. |
| Svarah | https://huggingface.co/datasets/ai4bharat/Svarah | CC BY 4.0 (card text; no metadata tag) | **auto** | Yes | Indian-accented English test set, 9.6 h, 117 speakers | `data/test-*.parquet` (3 files), 1.09 GB. |
| IndicVoices-R | https://huggingface.co/datasets/ai4bharat/indicvoices_r | CC-BY-4.0 | **auto** | Yes | TTS-grade bona fide speech; good reference clips for cloning | Folders use capitalised names (`Hindi/` 47.2 GB, `Telugu/` 86.1, `Tamil/` 63.1). Also CC-BY-4.0 and auto-gated: `ai4bharat/Rasa`, `ai4bharat/Shrutilipi`. |
| MLAAD | https://huggingface.co/datasets/mueller91/MLAAD | CC-BY-NC-4.0 **NC** ("strictly for non-commercial academic research") | **auto** | No | Spoof train/eval set that includes Hindi fakes | 183 GB. Layout `fake/<lang>/<model>/{meta.csv,*.wav}`. meta.csv is pipe-separated: `path\|original_file\|language\|is_original_language\|duration\|training_data\|model_name\|architecture\|transcript\|reference_speaker`. The card only mentions "v8" (the version that added `reference_speaker`); the current version number is unverified (last modified 2026-08-28). There are 54 languages. **hi**: IndicF5, Indri-TTS-0.1, OmniVoice, Ringg Squirrel TTS v1.0, Veena, VoxCPM2, Voxtral, bark, xtts_v2. **bn**: IndicF5, bn custom VITS female and male, bark. **ta, mr**: IndicF5. **kn**: Edge-TTS, SvaraTTS v1. **ml, ur, si**: Edge-TTS. **te: none**. Each system has about 1,000 clips (hi: IndicF5 619 MB, Indri 289 MB, OmniVoice 320 MB). The repo has no bona fide audio; real speech comes from M-AILABS. |
| MLAAD-tiny | https://huggingface.co/datasets/mueller91/MLAAD-tiny | fake: CC-BY-NC-4.0 **NC**; original: M-AILABS licence | false | No (fake part) | Smoke tests | 64 TTS systems x 100 clips, English and German only. |
| M-AILABS | https://github.com/i-celeste-aurora/m-ailabs-dataset | Custom BSD-style licence ("any commercial use ... permitted", keep the notice, no endorsement) | n/a | Yes | Bona fide pair for MLAAD | Languages: de_DE, en_UK, en_US, es_ES, fr_FR, it_IT, pl_PL, ru_RU, uk_UK. No Indic languages. |
| IndicSynth | https://huggingface.co/datasets/vdivyasharma/IndicSynth | CC-BY-NC-4.0 **NC** | false | No | Indic synthetic (spoof) speech, 12 languages | Parquet: `<Language>/train-*.parquet`. Columns (verified): `audio, Generative Model, Source Speaker_ID, Target Speaker ID, Gender, Source Reference Audio, Target Reference Audio, TTS Transcript`. Hindi 56.0 GB; Telugu 91.7, Tamil 148.5, Marathi 42.6, Bengali 33.6, Kannada 68.4, Malayalam 24.4, Gujarati 50.8 (about 845 GB in total). Whether it contains bona fide clips is unverified. |
| ASVspoof 2019 (LA) | https://datashare.ed.ac.uk/handle/10283/3336 | ODC-By ("Open Data Commons Attribution License") | n/a | Yes (with attribution) | English LA spoofs (train and eval) | Direct link: `https://datashare.ed.ac.uk/bitstreams/a9f87c35-f055-4015-80e2-2fdff0d46269/download`. A range-request test returned 206, so the link is live. LA.zip is 7,640,952,520 B ("7.12 GB"), MD5 `30c98f11d8b2bc21f2c257bfd78bb5c5`. PA.zip is 16.45 GB. DataShare moved to DSpace 7, so old `...?sequence=` links may break. |
| ASVspoof 5 | https://zenodo.org/records/14498691 | ODC-By (LICENSE.txt) | open | Yes | Large crowdsourced spoof set | v0.1 is the latest (2024-12-18). 142.3 GB: `flac_T_aa..ae.tar` (5 x 7.5 GB, train), `flac_D_aa..ac.tar` (3 x 6.7 GB, dev), `flac_E_aa..aj.tar` (10 x 8.46 GB, eval), `ASVspoof5_protocols.tar.gz` (0.02 GB), README.txt, LICENSE.txt. |
| In-the-Wild | https://deepfake-total.com/in_the_wild (HF: https://huggingface.co/datasets/mueller91/In-The-Wild) | Website says **Apache-2.0**; the HF card says **CC-BY-SA-4.0** (they conflict) | false | Yes (both are permissive; follow SA if you redistribute) | English real-world eval | `release_in_the_wild.zip`, 8.16 GB. 58 speakers: 20.8 h bona fide, 17.2 h spoof. |
| indian-language-deepfake-speech | https://huggingface.co/datasets/satwc-reddy/indian-language-deepfake-speech | CC-BY-4.0 (as declared by the uploader) | false | Unclear | Te/Ta/Ml/Konkani spoof vs real | About 15k clips. Real speech from OpenSLR; fakes from MMS-TTS (**NC** model), SIGVC, RVC. `metadata.csv: file_path,label,language,method` with 0 = real, 1 = fake. Licences of the source data are unverified. |
| SEA-Spoof | https://huggingface.co/datasets/Jack-ppkdczgx/SEA-Spoof | "other": non-commercial academic use only **NC** | **manual** | No | en, **hi**, id, ms, **ta**, th, vi spoofs (700+ h) | Needs author approval (by email or the HF form). |
| banglaFake | https://huggingface.co/datasets/sifat1221/banglaFake | No licence stated (unverified) | false | Unverified | Bangla spoofs | Only `final_data.zip` (5.64 GB); no card. |
| bangla_deepfake_samples | https://huggingface.co/datasets/tsfrsd/bangla_deepfake_samples | MIT | false | Yes | Small Bangla VITS-clone sample set | About 84 files. |
| IndieFake (IFD) | arXiv 2506.19014 | unverified | not on HF (no search hit) | Unverified | Indian-accented English deepfakes | 27.17 h, 50 speakers. Access route unverified. |

## 2. Detectors (zero-shot baselines)

| Name | Source URL | Licence | Gated? | Commercial use? | How we use it | Notes |
|---|---|---|---|---|---|---|
| SSL_Anti-spoofing (XLS-R + AASIST) | https://github.com/TakHemlata/SSL_Anti-spoofing | Code: MIT. Weights: no licence stated (Google Drive) | n/a | Code yes; weights unclear | Baseline A | Drive folder `1c4ywztEVlYVijfwbGLl9OEa1SNtFKppB` holds `LA_model.pth` (ID `11vFBNKzYUtWqdK358_JEygawFzmmaZjO`) and `Best_LA_model_for_DF.pth` (ID `1JHBClArVdM-Cr1b8In1iakTV_TvC3HvG`). The README calls them best_SSL_model_LA/DF.pth. Needs `xlsr2_300m.pt` and the fairseq commit bundled in the repo. Index 1 = bona fide. Input is 64600 samples at 16 kHz. **No official HF mirror.** `sempertemper/ssl-antispoofing-weights` is a 2.54 GB tar with no card (contents unverified). `ash56/ssl-aasist` (Apache-2.0) is a *different* SSL-AASIST trained on WaveFake LJSpeech HiFiGAN; it uses trust_remote_code and fairseq, and also hosts xlsr2_300m.pt. |
| XLS-R 300M (fairseq) | https://dl.fbaipublicfiles.com/fairseq/wav2vec/xlsr2_300m.pt | fairseq repo MIT; separate weights licence unverified | n/a | Likely | Front end for the model above | 3,808,868,242 B; link live (HTTP 206). |
| NII AntiDeepfake (14 repos) | https://huggingface.co/nii-yamagishilab/mms-300m-anti-deepfake | CC-BY-NC-SA-4.0 **NC** ("research and educational purposes") | false | No | Baseline B (strongest open model) | Repos: `{wav2vec-small, wav2vec-large, mms-300m, mms-1b, xls-r-1b, xls-r-2b, hubert-xlarge}-anti-deepfake` plus `-nda` variants. Note the ids use `wav2vec-` (`wav2vec2-small-anti-deepfake` does not exist). Files: `config.json`, `model.safetensors` (fairseq-style keys `m_ssl.model.*` + `proj_fc.*`). **Needs fairseq==0.12.2 + PyTorchModelHubMixin and does not load with plain transformers.** 16 kHz input, any length. Output index **0 = fake, 1 = real**. Trained on 56k h real + 18k h fake, including FLEURS, FLEURS-R, and MLAAD. GitHub AntiDeepfake reports licence "Other" (unverified). |
| Deepfake-audio-detection-V2 | https://huggingface.co/MelodyMachine/Deepfake-audio-detection-V2 | Apache-2.0 | false | Yes | Baseline C (transformers) | `Wav2Vec2ForSequenceClassification`, id2label `{0:"fake",1:"real"}`, 16 kHz. Base: motheecreator/Deepfake-audio-detection (wav2vec2-base). Training data is an undisclosed "audiofolder". |
| Deepfake-audio-detection | https://huggingface.co/motheecreator/Deepfake-audio-detection (same as `mo-thecreator/...`) | Apache-2.0 | false | Yes | Optional | id2label `{0:"fake",1:"real"}`. Training data undisclosed. |
| wav2vec2-large-xlsr-deepfake-audio-classification | https://huggingface.co/Gustking/wav2vec2-large-xlsr-deepfake-audio-classification | Apache-2.0 | false | Yes | Baseline D | id2label **`{0:"real",1:"fake"}`**. Base: alefiury/wav2vec2-large-xlsr-53-gender-recognition-librispeech. Card reports ASVspoof2019 (Kaggle) eval EER 4.01%. Training data not stated. |
| wav2vec2-deepfake-voice-detector | https://huggingface.co/garystafford/wav2vec2-deepfake-voice-detector | Apache-2.0 | false | Yes | Optional | id2label **`{0:"real",1:"fake"}`**. Fine-tuned from Gustking on `garystafford/deepfake-audio-detection` (ElevenLabs, Polly, Kokoro, Hume, Speechify, Luvvoice). English only. |

**Label order differs between families**: NII and MelodyMachine use index 0 = fake; Gustking and garystafford use index 0 = real; Tak uses index 1 = bona fide. Always read `config.id2label`.

## 3. Generators (attack corpus)

| Name | Source URL | Licence | Gated? | Commercial use? | How we use it | Notes |
|---|---|---|---|---|---|---|
| IndicF5 | https://huggingface.co/ai4bharat/IndicF5 | MIT (card metadata), plus Terms of Use: "only clone voices for which you have explicit permission" | **auto** | Yes per MIT | Main Indic cloning attack | 11 languages (as, bn, gu, hi, kn, ml, mr, or, pa, ta, te). Needs ref_audio + ref_text. Outputs 24 kHz. Prompts: `prompts/PAN_F_HAPPY_00001.wav`, `prompts/MAR_F_HAPPY_00001.wav`. |
| F5-Hindi-24KHz | https://huggingface.co/SPRINGLab/F5-Hindi-24KHz | CC-BY-4.0 | false | Yes (the card says "primarily intended for research") | Ungated Hindi F5 | F5 "small" (151M), trained from scratch on IndicTTS-Hindi + IndicVoices-R Hindi. Files: `model_2500000.safetensors`, `vocab.txt`. Run with the https://github.com/rumourscape/F5-TTS fork. |
| SPRING_F5 | https://huggingface.co/SPRINGLab/SPRING_F5 | Card says Apache-2.0, **but** base_model is SWivid/F5-TTS (**NC** weights), so whether the licence carries over is unclear | false | Unclear | Ungated, 23 Indic languages + en, code-mix | `AutoModel.from_pretrained(..., trust_remote_code=True)`, called with `lang='hi'`. Install: `pip install git+https://github.com/ArigalaAdarsh/SPRING_F5.git`. |
| F5-TTS (SWivid) | https://huggingface.co/SWivid/F5-TTS | Weights: CC-BY-NC-4.0 **NC** (trained on Emilia). Code: MIT | false | No (weights) | Optional | pip `f5-tts` (latest 1.1.22, MIT). |
| XTTS-v2 | https://huggingface.co/coqui/XTTS-v2 | Coqui Public Model License (CPML; non-commercial) **NC** | false | No | Hindi cloning attack (hi is supported) | 17 languages. Maintained package: `pip install coqui-tts` (idiap fork, 0.27.5, MPL-2.0; Python >=3.10,<3.15). To accept the licence without a prompt: `COQUI_TOS_AGREED=1`. |
| Chatterbox Multilingual | https://huggingface.co/ResembleAI/chatterbox | MIT | false | Yes | Hindi cloning attack (`language_id="hi"`) | 23 languages, 24 kHz. **The Perth watermark is applied to every output with no off switch.** `pip install chatterbox-tts` (0.1.3 or later has `ChatterboxMultilingualTTS`; 0.1.7 is latest but loads only the V2 checkpoint `t3_mtl23ls_v2`). V3 (`t3_model="v3"`) only works from a GitHub install. Hindi pack `ResembleAI/Chatterbox-Multilingual-hi` (MIT, ungated): `t3_hi.safetensors` + `s3gen_v3`. PyPI has no loader for it; the HF Space code does. |
| CosyVoice2-0.5B | https://huggingface.co/FunAudioLLM/CosyVoice2-0.5B | Apache-2.0 | false | Yes | Cross-lingual attack only | Languages: zh, en, fr, es, ja, ko, it, ru, de. **No Hindi.** |
| Fun-CosyVoice3-0.5B-2512 | https://huggingface.co/FunAudioLLM/Fun-CosyVoice3-0.5B-2512 | Apache-2.0 | false | Yes | Optional | Released. Same 9 languages plus 18+ Chinese dialects. **No Hindi.** The GitHub repo moved to QwenAudio/CosyVoice (Apache-2.0). Install from git (below); PyPI `cosyvoice` 0.0.8 is a GPL-3.0 package from 2024 (official status unverified). |
| Seed-VC | https://huggingface.co/Plachta/Seed-VC (code: https://github.com/Plachtaa/seed-vc) | GPL-3.0 (code and HF weights) | false | Yes (copyleft) | Voice-conversion attack (language-agnostic) | Speech models output **22,050 Hz** (there is no 16 kHz model); SVC outputs 44.1 kHz. The `Plachtaa/seed-vc` HF id does not exist; the HF id is `Plachta/Seed-VC`. pip `seed-vc` 0.4.3 (GPL-3.0) exists but is unverified as official. |
| OpenAudio S1-mini | https://huggingface.co/fishaudio/openaudio-s1-mini | CC-BY-NC-SA-4.0 **NC** | **auto** | No | Optional | |
| Fish Audio S2-Pro | https://huggingface.co/fishaudio/s2-pro | Fish Audio Research License (research and non-commercial; commercial use needs a separate licence) **NC** | false | No | Optional (lists hi, ta, te, bn, ml, ur) | Supports 80+ languages. |
| IndexTTS-2 | https://huggingface.co/IndexTeam/IndexTTS-2 | bilibili Model Use License: royalty-free, but you need a separate licence above 100M MAU or RMB 1bn revenue. Section 3.4(c): you **may not use the model or Derivative Works (outputs included) to improve any other AI model except non-commercial ones** | false | Conditional | Probably skip | Card languages: **en, zh only**. Repo LICENSE.txt; China law and arbitration. |
| Indic Parler-TTS | https://huggingface.co/ai4bharat/indic-parler-tts | Apache-2.0 | **auto** | Yes | Stock-voice Indic TTS (no cloning) | Card lists en, as, bn, gu, hi, kn, ks, or, ml, mr, ne, pa, sa, sd, ta, te, ur. pip `parler-tts`. |
| MMS-TTS hin / tel / tam | https://huggingface.co/facebook/mms-tts-hin (also -tel, -tam) | CC-BY-NC-4.0 **NC** | false | No | Low-quality single-speaker TTS spoofs | transformers `VitsModel`. |
| AudioSeal | https://huggingface.co/facebook/audioseal (code: facebookresearch/audioseal) | MIT (code and weights since 2024-04-02) | false | Yes | Watermark-detection side signal | pip `audioseal` 0.2.0. Detector `audioseal_detector_16bits`. |

## 4. Commercial APIs (stock-voice spoofs)

| Name | Source URL | Licence | Gated? | Commercial use? | How we use it | Notes |
|---|---|---|---|---|---|---|
| Sarvam Bulbul | https://docs.sarvam.ai/api-reference-docs/text-to-speech/convert | Sarvam ToS (not reviewed) | API key (`api-subscription-key` header) | Paid | Indic stock-voice spoofs | `POST https://api.sarvam.ai/text-to-speech`. Models `bulbul:v3` (latest) and `bulbul:v2` (legacy). Output: JSON `audios[]` of base64 audio (WAV by default). Details in Loading notes. |
| OpenAI TTS | https://developers.openai.com/api/docs/guides/text-to-speech | OpenAI usage policies (you must disclose AI voice to end users) | API key | Paid | Hindi/English stock spoofs | `POST https://api.openai.com/v1/audio/speech`. Models: `gpt-4o-mini-tts`, `tts-1`, `tts-1-hd`. 13 voices: alloy, ash, ballad, coral, echo, fable, nova, onyx, sage, shimmer, verse, marin, cedar (tts-1 and tts-1-hd support 9 of these). Hindi, Marathi, Tamil, Kannada, Urdu are in the supported-language list; the docs say voices are "optimized for English". Formats: mp3 (default), opus, aac, flac, wav, pcm (24 kHz, s16le). |
| Gemini TTS | https://ai.google.dev/gemini-api/docs/speech-generation | Google API terms (not reviewed); SynthID not mentioned on the page (unverified) | API key | Paid | Indic stock spoofs; also has voice replication | Current models: **`gemini-3.8-flash-tts`, `gemini-3.8-flash-lite-tts`** via the **Interactions API** (`POST https://generativelanguage.googleapis.com/v1beta/interactions`). Also listed: Gemini 3.1 Flash TTS Preview and `gemini-2.5-pro-preview-tts`. `gemini-2.5-flash-preview-tts` is no longer listed. Unary output is WAV (24 kHz mono s16le); streaming output is raw `audio/l16`. Also offers mulaw and alaw, plus `sample_rate` 24000/16000/8000. Hindi, Bangla, Gujarati, Kannada, Malayalam, Marathi, Odia, Punjabi, Tamil, Telugu are supported. 30 voices are listed below. |
| Deepgram Aura-2 | https://developers.deepgram.com/docs/tts-models | Deepgram ToS | API key | Paid | Not useful | Languages: en, es, de, fr, nl, it, ja. **No Hindi voice.** |

## 5. Tools

| Name | Source URL | Licence | Gated? | Commercial use? | How we use it | Notes |
|---|---|---|---|---|---|---|
| pyroomacoustics | https://github.com/LCAV/pyroomacoustics | MIT | n/a | Yes | Room impulse responses / reverberation augmentation | PyPI 0.10.1 |
| silero-vad | https://github.com/snakers4/silero-vad | MIT | n/a | Yes | Voice activity detection (VAD) | PyPI 6.2.3 |
| webrtcvad | https://github.com/wiseman/py-webrtcvad | MIT (PyPI) | n/a | Yes | Lightweight VAD | PyPI `webrtcvad` 2.0.10 (2017). On Windows use `webrtcvad-wheels` 2.0.14.post1 (MIT). |
| opencore-amr | https://sourceforge.net/projects/opencore-amr/ | Apache-2.0 (LICENSE in master) | n/a | Yes (code; codec patent status unverified) | AMR-NB/WB telephony channel simulation | No PyPI package with that name; use through ffmpeg (`libopencore_amrnb`). |
| resemble-perth | https://github.com/resemble-ai/Perth | MIT | n/a | Yes | Detect the Chatterbox watermark | PyPI 1.0.1 |
| fairseq | https://github.com/facebookresearch/fairseq | MIT | n/a | Yes | Needed by the NII and Tak models | |

## Loading notes

**FLEURS (1).** `load_dataset("google/fleurs","hi_in",split="test")` reads `parquet-data/`. To work from the raw files instead: `hf_hub_download("google/fleurs","data/hi_in/test.tsv",repo_type="dataset")` and `.../data/hi_in/audio/test.tar.gz`. The TSV has no header and is tab-separated, with 7 columns: `id`, `file_name`, `raw_transcription`, `transcription` (normalised), `char_tokens` (space-separated characters, `|` between words), `num_samples` (at 16 kHz), `gender`. Tar members are named `<split>/<file_name>` (for example `dev/1000...wav`).

**MLAAD Hindi subset (3).** Accept the conditions on the HF page, then `huggingface-cli login`, then `huggingface-cli download mueller91/MLAAD --repo-type dataset --include "fake/hi/*" --local-dir MLAAD`.

**ASVspoof 2019 LA (5).** `curl -L -o LA.zip "https://datashare.ed.ac.uk/bitstreams/a9f87c35-f055-4015-80e2-2fdff0d46269/download"`, then check the MD5 `30c98f11d8b2bc21f2c257bfd78bb5c5`.

**8. SSL_Anti-spoofing (Tak).**
```bash
git clone https://github.com/TakHemlata/SSL_Anti-spoofing && cd SSL_Anti-spoofing
pip install -e fairseq-a54021305d6b3c4c5959ac9395135f63202db8f1   # README env: py3.7, torch 1.8.1+cu111
wget https://dl.fbaipublicfiles.com/fairseq/wav2vec/xlsr2_300m.pt   # model.py hard-codes cp_path='xlsr2_300m.pt' (relative to cwd)
gdown 11vFBNKzYUtWqdK358_JEygawFzmmaZjO   # LA_model.pth
gdown 1JHBClArVdM-Cr1b8In1iakTV_TvC3HvG   # Best_LA_model_for_DF.pth
```
```python
import torch, librosa, numpy as np
from model import Model                      # repo's model.py
m = Model(None, "cuda").to("cuda")           # the args parameter is never used
m.load_state_dict(torch.load("LA_model.pth", map_location="cuda")); m.eval()   # no 'module.' prefix in train/eval code
def pad(x, L=64600):                         # repo's pad(): truncate, or tile-repeat short clips (~4 s at 16 kHz)
    return x[:L] if len(x) >= L else np.tile(x, L // len(x) + 1)[:L]
x, _ = librosa.load(path, sr=16000)
with torch.no_grad():
    out = m(torch.tensor(pad(x))[None].float().cuda())   # [B,2] logits
score = out[:, 1].item()   # eval code writes raw logit[:,1]; labels bonafide=1, spoof=0 -> higher = more bona fide
```
Eval also cuts to the first 64600 samples. Training uses CrossEntropy with weight [0.1, 0.9].

**9. NII AntiDeepfake.** This needs fairseq; plain transformers will not load it. The card pins `python==3.9.0`, `pip==24.0`, `huggingface-hub==0.31.1 fairseq==0.12.2 safetensors==0.5.3 soundfile==0.13.1`. Minimal code from the card (mms-300m and xls-r-300m-size config):
```python
import torch, torchaudio
from fairseq.models.wav2vec import Wav2Vec2Model, Wav2Vec2Config
from huggingface_hub import PyTorchModelHubMixin
class SSLModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        cfg = Wav2Vec2Config(quantize_targets=True, extractor_mode="layer_norm", layer_norm_first=True,
            final_dim=768, latent_temp=(2.0,0.1,0.999995), encoder_layerdrop=0.0, dropout_input=0.0,
            dropout_features=0.0, dropout=0.0, attention_dropout=0.0, conv_bias=True, encoder_layers=24,
            encoder_embed_dim=1024, encoder_ffn_embed_dim=4096, encoder_attention_heads=16, feature_grad_mult=1.0)
        self.model = Wav2Vec2Model(cfg)
    def extract_feat(self, x):
        with torch.no_grad():
            return self.model(x, mask=False, features_only=True)['x']
class DeepfakeDetector(torch.nn.Module, PyTorchModelHubMixin):
    def __init__(self):
        super().__init__()
        self.m_ssl = SSLModel(); self.adap_pool1d = torch.nn.AdaptiveAvgPool1d(1)
        self.proj_fc = torch.nn.Linear(1024, 2)
    def forward(self, wav):
        emb = self.m_ssl.extract_feat(wav).transpose(1, 2)
        return self.proj_fc(self.adap_pool1d(emb).squeeze(-1))
model = DeepfakeDetector.from_pretrained("nii-yamagishilab/mms-300m-anti-deepfake").eval()
wav, sr = torchaudio.load(p); wav = wav.mean(0)
wav = torchaudio.functional.resample(wav, sr, 16000)
wav = torch.nn.functional.layer_norm(wav, wav.shape)[None]       # mono, 16 kHz, layer-normed, any length
probs = torch.softmax(model(wav), dim=1)[0]; p_real, p_fake = probs[1], probs[0]   # index 0 = fake, 1 = real
```
Other sizes need different config values, so copy the block from each card:
- `wav2vec-small`: `Wav2Vec2Config(encoder_layers=12, encoder_embed_dim=768, quantize_targets=True, latent_dim=256, final_dim=256)` with a Linear(768, 2) head.
- `xls-r-1b`: 48 layers, embed 1280, ffn 5120, final_dim 1024, with a Linear(1280, 2) head.

**10. HF classifiers.** `AutoFeatureExtractor` + `AutoModelForAudioClassification.from_pretrained(id)` at 16 kHz, then `softmax(logits)[model.config.label2id["fake"]]`.

**11. IndicF5.** Gated (auto): accept the conditions on the page, then `huggingface-cli login`. Install with `pip install git+https://github.com/ai4bharat/IndicF5.git` (python 3.10). Card snippet:
```python
from transformers import AutoModel
import numpy as np, soundfile as sf
model = AutoModel.from_pretrained("ai4bharat/IndicF5", trust_remote_code=True)
audio = model("नमस्ते! संगीत की तरह जीवन भी खूबसूरत होता है, बस इसे सही ताल में जीना आना चाहिए.",
              ref_audio_path="prompts/PAN_F_HAPPY_00001.wav",
              ref_text="ਭਹੰਪੀ ਵਿੱਚ ਸਮਾਰਕਾਂ ਦੇ ਭਵਨ ਨਿਰਮਾਣ ਕਲਾ ਦੇ ਵੇਰਵੇ ਗੁੰਝਲਦਾਰ ਅਤੇ ਹੈਰਾਨ ਕਰਨ ਵਾਲੇ ਹਨ, ਜੋ ਮੈਨੂੰ ਖੁਸ਼ ਕਰਦੇ  ਹਨ।")
if audio.dtype == np.int16: audio = audio.astype(np.float32) / 32768.0
sf.write("namaste.wav", np.array(audio, dtype=np.float32), samplerate=24000)
```
Ungated alternatives:
- `SPRINGLab/SPRING_F5`: same call pattern plus `lang='hi'`; install from `git+https://github.com/ArigalaAdarsh/SPRING_F5.git`.
- `SPRINGLab/F5-Hindi-24KHz`: run with the rumourscape/F5-TTS fork, using `model_2500000.safetensors` + `vocab.txt` and the F5 small config.

**12. F5-TTS.** `pip install f5-tts`. The code is MIT, but the weights are CC-BY-NC-4.0.

**13. XTTS-v2.**
```bash
pip install coqui-tts
COQUI_TOS_AGREED=1 tts --model_name tts_models/multilingual/multi-dataset/xtts_v2 ...
```
or in Python, `os.environ["COQUI_TOS_AGREED"]="1"` before `TTS("tts_models/multilingual/multi-dataset/xtts_v2")`. The env var check is in `TTS/utils/manage.py`.

**14. Chatterbox Multilingual + Perth.**
```bash
pip install chatterbox-tts==0.1.7                               # V2 multilingual (t3_mtl23ls_v2) only
pip install git+https://github.com/resemble-ai/chatterbox.git   # master: adds t3_model="v3"
```
```python
import torchaudio as ta
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
m = ChatterboxMultilingualTTS.from_pretrained(device="cuda")            # master: (device="cuda", t3_model="v3")
wav = m.generate("नमस्ते, मैं आपके बैंक से बोल रहा हूँ।", language_id="hi",
                 audio_prompt_path="ref_hi.wav", exaggeration=0.5, cfg_weight=0.5)   # README tip: cfg_weight=0 if ref accent != language
ta.save("out.wav", wav, m.sr)                                           # m.sr = 24000; output is ALWAYS Perth-watermarked
```
Detecting the watermark (resemble-perth, MIT):
```python
import perth, librosa
wav, sr = librosa.load("out.wav", sr=None)
wm = perth.PerthImplicitWatermarker().get_watermark(wav, sample_rate=sr)   # 0.0 = none, 1.0 = watermarked
```
CLI: `perth input.wav --extract`.

Because every Chatterbox clip carries the watermark, the detector could learn the watermark instead of real spoof cues. To guard against this, also evaluate with the watermark degraded, for example after codec or channel passes.

**15. CosyVoice 2/3.**
```bash
git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git
conda create -n cosyvoice python=3.10
pip install -r requirements.txt
```
Then `snapshot_download('FunAudioLLM/Fun-CosyVoice3-0.5B-2512', local_dir='pretrained_models/Fun-CosyVoice3-0.5B')`. In Python: `sys.path.append('third_party/Matcha-TTS')`, `from cosyvoice.cli.cosyvoice import AutoModel`, `AutoModel(model_dir=...)`, `.inference_zero_shot(text, prompt_text, prompt_wav)`. CosyVoice3 prompt text uses the prefix `'You are a helpful assistant.<|endofprompt|>'`. The optional `ttsfrd` wheel is Linux cp310 only. No Hindi.

**16. Seed-VC.** `git clone https://github.com/Plachtaa/seed-vc && pip install -r requirements.txt` (python 3.10).
```bash
python inference.py --source src.wav --target ref.wav --output out_dir \
  --diffusion-steps 30 --length-adjust 1.0 --inference-cfg-rate 0.7 \
  --f0-condition False --auto-f0-adjust False --semi-tone-shift 0 --fp16 True
  # optional: --checkpoint <pth> --config <yml>
```
- The code default for `--diffusion-steps` is 30 (the README says 25).
- Leaving out `--checkpoint`/`--config` downloads `Plachta/Seed-VC` `DiT_seed_v2_uvit_whisper_small_wavenet_bigvgan_pruned.pth` + `config_dit_mel_seed_uvit_whisper_small_wavenet.yml` (22,050 Hz, BigVGAN 22k). This is the offline speech VC model.
- `DiT_uvit_tat_xlsr_ema.pth` (xlsr-tiny, 22,050 Hz, HiFT vocoder) is the real-time model.
- `--f0-condition True` switches to `..._whisper_base_f0_44k...ft_ema_v2.pth` (44.1 kHz, singing).
- No 16 kHz model exists, so resample before scoring.
- V2: `python inference_v2.py --source --target --output --diffusion-steps 25 --length-adjust 1.0 --intelligibility-cfg-rate 0.7 --similarity-cfg-rate 0.7 --convert-style true --anonymization-only false --top-p 0.9 --temperature 1.0 --repetition-penalty 1.0 [--cfm-checkpoint-path --ar-checkpoint-path]` (22,050 Hz).

**18. APIs.**
```bash
# Sarvam
curl -X POST https://api.sarvam.ai/text-to-speech -H "api-subscription-key: $SARVAM_API_KEY" -H "Content-Type: application/json" \
  -d '{"text":"नमस्ते, आपका खाता ब्लॉक हो गया है","language_code":"hi-IN","model":"bulbul:v3","speaker":"shubh","pace":1.0,"temperature":0.6,"speech_sample_rate":16000,"output_audio_codec":"wav"}'
# -> {"request_id":..,"audios":["<base64 wav>"]}
```
- `language_code`: bn-IN, en-IN, gu-IN, hi-IN, kn-IN, ml-IN, mr-IN, od-IN, pa-IN, ta-IN, te-IN.
- v3 speakers (lowercase): shubh (default), aditya, ritu, priya, neha, rahul, pooja, rohan, simran, kavya, amit, dev, ishita, shreya, ratan, varun, manan, sumit, roopa, kabir, aayan, ashutosh, advait, anand, tanya, tarun, sunny, mani, gokul, vijay, shruti, suhani, mohit, kavitha, rehan, soham, rupali.
- v2 speakers: anushka, manisha, vidya, arya, abhilash, karun, hitesh.
- `pitch`/`loudness` work only with v2. `pace` range is 0.5-2.0 on v3.
- Max text length: 2500 characters on v3, 1500 on v2.
- `speech_sample_rate`: 8000, 16000, 22050, 24000, 32000, 44100, 48000 (the last three are v3 REST only).
- `output_audio_codec`: mp3, linear16, mulaw, alaw, opus, flac, aac, wav.
```bash
# OpenAI
curl https://api.openai.com/v1/audio/speech -H "Authorization: Bearer $OPENAI_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini-tts","input":"नमस्ते, मैं बैंक से बोल रहा हूँ","voice":"marin","instructions":"Speak in Hindi with an Indian accent.","response_format":"wav"}' --output out.wav
# Gemini (Interactions API; unary returns a 24 kHz mono s16le WAV, base64)
curl -X POST "https://generativelanguage.googleapis.com/v1beta/interactions" -H "x-goog-api-key: $GEMINI_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"gemini-3.8-flash-tts","input":[{"type":"user_input","content":[{"type":"text","text":"नमस्ते, आपका OTP बताइए","annotations":[{"type":"speech_metadata","style":"calm, polite bank officer"}]}]}],
       "response_format":{"type":"audio","mime_type":"audio/wav","sample_rate":16000},"generation_config":{"speech_config":[{"voice":"Kore"}]}}' \
  | jq -r '[.steps[]|select(.type=="model_output")|.content[]|select(.type=="audio")]|last|.data' | base64 --decode > out.wav
```
Gemini voices: Zephyr, Puck, Charon, Kore, Fenrir, Leda, Orus, Aoede, Callirrhoe, Autonoe, Enceladus, Iapetus, Umbriel, Algieba, Despina, Erinome, Algenib, Rasalgethi, Laomedeia, Achernar, Alnilam, Schedar, Gacrux, Pulcherrima, Achird, Zubenelgenubi, Vindemiatrix, Sadachbia, Sadaltager, Sulafat. More are available from `GET /v1beta/voices`. The Python SDK equivalent is `google-genai` `client.interactions.create(...)`, reading `interaction.output_audio.data`.

**19. AudioSeal.** `pip install audioseal`
```python
from audioseal import AudioSeal
det = AudioSeal.load_detector("audioseal_detector_16bits")
prob, msg = det.detect_watermark(wav_BxCxT, sample_rate=16000)   # prob = P(watermarked); low level: det(wav) -> [B,2,frames], use [:,1,:] > 0.5
```
