import os
import subprocess
import sys
from t_av_without_emotion import AudioTOVideo

class VideoLipSync:
    """
    Module for performing Lip Sync on a video using generated audio.
    Uses logic from AudioTOVideo for audio generation and Wav2Lip for lip syncing.
    """
    def __init__(self, json_file, video_file, output_video, src_audio_file, checkpoint_path=None):
        self.json_file = json_file
        self.video_file = video_file
        self.output_video = output_video
        self.src_audio_file = src_audio_file
        
        # Determine the base directory (v_v_website)
        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.wav2lip_dir = os.path.join(self.base_dir, "Wav2Lip")
        
        # Default checkpoint path if not provided
        if checkpoint_path is None:
            # Common default path for Wav2Lip GAN checkpoint
            self.checkpoint_path = os.path.join(self.wav2lip_dir, "checkpoints", "wav2lip_gan.pth")
        else:
            self.checkpoint_path = checkpoint_path
            
        self.final_audio_file = os.path.abspath("temp_final_audio.wav")
        
        # Initialize AudioTOVideo generator
        self.audio_generator = AudioTOVideo(
            json_file=self.json_file,
            final_audio_file=self.final_audio_file,
            video_file=self.video_file,
            output_video=self.output_video, # Final output will be handled by Wav2Lip
            src_audio_file=self.src_audio_file
        )

    def generate_audio(self, method="default", **kwargs):
        """
        Generates audio using one of the methods from AudioTOVideo.
        Methods: 'default', 'sarvam', 'xtts', 'indic_tts', 'svara_tts'
        """
        print(f"Generating audio using method: {method}...")
        
        if method == "default":
            self.audio_generator.convert(merge=False)
        elif method == "sarvam":
            api_key = kwargs.get("api_key", "sk_omffrun1_uVmCyExpF9xp9Atcfni45GS4")
            self.audio_generator.convert_with_sarvam(api_key, merge=False)
        elif method == "xtts":
            self.audio_generator.convert_with_xtts(merge=False)
        elif method == "indic_tts":
            description = kwargs.get("description", "A female speaker with a clear and natural tone.")
            self.audio_generator.convert_with_indic_tts(description, merge=False)
        elif method == "svara_tts":
            language = kwargs.get("language", "te")
            age_group = kwargs.get("age_group", "adult")
            gender = kwargs.get("gender", "female")
            self.audio_generator.convert_with_svara_tts(language, age_group, gender, merge=False)
        elif method == "indic_f5":
            self.audio_generator.convert_with_indic_f5(
                merge=False
            )
        else:
            print(f"Unknown audio generation method: {method}. Falling back to default.")
            self.audio_generator.convert(merge=False)

    def sync(self):
        """
        Performs the lip sync process using Wav2Lip.
        """
        if not os.path.exists(self.final_audio_file):
            print(f"Error: Final audio file {self.final_audio_file} not found. Generate audio first.")
            return

        if not os.path.exists(self.checkpoint_path):
            print(f"Warning: Checkpoint not found at {self.checkpoint_path}.")
            print("Please ensure the Wav2Lip checkpoint is placed in the checkpoints folder.")
            # We'll try to run anyway in case the user has it elsewhere or the path is relative to script
        
        print("Starting Wav2Lip inference...")
        inference_script = os.path.join(self.wav2lip_dir, "inference.py")
        
        # Prepare Wav2Lip command
        command = [
            sys.executable,
            inference_script,
            "--checkpoint_path", os.path.abspath(self.checkpoint_path),
            "--face", os.path.abspath(self.video_file),
            "--audio", os.path.abspath(self.final_audio_file),
            "--outfile", os.path.abspath(self.output_video)
        ]
        
        print(f"Running command: {' '.join(command)}")
        
        try:
            # Wav2Lip needs to be run from its directory to find its modules correctly
            process = subprocess.Popen(
                command,
                cwd=self.wav2lip_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Stream output to console
            for line in process.stdout:
                print(f"[Wav2Lip] {line.strip()}")
                
            process.wait()
            
            if process.returncode == 0:
                print(f"\nSUCCESS: Lip-synced video generated at {self.output_video}")
            else:
                print(f"\nFAILED: Wav2Lip exited with code {process.returncode}")
                
        except Exception as e:
            print(f"An error occurred during Lip Sync: {str(e)}")
        
        finally:
            self.cleanup()

    def cleanup(self):
        """
        Removes temporary files created during the process.
        """
        print("Cleaning up temporary files...")
        temp_files = [self.final_audio_file]
        for f in temp_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass

if __name__ == "__main__":
    # Test parameters
    json_file = "output/translated_text.json"
    video_file = "video3[cry].mp4"
    output_video = "output/output_lipsynced.mp4"
    src_audio_file = "output/output_combined.mp3"
    
    # Initialize and run
    ls = VideoLipSync(json_file, video_file, output_video, src_audio_file)
    ls.generate_audio(method="svara_tts") # Example using svara_tts as per user's current work
    ls.sync()
