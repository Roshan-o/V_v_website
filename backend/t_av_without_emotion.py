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
    from transformers import AutoTokenizer
except ImportError:
    ParlerTTSForConditionalGeneration = None
    AutoTokenizer = None

try:
    from svara_tts import SvaraTTS
except ImportError:
    SvaraTTS = None



class AudioTOVideo:
    def __init__(self,json_file,final_audio_file,video_file,output_video,src_audio_file):
        self.json_file=json_file
        self.video_file=video_file
        self.output_video=output_video
        self.final_audio_file=final_audio_file
        self.src_audio_file=src_audio_file
        self.temp_files = []

    def convert(self):
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


    def convert_with_sarvam(self,api_key):
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
        self.merge_with_video()

    def convert_with_xtts(self):
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
        self.merge_with_video()


    def convert_with_indic_tts(self, default_description="A female speaker with a clear and natural tone."):
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
        self.merge_with_video()

    def convert_with_svara_tts(self, language="te", default_age_group="adult", default_gender="female"):
        """
        Uses SvaraTTS (kenpath/svara-tts-v1) to generate audio.
        Handles different age groups by mapping them to speaker names if available,
        otherwise uses gender-based speakers.
        """
        if SvaraTTS is None:
            print("Error: 'svara_tts' library not found. Please install it.")
            return

        print("Loading SvaraTTS model: kenpath/svara-tts-v1...")
        model = SvaraTTS.from_pretrained("kenpath/svara-tts-v1")
        
        with open(self.json_file, "r", encoding="utf-8") as f:
            segments = json.load(f)

        # Initialize silent audio buffer
        total_duration = int(max(seg["end"] for seg in segments) * 1000)
        final_audio = AudioSegment.silent(duration=total_duration + 500)

        for i, seg in enumerate(segments):
            text = seg.get("translated_text", seg.get("text", ""))
            
            # Map age group and gender to speaker
            # Priority: 1. segment['speaker'], 2. segment['age_group'], 3. defaults
            age = seg.get("age_group", default_age_group).lower()
            gender = seg.get("gender", default_gender).lower()
            
            speaker = seg.get("speaker")
            if not speaker:
                # If the library supports specific age-based speaker IDs, they can be mapped here.
                # For now, we use the provided gender as the speaker ID as per the example.
                # If 'child' or 'elderly' is specified, we can try to use those as prefixes if the model supports it.
                if age in ["child", "elderly"]:
                    speaker = f"{age}_{gender}"
                else:
                    speaker = gender

            print(f"Generating segment {i} | Text: {text[:30]}... | Speaker: {speaker}")
            
            try:
                # Generate audio using SvaraTTS API
                audio_data = model.generate(
                    text=text,
                    language=language,
                    speaker=speaker
                )
                
                # Save to temporary file to load with pydub
                temp_filename = f"temp_svara_{i}.wav"
                model.save_wav(audio_data, temp_filename)
                
                speech = AudioSegment.from_wav(temp_filename)
                
                # Cleanup temp file
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)

                # Match duration with segment timeline
                start_time = int(seg["start"] * 1000)
                target_duration = int((seg["end"] - seg["start"]) * 1000)

                if len(speech) > target_duration:
                    speech = speech[:target_duration]
                else:
                    silence = AudioSegment.silent(duration=target_duration - len(speech))
                    speech += silence

                final_audio = final_audio.overlay(speech, position=start_time)
            
            except Exception as e:
                print(f"Error in Svara generation for segment {i}: {e}")

        # Export final audio
        print(f"Saving final Svara audio to {self.final_audio_file}...")
        final_audio.export(self.final_audio_file, format="wav")
        
        # Merge with video
        self.merge_with_video()


if __name__=="__main__":
    json_file = "output/translated_text.json"
    video_file = "video3[cry].mp4"
    output_video = "output/output_telugu_without_sarvam.mp4"
    final_audio_file = "output/final_telugu_audio.wav"
    src_audio_file="output/output_combined.mp3"

    final_audio_file_xtts="output/xtts/final_telugu_audio.wav"
    output_video_xtts="output/xtts/output_telugu_without_sarvam.mp4"

    # AudioTOVideo(json_file,final_audio_file,video_file,output_video).convert_with_sarvam("sk_omffrun1_uVmCyExpF9xp9Atcfni45GS4")
    # AudioTOVideo(json_file,final_audio_file_xtts,video_file,output_video_xtts,src_audio_file).convert_with_xtts()
    # Example using Svara-TTS (AI4Bharat Indic Parler-TTS) with age groups
    # AudioTOVideo(json_file, final_audio_file, video_file, output_video, src_audio_file).convert_with_svara_tts(
    #     default_age_group="child", 
    #     default_gender="female"
    # )
        # Example using Svara-TTS (AI4Bharat Indic Parler-TTS) with age groups
    AudioTOVideo(json_file, final_audio_file, video_file, output_video, src_audio_file).convert_with_svara_tts(
        default_age_group="child", 
        default_gender="female"
    )
    
    
    # AudioTOVideo(json_file,final_audio_file,video_file,output_video,src_audio_file).convert_xtts()
    # AudioTOVideo(json_file,final_audio_file,video_file,output_video).merge_with_video()

