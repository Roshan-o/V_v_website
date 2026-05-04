import whisper
import json
class AudioTOText:
    def __init__(self,audio_path,_text_src):
        self.audio_path=audio_path
        self.text_src=_text_src

    def convert(self):
        model = whisper.load_model("base")
        result = model.transcribe(self.audio_path)
        segments=[]
        for segment in result["segments"]:
            segments.append({"start":segment["start"],"end":segment["end"],"text":segment["text"]})
        with open(self.text_src, "w") as f:
            json.dump(segments,f)  
        return self.text_src

if __name__=="__main__":
    AudioTOText("audio.wav","source_text.json").convert()
