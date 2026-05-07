import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import soundfile as sf
import os
import numpy as np

class SvaraTTS:
    def __init__(self, model_id):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading SvaraTTS model on {self.device}...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float16 if self.device == "cuda" else torch.float32).to(self.device)
        
        try:
            from snac import SNAC
            self.snac_model = SNAC.from_pretrained("hubertsiuzdak/snac_24khz").to(self.device).eval()
        except ImportError:
            print("Warning: 'snac' library not found. Audio decoding might fail.")
            self.snac_model = None

    @classmethod
    def from_pretrained(cls, model_id):
        return cls(model_id)

    def generate(self, text, language="te", speaker="female"):
        # Format the prompt for Svara-TTS
        # Svara-TTS usually expects the language and speaker in the prompt or as tags
        # Using the standard Orpheus-style formatting
        prompt = f"{text} <{language}> <{speaker}>"
        
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            output_tokens = self.model.generate(
                **inputs,
                max_new_tokens=2048, # Adjust as needed
                do_sample=True,
                top_k=50,
                top_p=0.95
            )
            
        # Extract audio tokens (assuming they start after the input tokens)
        audio_tokens = output_tokens[0][inputs.input_ids.shape[-1]:]
        
        if self.snac_model is None:
            raise ImportError("SNAC decoder is required for audio generation.")

        # Decode using SNAC
        # Note: This is a simplified version. Actual Orpheus/Svara decoding might involve 
        # multiple levels of SNAC tokens.
        with torch.no_grad():
            # Many Orpheus models output SNAC indices directly
            # We need to reshape them for the SNAC decoder
            # Typically 24khz SNAC has 4 layers
            # Here we assume a single stream for simplicity, but real implementation varies.
            audio_tokens = audio_tokens.view(1, 1, -1) 
            audio = self.snac_model.decode(audio_tokens)
            
        return audio.cpu().numpy().squeeze()

    def save_wav(self, audio, path):
        # Default sample rate for Svara-TTS/SNAC 24khz is 24000
        sf.write(path, audio, 24000)
