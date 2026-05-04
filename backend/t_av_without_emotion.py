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



class AudioTOVideo:
    def __init__(self,json_file,final_audio_file,video_file,output_video):
        self.json_file=json_file
        self.video_file=video_file
        self.output_video=output_video
        self.final_audio_file=final_audio_file
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

    def convert_xtts(self, reference_audio):
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
                speaker_wav=reference_audio,
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


if __name__=="__main__":
    json_file = "output/translated_text.json"
    video_file = "video3[cry].mp4"
    output_video = "output/output_telugu_without_sarvam.mp4"
    final_audio_file = "output/final_telugu_audio.wav"

    # AudioTOVideo(json_file,final_audio_file,video_file,output_video).convert_with_sarvam("sk_omffrun1_uVmCyExpF9xp9Atcfni45GS4")
    AudioTOVideo(json_file,final_audio_file,video_file,output_video).convert_xtts("output/ouput_combined.mp3")
    # AudioTOVideo(json_file,final_audio_file,video_file,output_video).merge_with_video()

