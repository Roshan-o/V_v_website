# from transformers import pipeline
from aiohttp import client
import json
from transformers import AutoTokenizer
# from transformers import M2M100Tokenizer
from transformers import AutoModelForSeq2SeqLM
from sarvamai import SarvamAI
# from IndicTransToolkit.processor import IndicProcessor
# indic tans2
import torch
import os
from dotenv import load_dotenv
load_dotenv()
hf_token=os.getenv("hf_token")
sarvam_api_key=os.getenv("sarvam_api_key")

class textConversion:
    def __init__(self, src, dest="output/translated_text.json", src_language="English", target_language="Telugu"):
        self.src = src
        self.dest = dest
        self.src_language = src_language
        self.target_language = target_language
        
        # NLLB language code mapping
        self.nllb_lang_map = {
            "English": "eng_Latn",
            "Hindi": "hin_Deva",
            "Telugu": "tel_Telu",
            "Tamil": "tam_Taml",
            "Kannada": "kan_Knda",
            "Malayalam": "mal_Mlym",
            "Marathi": "mar_Deva",
            "Bengali": "ben_Beng",
            "Gujarati": "guj_Gujr",
            "Punjabi": "pan_Guru",
            "Odia": "ory_Orya",
            "Urdu": "urd_Arab",
            "Assamese": "asm_Beng",
            "Nepali": "npi_Deva"
        }
    
    def convert(self, model_name="facebook/nllb-200-distilled-600M"):
        with open(self.src, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        tokenizer = AutoTokenizer.from_pretrained(model_name, token=hf_token, trust_remote_code=True)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name, token=hf_token, trust_remote_code=True)
        
        src_text = [i["text"] for i in data]

        # Get NLLB codes with case-insensitive lookup
        src_key = self.src_language.strip().capitalize()
        tgt_key = self.target_language.strip().capitalize()
        
        src_code = self.nllb_lang_map.get(src_key, "eng_Latn")
        tgt_code = self.nllb_lang_map.get(tgt_key, "tel_Telu")
        
        print(f"Translating from {self.src_language} ({src_code}) to {self.target_language} ({tgt_code})")


        tokenizer.src_lang = src_code
        encoded = tokenizer(
            src_text,
            return_tensors="pt",
            padding=True,
            truncation=True
        )
        
        generated_tokens = model.generate(
            **encoded,
            forced_bos_token_id=tokenizer.convert_tokens_to_ids(tgt_code)
        )
        
        translated_text = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)
        
        trans_seg = []
        for i in range(len(translated_text)):
            trans_seg.append({
                "start": data[i]["start"],
                "end": data[i]["end"],
                "text": translated_text[i]
            })
            
        with open(self.dest, "w", encoding="utf-8") as f:
            json.dump(trans_seg, f, ensure_ascii=False, indent=2)
            
        return trans_seg


    def convert_indictrans2(self,model_name="ai4bharat/indictrans2-en-indic-1B"):
        
        DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

        model_name = "ai4bharat/indictrans2-en-indic-1B"

        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        model = AutoModelForSeq2SeqLM.from_pretrained(
            model_name,
            trust_remote_code=True,
            torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32
        ).to(DEVICE)

        model.eval()

        # Initialize IndicProcessor
        from IndicTransToolkit.processor import IndicProcessor
        ip = IndicProcessor(inference=True)

        # Load JSON
        with open(self.src, "r", encoding="utf-8") as f:
            data = json.load(f)

        input_sentences = [item["text"] for item in data]

        # Use IndicProcessor to add language tags and preprocess
        batch = ip.preprocess_batch(input_sentences, src_lang="eng_Latn", tgt_lang="tel_Telu")
        
        inputs = tokenizer(
            batch,
            return_tensors="pt",
            padding=True,
            truncation=True
        ).to(DEVICE)

        with torch.no_grad():
            outputs = model.generate(**inputs, max_length=256)

        generated_tokens = tokenizer.batch_decode(outputs, skip_special_tokens=True)
        
        # Postprocess to convert the Devanagari output back into the Telugu script
        translations = ip.postprocess_batch(generated_tokens, lang="tel_Telu")

        # Save output
        output = []
        for item, t in zip(data, translations):
            item["translated_text"] = t
            output.append(item)

        with open(self.dest, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print("Done")
    
    def convert_with_sarvam(self, api_key):
        # from sarvamai import SarvamAI
        from concurrent.futures import ThreadPoolExecutor
        
        with open(self.src, "r") as f:
            data = json.load(f)
            
        # Initialize the official SarvamAI client
        client = SarvamAI(api_subscription_key=api_key)

        def translate_segment(segment):
            try:
                # Use the SDK as requested
                response = client.text.translate(
                    input=segment["text"],
                    source_language_code="en-IN",
                    target_language_code="te-IN",
                    model="mayura:v1"
                )
                return {
                    "start": segment["start"], 
                    "end": segment["end"], 
                    "text": response.translated_text
                }
            except Exception as e:
                print(f"Exception for segment {segment['start']}: {e}")
                return segment

        # Maximize speed by translating segments concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            trans_seg = list(executor.map(translate_segment, data))

        with open(self.dest, "w", encoding="utf-8") as f:
            json.dump(trans_seg, f, ensure_ascii=False, indent=2)
            
        return trans_seg

    # def 


if __name__=="__main__":
    textConversion("output/source_text.json").convert_indictrans2("ai4bharat/indictrans2-en-indic-1B")
    # textConversion("output/source_text.json").convert_with_sarvam(sarvam_api_key)