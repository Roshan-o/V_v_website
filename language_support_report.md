# Language Support Report: End-to-End Dubbing Pipeline

This report outlines the language capabilities of your video translation and dubbing pipeline, breaking down the supported languages for each individual module and calculating the **overall end-to-end compatibility**.

Your pipeline relies on three core AI models:
1. **ASR (Speech-to-Text):** Whisper (OpenAI)
2. **Translation:** IndicTrans2 (AI4Bharat)
3. **TTS (Text-to-Speech):** Svara-TTS

---

## 1. Whisper (ASR - Source Language)
OpenAI's Whisper is a highly robust multilingual ASR system. It dictates what **Source Languages** your application can accept.

*   **Global Support:** Supports 99 languages globally.
*   **Indian Languages Supported:** Hindi, Bengali, Tamil, Telugu, Marathi, Malayalam, Kannada, Gujarati, Punjabi, Urdu, Nepali, Assamese, Odia, Sanskrit, and Sindhi.
*   **Other Major Languages:** English, Spanish, French, German, Mandarin, Japanese, etc.

## 2. IndicTrans2 (Machine Translation - Source & Target)
IndicTrans2 acts as the bridge. It translates the transcribed text into the desired target language. It restricts the pipeline to English and the 22 scheduled official languages of India.

**Supported Translation Directions:**
*   English <-> Indic Language
*   Indic Language <-> Indic Language

**The 22 Supported Indian Languages are:**
Assamese, Bengali, Bodo, Dogri, Gujarati, Hindi, Kannada, Kashmiri, Konkani, Maithili, Malayalam, Manipuri, Marathi, Nepali, Odia, Punjabi, Sanskrit, Santali, Sindhi, Tamil, Telugu, and Urdu.

*(Note: If Whisper transcribes a foreign language like Spanish, IndicTrans2 cannot natively translate Spanish -> Telugu. The source language must be English or one of the 22 Indic languages).*

## 3. Svara-TTS (Text-to-Speech - Target Language)
Svara-TTS handles the final voice generation. Like most modern Indian TTS models, it specializes in English and the most prominent Indian languages.

**Commonly Supported Languages:**
English, Hindi, Bengali, Gujarati, Marathi, Kannada, Malayalam, Tamil, Telugu, Odia, Punjabi, and Urdu.

---

## End-to-End Pipeline Compatibility

For a video to be successfully processed from start to finish, the languages must satisfy the intersection of all three models. 

### Valid Source Languages (Audio Input)
To be understood by Whisper AND translatable by IndicTrans2, the original video's audio must be in:
*   **English**
*   **Major Indian Languages:** Hindi, Bengali, Tamil, Telugu, Marathi, Malayalam, Kannada, Gujarati, Punjabi, Urdu, Odia, Assamese, Nepali, Sanskrit, Sindhi.

### Valid Target Languages (Audio Output)
To be translatable by IndicTrans2 AND vocalized by Svara-TTS, the final desired language can be:
*   **English**
*   **Hindi**
*   **Telugu**
*   **Tamil**
*   **Kannada**
*   **Malayalam**
*   **Marathi**
*   **Gujarati**
*   **Bengali**
*   **Punjabi**
*   **Odia**
*   **Urdu**

### What Will Not Work
1. **Foreign Source -> Indic Target:** (e.g., Spanish Video -> Telugu Voice). *Whisper will transcribe the Spanish, but IndicTrans2 will fail to translate it.*
2. **Indic Source -> Foreign Target:** (e.g., Hindi Video -> French Voice). *IndicTrans2 does not output French.*
3. **Indic Source -> Rare Indic Target:** (e.g., Hindi Video -> Bodo Voice). *IndicTrans2 will translate to Bodo, but Svara-TTS may fail to generate a voice for Bodo.*

---
