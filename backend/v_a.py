from moviepy import VideoFileClip

class videotoaudio:
    def __init__(self,video_path,audio_path):
        self.video_path=video_path
        self.audio_path=audio_path

    def convert(self):
        video = VideoFileClip(self.video_path)
        audio = video.audio
        # Convert to mono and 16kHz for better Whisper compatibility
        audio.write_audiofile(self.audio_path, fps=16000, nbytes=2, codec='pcm_s16le', ffmpeg_params=["-ac", "1"])
        return self.audio_path


if __name__=="__main__":
    video_path="Video Project 2.mp4"
    videotoaudio(video_path).convert()