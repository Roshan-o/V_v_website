import whisper
import json
class AudioTOText:
    def __init__(self, audio_path, _text_src, language="English"):
        self.audio_path = audio_path
        self.text_src = _text_src
        self.language = language
        
        # Mapping full language names to Whisper codes
        self.lang_map = {
            "English": "en",
            "Hindi": "hi",
            "Telugu": "te",
            "Tamil": "ta",
            "Kannada": "kn",
            "Malayalam": "ml",
            "Marathi": "mr",
            "Bengali": "bn",
            "Gujarati": "gu",
            "Punjabi": "pa"
        }

    def convert(self):
        model = whisper.load_model("medium")
        
        # Get language code from map, default to None (auto-detect) if not found
        # Using case-insensitive lookup
        whisper_lang = None
        target_lang = self.language.strip().capitalize()
        if target_lang in self.lang_map:
            whisper_lang = self.lang_map[target_lang]
        
        print(f"Starting transcription for {self.audio_path} in {self.language} (mapped to: {whisper_lang})")

        
        # Use language code if found in map
        # fp16=False is more stable on various hardware
        # condition_on_previous_text=False helps if Whisper gets stuck or stops early
        transcribe_options = {
            "language": whisper_lang,
            "fp16": False,
            "condition_on_previous_text": False,
            "verbose": True
        }
        
        if not whisper_lang:
            del transcribe_options["language"]
            
        result = model.transcribe(self.audio_path, **transcribe_options)
            
        segments = []
        for segment in result["segments"]:
            segments.append({
                "start": segment["start"], 
                "end": segment["end"], 
                "text": segment["text"]
            })

            
        with open(self.text_src, "w", encoding='utf-8') as f:
            json.dump(segments, f, ensure_ascii=False, indent=4)  
        return self.text_src

if __name__ == "__main__":
    AudioTOText("audio.wav", "source_text.json").convert()

