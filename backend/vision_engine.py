from transformers import Qwen2VLForConditionalGeneration, AutoTokenizer, AutoProcessor
from qwen_vl_utils import process_vision_info
import torch
from PIL import Image
import io
import base64
import threading

class VisionEngine:
    def __init__(self, model_path="Qwen/Qwen2-VL-2B-Instruct"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.lock = threading.Lock()
        print(f"LOG: Loading Qwen2-VL on {self.device}...")
        
        print("LOG: Initializing model from HuggingFace (this will download ~4GB if not cached)...")
        self.model = Qwen2VLForConditionalGeneration.from_pretrained(
            model_path, 
            torch_dtype="auto", 
            device_map="auto"
        )
        print("LOG: Model weights loaded successfully.")
        
        print("LOG: Initializing processor...")
        self.processor = AutoProcessor.from_pretrained(model_path)
        print("LOG: Processor loaded.")
        
        print("LOG: Initializing tokenizer...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        print("LOG: Tokenizer loaded.")
        
        print("LOG: VisionEngine is fully initialized and ready for inference.")

    def analyze_frame(self, frame_base64, prompt):
        print("LOG: Decoding image and preparing messages...")
        # Convert base64 to PIL Image
        img_data = base64.b64decode(frame_base64)
        image = Image.open(io.BytesIO(img_data)).convert("RGB")

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        # Preparation for inference
        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = self.processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        )
        inputs = inputs.to(self.model.device)

        # Inference with thread safety
        with self.lock:
            print("LOG: Model lock acquired for inference.")
            generated_ids = self.model.generate(**inputs, max_new_tokens=128)
            print("LOG: Inference complete, releasing lock.")
        generated_ids_trimmed = [
            out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = self.processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )
        
        return output_text[0]

    def summarize_scene(self, frame_base64, custom_instruction=None):
        default_prompt = "Describe what is happening in this video frame in one very short, professional sentence for a security activity log. Focus on movements, people, or significant changes."
        prompt = custom_instruction if custom_instruction else default_prompt
        return self.analyze_frame(frame_base64, prompt)
