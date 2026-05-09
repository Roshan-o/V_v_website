import json
from gtts import gTTS
from pydub import AudioSegment
import subprocess
import os
from sarvamai import SarvamAI
import torch
import numpy as np
import soundfile as sf
from TTS.api import TTS
try:
    from parler_tts import ParlerTTSForConditionalGeneration
    from transformers import AutoTokenizer, AutoProcessor, AutoModel
except ImportError:
    ParlerTTSForConditionalGeneration = None
    AutoTokenizer = None
    AutoProcessor = None
    AutoModel = None



class AudioTOVideo:
    def __init__(self,json_file,final_audio_file,video_file,output_video,src_audio_file):
        self.json_file=json_file
        self.video_file=video_file
        self.output_video=output_video
        self.final_audio_file=final_audio_file
        self.src_audio_file=src_audio_file
        self.temp_files = []

    def convert(self, merge=True):
        with open(self.json_file, "r", encoding="utf-8") as f:
            segments = json.load(f)

        # Total duration
        total_duration = max(seg["end"] for seg in segments) * 1000
        final_audio = AudioSegment.silent(duration=total_duration)

        self.temp_files = []

        for i, seg in enumerate(segments):
            text = seg["text"]
            start_time = int(seg["start"] * 1000)

            # Telugu TTS
            tts = gTTS(text=text, lang='te')  #
            temp_file = f"temp_{i}.mp3"
            tts.save(temp_file)
            self.temp_files.append(temp_file)

            speech = AudioSegment.from_mp3(temp_file)

            # Match duration
            target_duration = int((seg["end"] - seg["start"]) * 1000)

            if len(speech) > target_duration:
                speech = speech[:target_duration]
            else:
                silence = AudioSegment.silent(duration=target_duration - len(speech))
                speech += silence

            final_audio = final_audio.overlay(speech, position=start_time)

        # Export audio
        final_audio.export(self.final_audio_file, format="wav")

        # Merge with video
        if merge:
            self.merge_with_video()

    def merge_with_video(self):
        command = [
            "ffmpeg",
            "-y", # Overwrite output file
            "-i", self.video_file,
            "-i", self.final_audio_file,
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            self.output_video
        ]

        subprocess.run(command)

        # Cleanup
        for f in self.temp_files:
            if os.path.exists(f):
                os.remove(f)

        print(f"Telugu dubbed video generated: {self.output_video}")


    def convert_with_sarvam(self,api_key, merge=True):
        import io
        client=SarvamAI(api_subscription_key=api_key)
        
        with open(self.json_file, "r", encoding="utf-8") as f:
            segments = json.load(f)
            
        # Total duration
        total_duration = max(seg["end"] for seg in segments) * 1000
        final_audio = AudioSegment.silent(duration=total_duration)
        
        self.temp_files = []

        for i, segment in enumerate(segments):
            print(f"Processing segment {i}: {segment['start']}s - {segment['end']}s")
            
            # Stream audio generation
            chunks = []
            for chunk in client.text_to_speech.convert_stream(
                text=segment["text"],
                target_language_code="te-IN",  # Telugu language code
                speaker="neha",
                model="bulbul:v3",
                output_audio_codec="mp3"
            ):
                chunks.append(chunk)
        
            # Combine chunks
            audio_data = b"".join(chunks)
            
            # Load as AudioSegment
            speech = AudioSegment.from_file(io.BytesIO(audio_data), format="mp3")
            
            # Match duration
            start_time = int(segment["start"] * 1000)
            target_duration = int((segment["end"] - segment["start"]) * 1000)

            if len(speech) > target_duration:
                speech = speech[:target_duration]
            else:
                silence = AudioSegment.silent(duration=target_duration - len(speech))
                speech += silence

            # Overlay
            final_audio = final_audio.overlay(speech, position=start_time)
            
            # (Optional) Save segment if needed, but we'll primarily use memory
            filename = f"output/segment_{i}_{segment['start']}s_{segment['end']}s.mp3"
            if not os.path.exists("output"):
                os.makedirs("output")
            with open(filename, "wb") as f:
                f.write(audio_data)
            self.temp_files.append(filename)
        
        # Export final audio
        print(f"Exporting final audio to {self.final_audio_file}...")
        final_audio.export(self.final_audio_file, format="wav")
        
        # Merge with video
        if merge:
            self.merge_with_video()

    def convert_with_xtts(self, merge=True):
        SAMPLE_RATE = 22050  # XTTS default

        device = "cuda" if torch.cuda.is_available() else "cpu"

        # ---------------------------
        # LOAD MODEL
        # ---------------------------
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

        # ---------------------------
        # LOAD JSON
        # ---------------------------
        with open(self.json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # ---------------------------
        # CREATE EMPTY AUDIO BUFFER
        # ---------------------------
        total_duration = max(item["end"] for item in data)
        total_samples = int(total_duration * SAMPLE_RATE)

        final_audio = np.zeros(total_samples, dtype=np.float32)

        # ---------------------------
        # GENERATE + PLACE AUDIO
        # ---------------------------
        for item in data:
            start = item["start"]
            end = item["end"]
            text = item.get("translated_text", item.get("text", ""))

            if not text.strip():
                continue

            # Generate speech
            wav = tts.tts(
                text=text,
                speaker_wav=self.src_audio_file,
                language="te"
            )

            wav = np.array(wav)

            # Convert time → samples
            start_sample = int(start * SAMPLE_RATE)
            end_sample = start_sample + len(wav)

            # Prevent overflow
            if end_sample > len(final_audio):
                end_sample = len(final_audio)
                wav = wav[:end_sample - start_sample]

            # Insert into timeline
            final_audio[start_sample:end_sample] = wav

        # ---------------------------
        # SAVE FINAL AUDIO
        # ---------------------------
        sf.write(self.final_audio_file, final_audio, SAMPLE_RATE)
        
        # Merge with video
        if merge:
            self.merge_with_video()


    def convert_with_indic_tts(self, default_description="A female speaker with a clear and natural tone.", merge=True):
        """
        Uses AI4Bharat's Indic Parler-TTS for high-quality, customizable voice synthesis.
        Allows specifying voice characteristics (male, female, young, etc.) via natural language descriptions.
        """
        if ParlerTTSForConditionalGeneration is None or AutoTokenizer is None:
            print("Error: 'parler_tts' or 'transformers' not installed. Please install them using:")
            print("pip install git+https://github.com/huggingface/parler-tts.git transformers")
            return

        device = "cuda" if torch.cuda.is_available() else "cpu"
        repo_id = "ai4bharat/indic-parler-tts"
        
        print(f"Loading Indic Parler-TTS model: {repo_id}...")
        model = ParlerTTSForConditionalGeneration.from_pretrained(repo_id).to(device)
        tokenizer = AutoTokenizer.from_pretrained(repo_id)
        sample_rate = model.config.sampling_rate

        with open(self.json_file, "r", encoding="utf-8") as f:
            segments = json.load(f)

        # Calculate total duration and initialize buffer
        total_duration = max(seg["end"] for seg in segments)
        total_samples = int(total_duration * sample_rate)
        final_audio_np = np.zeros(total_samples, dtype=np.float32)

        for i, seg in enumerate(segments):
            text = seg.get("translated_text", seg.get("text", ""))
            # You can specify "voice_description" per segment in your JSON to change voices
            # Example: "A young girl with a cheerful voice" or "An elderly man with a deep voice"
            description = seg.get("voice_description", default_description)
            
            print(f"Generating segment {i} | Start: {seg['start']}s | Voice: {description}")
            
            input_ids = tokenizer(description, return_tensors="pt").input_ids.to(device)
            prompt_input_ids = tokenizer(text, return_tensors="pt").input_ids.to(device)

            with torch.no_grad():
                generation = model.generate(input_ids=input_ids, prompt_input_ids=prompt_input_ids)
            
            audio_arr = generation.cpu().numpy().squeeze()

            # Time to samples mapping
            start_sample = int(seg["start"] * sample_rate)
            target_duration_samples = int((seg["end"] - seg["start"]) * sample_rate)

            # Align audio with segment duration
            if len(audio_arr) > target_duration_samples:
                audio_arr = audio_arr[:target_duration_samples]
            
            end_sample = start_sample + len(audio_arr)
            if end_sample > total_samples:
                end_sample = total_samples
                audio_arr = audio_arr[:end_sample - start_sample]

            final_audio_np[start_sample:end_sample] = audio_arr

        # Export final audio
        print(f"Saving final audio to {self.final_audio_file}...")
        sf.write(self.final_audio_file, final_audio_np, sample_rate)
        
        # Merge with video
        if merge:
            self.merge_with_video()

    def convert_with_indic_f5(self,merge=True):
        """
        Uses AI4Bharat's Indic-F5 for high-quality, zero-shot voice synthesis.
        Requires reference audio files and their corresponding transcripts.
        """
        if AutoModel is None:
            print("Error: 'transformers' not installed. Please install it.")
            return

        device = "cuda" if torch.cuda.is_available() else "cpu"
        repo_id = "ai4bharat/IndicF5"
        
        print(f"Loading Indic-F5 model: {repo_id}...")
        # Use trust_remote_code=True for custom architectures
        model = AutoModel.from_pretrained(repo_id, trust_remote_code=True).to(device)
        
        with open(self.json_file, "r", encoding="utf-8") as f:
            segments = json.load(f)

        # Initialize silent audio buffer
        # Indic-F5 typically outputs at 24000Hz
        SAMPLE_RATE = 24000
        total_duration = max(seg["end"] for seg in segments)
        total_samples = int(total_duration * SAMPLE_RATE)
        final_audio_np = np.zeros(total_samples, dtype=np.float32)

        # Use the first segment's original text as reference text if available
        # or use a default if not. F5 needs the transcript of the reference audio clip.
        default_ref_text = segments[0].get("text", "") if segments else ""

        for i, seg in enumerate(segments):
            text = seg.get("translated_text", seg.get("text", ""))
            
            # Using the source audio file as reference for cloning
            ref_audio = self.src_audio_file
            # The transcript of the reference audio (using the original text of this segment or the first one)
            ref_text = seg.get("text", default_ref_text)

            print(f"Generating segment {i} | Text: {text[:30]}... | Cloning from source audio: {ref_audio}")
            
            try:
                # Indic-F5 call: audio = model(text, ref_audio_path, ref_text)
                audio_output = model(
                    text,
                    ref_audio_path=ref_audio,
                    ref_text=ref_text
                )
                
                # Normalize if needed (int16 -> float32)
                if hasattr(audio_output, "dtype") and audio_output.dtype == np.int16:
                    audio_arr = audio_output.astype(np.float32) / 32768.0
                else:
                    audio_arr = np.array(audio_output, dtype=np.float32)

                # Time to samples mapping
                start_sample = int(seg["start"] * SAMPLE_RATE)
                target_duration_samples = int((seg["end"] - seg["start"]) * SAMPLE_RATE)

                # Align audio with segment duration
                if len(audio_arr) > target_duration_samples:
                    audio_arr = audio_arr[:target_duration_samples]
                
                end_sample = start_sample + len(audio_arr)
                if end_sample > total_samples:
                    end_sample = total_samples
                    audio_arr = audio_arr[:end_sample - start_sample]

                final_audio_np[start_sample:end_sample] = audio_arr
            
            except Exception as e:
                print(f"Error generating Indic-F5 segment {i}: {e}")

        # Export final audio
        print(f"Saving final Indic-F5 audio to {self.final_audio_file}...")
        sf.write(self.final_audio_file, final_audio_np, SAMPLE_RATE)
        
        if merge:
            self.merge_with_video()
    
    def convert_with_sooktam2(self, language="hindi", merge=True):
        """
        Uses BharatGenAI's Sooktam2 for high-quality voice synthesis.
        Allows for zero-shot voice cloning using a reference audio file.
        """
        if AutoModel is None:
            print("Error: 'transformers' not installed. Please install it.")
            return

        device = "cuda" if torch.cuda.is_available() else "cpu"
        repo_id = "bharatgenai/sooktam2"
        
        print(f"Loading Sooktam2 model: {repo_id}...")
        # Download the necessary repo code files to ensure 'src' directory is present in cache
        from huggingface_hub import snapshot_download
        model_path = snapshot_download(repo_id=repo_id, allow_patterns=["*.py", "src/*", "*.yaml", "*.json", "*.txt"])
        
        import sys, os
        src_path = os.path.join(model_path, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

        # Load model (auto-downloads checkpoint + vocab from HuggingFace)
        model = AutoModel.from_pretrained(
            repo_id,
            trust_remote_code=True,
        ).to(device)

        with open(self.json_file, "r", encoding="utf-8") as f:
            segments = json.load(f)

        # Initialize audio buffer variables
        final_audio_np = None
        target_sr = None
        
        # Use the first segment's original text as reference text if available
        default_ref_text = segments[0].get("text", "") if segments else ""

        for i, seg in enumerate(segments):
            text = seg.get("translated_text", seg.get("text", ""))
            ref_audio = self.src_audio_file
            ref_text = seg.get("text", default_ref_text)

            print(f"Generating segment {i} | Text: {text[:30]}... | Cloning from source audio: {ref_audio}")
            
            try:
                # Sooktam2 inference: wav, sr, _ = model.infer(...)
                # CLS tokenization is handled inside utils_infer via cls_tokenizer_v2
                wav, sr, _ = model.infer(
                    ref_file=ref_audio,
                    ref_text=ref_text,
                    gen_text=text,
                    tokenizer="cls",
                    cls_language=language
                )
                
                # Initialize buffer based on sample rate of first successful segment
                if final_audio_np is None:
                    target_sr = sr
                    total_duration = max(s["end"] for s in segments)
                    total_samples = int(total_duration * target_sr)
                    final_audio_np = np.zeros(total_samples, dtype=np.float32)

                # Convert to numpy and normalize if needed
                audio_arr = np.array(wav, dtype=np.float32)
                
                # Time to samples mapping
                start_sample = int(seg["start"] * target_sr)
                target_duration_samples = int((seg["end"] - seg["start"]) * target_sr)

                # Align audio with segment duration
                if len(audio_arr) > target_duration_samples:
                    audio_arr = audio_arr[:target_duration_samples]
                
                end_sample = start_sample + len(audio_arr)
                if end_sample > len(final_audio_np):
                    end_sample = len(final_audio_np)
                    audio_arr = audio_arr[:end_sample - start_sample]

                final_audio_np[start_sample:end_sample] = audio_arr
            
            except Exception as e:
                print(f"Error generating Sooktam2 segment {i}: {e}")

        if final_audio_np is not None:
            # Export final audio
            print(f"Saving final Sooktam2 audio to {self.final_audio_file}...")
            sf.write(self.final_audio_file, final_audio_np, target_sr)
            
            if merge:
                self.merge_with_video()


    def convert_with_sooktam2_fast(self, language="telugu", merge=True, max_workers=2):
        """
        Uses Sooktam2 for voice synthesis with FP16 precision and concurrent threading
        to dramatically speed up processing time.
        """
        if AutoModel is None:
            print("Error: 'transformers' not installed. Please install it.")
            return

        device = "cuda" if torch.cuda.is_available() else "cpu"
        repo_id = "bharatgenai/sooktam2"
        
        print(f"Loading Sooktam2 model (FP16 optimized): {repo_id}...")
        from huggingface_hub import snapshot_download
        model_path = snapshot_download(repo_id=repo_id, allow_patterns=["*.py", "src/*", "*.yaml", "*.json", "*.txt"])
        
        import sys, os
        src_path = os.path.join(model_path, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

        # Load model in FP16 to double speed and halve VRAM usage
        # (Only do FP16 if CUDA is available)
        dtype = torch.float16 if device == "cuda" else torch.float32
        model = AutoModel.from_pretrained(
            repo_id,
            trust_remote_code=True,
            torch_dtype=dtype,
        ).to(device)

        with open(self.json_file, "r", encoding="utf-8") as f:
            segments = json.load(f)

        # Use the first segment's original text as reference text if available
        default_ref_text = segments[0].get("text", "") if segments else ""
        
        # We need the sample rate to initialize the final array, we will do the first segment manually 
        # to get the sample rate, then thread the rest.
        if not segments:
            return

        target_sr = None
        final_audio_np = None

        print(f"Starting sequential generation (FP16)...")
        
        for i, seg in enumerate(segments):
            text = seg.get("translated_text", seg.get("text", ""))
            ref_audio = self.src_audio_file
            ref_text = seg.get("text", default_ref_text)
            
            print(f"Processing segment {i} | Text: {text[:30]}...")
            try:
                wav, sr, _ = model.infer(
                    ref_file=ref_audio,
                    ref_text=ref_text,
                    gen_text=text,
                    tokenizer="cls",
                    cls_language=language
                )
                
                audio_arr = np.array(wav, dtype=np.float32)
                
                # Initialize the big buffer on the first successful completion
                if final_audio_np is None:
                    target_sr = sr
                    total_duration = max(s["end"] for s in segments)
                    total_samples = int(total_duration * target_sr)
                    final_audio_np = np.zeros(total_samples, dtype=np.float32)

                # Time to samples mapping
                start_sample = int(seg["start"] * target_sr)
                target_duration_samples = int((seg["end"] - seg["start"]) * target_sr)

                # Align audio with segment duration
                if len(audio_arr) > target_duration_samples:
                    audio_arr = audio_arr[:target_duration_samples]
                
                end_sample = start_sample + len(audio_arr)
                if end_sample > len(final_audio_np):
                    end_sample = len(final_audio_np)
                    audio_arr = audio_arr[:end_sample - start_sample]

                final_audio_np[start_sample:end_sample] = audio_arr

            except Exception as e:
                print(f"Error generating Sooktam2 segment {i}: {e}")

        if final_audio_np is not None:
            # Export final audio
            print(f"Saving final Sooktam2 audio to {self.final_audio_file}...")
            sf.write(self.final_audio_file, final_audio_np, target_sr)
            
            if merge:
                self.merge_with_video()

    def convert_with_svara_tts(self, default_language="Telugu", default_gender="Female", default_age_group=None, merge=True):
        """
        Uses kenpath/svara-tts-v1 for high-quality voice synthesis.
        """
        try:
            from snac import SNAC
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError:
            print("Error: 'snac' or 'transformers' not installed. Please install them.")
            return

        device = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
        model_name = "kenpath/svara-tts-v1"

        print(f"Loading SNAC model...")
        snac_model = SNAC.from_pretrained("hubertsiuzdak/snac_24khz").to(device)
        
        print(f"Loading Svara-TTS model: {model_name}...")
        try:
            from transformers import BitsAndBytesConfig
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16
            )
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                device_map="auto",
                quantization_config=quantization_config,
                low_cpu_mem_usage=True
            )
        except Exception as e:
            print(f"Could not load in 4-bit (install bitsandbytes). Falling back to 16-bit accelerate: {e}")
            try:
                model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    device_map="auto",
                    torch_dtype=torch.float16,
                    low_cpu_mem_usage=True
                )
            except Exception as e2:
                print(f"Loading with accelerate failed, falling back to normal load: {e2}")
                model = AutoModelForCausalLM.from_pretrained(model_name).to(device)
        
        tokenizer = AutoTokenizer.from_pretrained(model_name)

        with open(self.json_file, "r", encoding="utf-8") as f:
            segments = json.load(f)

        SAMPLE_RATE = 24000
        total_duration = max(seg["end"] for seg in segments)
        total_samples = int(total_duration * SAMPLE_RATE)
        final_audio_np = np.zeros(total_samples, dtype=np.float32)

        def redistribute_codes(code_list):
            """De-interleave SNAC tokens into 3 hierarchical levels"""
            codes_lvl = [[] for _ in range(3)]
            llm_codebook_offsets = [j * 4096 for j in range(7)]

            for j in range(0, len(code_list), 7):
                codes_lvl[0].append(code_list[j] - llm_codebook_offsets[0])
                codes_lvl[1].append(code_list[j+1] - llm_codebook_offsets[1])
                codes_lvl[1].append(code_list[j+4] - llm_codebook_offsets[4])
                codes_lvl[2].append(code_list[j+2] - llm_codebook_offsets[2])
                codes_lvl[2].append(code_list[j+3] - llm_codebook_offsets[3])
                codes_lvl[2].append(code_list[j+5] - llm_codebook_offsets[5])
                codes_lvl[2].append(code_list[j+6] - llm_codebook_offsets[6])

            hierarchical_codes = []
            for lvl_codes in codes_lvl:
                tensor = torch.tensor(lvl_codes, dtype=torch.long, device=device).unsqueeze(0)
                hierarchical_codes.append(tensor)

            with torch.no_grad():
                audio_hat = snac_model.decode(hierarchical_codes)

            return audio_hat

        for i, seg in enumerate(segments):
            text = seg.get("translated_text", seg.get("text", ""))
            if not text.strip():
                continue

            language = seg.get("language", default_language)
            gender = seg.get("gender", default_gender)

            print(f"Generating segment {i} | Text: {text[:30]}... | Voice: {language} ({gender})")
            
            try:
                # Format the prompt for Svara-TTS
                voice = f"{language} ({gender})"
                formatted_text = f"<|audio|> {voice}: {text}<|eot_id|>"
                prompt = "<custom_token_3>" + formatted_text + "<custom_token_4><custom_token_5>"

                # Tokenize the prompt
                input_ids = tokenizer(prompt, return_tensors="pt").input_ids

                # Add special tokens
                start_token = torch.tensor([[128259]], dtype=torch.int64)
                end_tokens = torch.tensor([[128009, 128260, 128261, 128257]], dtype=torch.int64)

                modified_input_ids = torch.cat([start_token, input_ids, end_tokens], dim=1).to(device)

                # Generate speech tokens
                with torch.no_grad():
                    generated_ids = model.generate(
                        input_ids=modified_input_ids,
                        max_new_tokens=800,
                        do_sample=True,
                        temperature=0.7,
                        top_p=0.95,
                        repetition_penalty=1.2,
                        num_return_sequences=1,
                        eos_token_id=128258,
                    )

                START_OF_SPEECH_TOKEN = 128257
                END_OF_SPEECH_TOKEN = 128258
                AUDIO_CODE_BASE_OFFSET = 128266
                AUDIO_CODE_MAX = AUDIO_CODE_BASE_OFFSET + (7 * 4096) - 1

                row = generated_ids[0]
                token_indices = (row == START_OF_SPEECH_TOKEN).nonzero(as_tuple=True)[0]

                if len(token_indices) > 0:
                    start_idx = token_indices[-1].item() + 1
                    audio_tokens = row[start_idx:]
                    audio_tokens = audio_tokens[audio_tokens != END_OF_SPEECH_TOKEN]
                    audio_tokens = audio_tokens[audio_tokens != 128263]  # PAD token

                    valid_mask = (audio_tokens >= AUDIO_CODE_BASE_OFFSET) & (audio_tokens <= AUDIO_CODE_MAX)
                    audio_tokens = audio_tokens[valid_mask]

                    snac_tokens = audio_tokens.tolist()
                    snac_tokens = [t - AUDIO_CODE_BASE_OFFSET for t in snac_tokens]

                    new_length = (len(snac_tokens) // 7) * 7
                    snac_tokens = snac_tokens[:new_length]
                    
                    if len(snac_tokens) == 0:
                        print(f"No valid SNAC tokens found for segment {i} after processing")
                        continue
                        
                    audio_waveform = redistribute_codes(snac_tokens)
                    audio_arr = audio_waveform.detach().squeeze().to("cpu").numpy()

                    # Align audio with segment duration
                    start_sample = int(seg["start"] * SAMPLE_RATE)
                    target_duration_samples = int((seg["end"] - seg["start"]) * SAMPLE_RATE)

                    if len(audio_arr) > target_duration_samples:
                        audio_arr = audio_arr[:target_duration_samples]
                    
                    end_sample = start_sample + len(audio_arr)
                    if end_sample > total_samples:
                        end_sample = total_samples
                        audio_arr = audio_arr[:end_sample - start_sample]

                    final_audio_np[start_sample:end_sample] = audio_arr
                else:
                    print(f"No speech tokens found for segment {i}")

            except Exception as e:
                print(f"Error generating svara-tts segment {i}: {e}")

        print(f"Saving final svara-tts audio to {self.final_audio_file}...")
        sf.write(self.final_audio_file, final_audio_np, SAMPLE_RATE)
        
        if merge:
            self.merge_with_video()


if __name__=="__main__":
    json_file = "output/translated_text.json"
    video_file = "video3[cry].mp4"
    output_video = "output/output_telugu_without_sarvam.mp4"
    final_audio_file = "output/final_telugu_audio.wav"
    src_audio_file="output/output_combined.mp3"

    final_audio_file_xtts="output/xtts/final_telugu_audio.wav"
    output_video_xtts="output/xtts/output_telugu_without_sarvam.mp4"
    final_audio_file_svara="output/svara/final_telugu_audio.wav"
    output_video_svara="output/svara/output_telugu_without_sarvam.mp4"

    # Example using Svara-TTS (kenpath/svara-tts-v1)
    AudioTOVideo(json_file, final_audio_file_svara, video_file, output_video_svara, src_audio_file).convert_with_svara_tts(
        default_language="Telugu", 
        default_gender="Male"
    )
