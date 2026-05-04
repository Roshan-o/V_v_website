from moviepy import VideoFileClip

class videotoaudio:
    def __init__(self,video_path,audio_path):
        self.video_path=video_path
        self.audio_path=audio_path

    def convert(self):
        video = VideoFileClip(self.video_path)
        audio = video.audio
        audio_path=self.audio_path
        audio.write_audiofile(audio_path)
        return audio_path

if __name__=="__main__":
    video_path="Video Project 2.mp4"
    videotoaudio(video_path).convert()