# v-v\Scripts\activate.ps1 
from v_a import videotoaudio
from a_t import AudioTOText
from t_t import textConversion
from t_a import TextToAudio
from t_av_without_emotion import AudioTOVideo

if __name__=="__main__":
    #audio extraction
    video_path="video3[cry].mp4"
    OUTPUT_MP3 = "output/output_combined.mp3"
    src_text_path="output/source_text.json"
    dst_text_path="output/translated_text.json"
    output_video = "output/output_telugu.mp4"

    #audio extraction
    videotoaudio(video_path,OUTPUT_MP3).convert()
    print("audio extracted done")

    #text extraction
    AudioTOText(OUTPUT_MP3,src_text_path).convert()
    print("text extracted done")

    #text to text translation
    textConversion(src_text_path,dst_text_path).convert_with_sarvam("sk_omffrun1_uVmCyExpF9xp9Atcfni45GS4")
    print("text to text translation done")

    #audio to video translation
    AudioTOVideo(dst_text_path,video_path,output_video).convert()
    print("audio to video translation done")