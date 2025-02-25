from openai import OpenAI
import requests
import base64
import os
import json
import cv2
import random

# Set a different seed for each concurrent request
unique_seed = random.randint(1, 1_000_000)
from dotenv import load_dotenv

  # Load environment variables from .env file
load_dotenv()

   # Access the API key
# openai_api_key = os.getenv('OPENAI_API_KEY')

   # Initialize the OpenAI client with the API key
# client = OpenAI(api_key=openai_api_key)

def create_from_data(data, output_dir, caption_settings=None):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

        # Define a separate directory for storing prompt JSON files
    prompt_log_dir = os.path.join(output_dir, "prompts")
    if not os.path.exists(prompt_log_dir):
        os.makedirs(prompt_log_dir)

    # Get image settings from caption_settings
    image_settings = caption_settings.get("image", {}) if caption_settings else {}
    model = image_settings.get("model", "dall-e-3")
    # size = image_settings.get("size", "1024x1024")
    width = image_settings.get("width", 1024)
    height = image_settings.get("height", 1024)
    orientation = image_settings.get("orientation", "1024x1024")
    quality = image_settings.get("quality", "standard")
    n = image_settings.get("n", 1)
    # subject = image_settings.get("subject", "Cro-Magnons")
    effect = image_settings.get("effect", "Cinematic")
    prompt_size = image_settings.get("prompt_size", "Cinematic")
    size = str(width) + 'x' + str(height)
    image_counter = 1  # Initialize a counter for saved images

    for item in data["scenes"]:
            if "image" in item:
                art_style = item.get("art_style", {})
                # style_name = art_style.get("name", "").strip()
                style_characteristics = art_style.get("characteristics", [])
                neg = art_style.get("negative", "").strip()

                # Orientation and Effect Handling
                style_prompt = f" {effect.lower()}"
                # style_prompt += "The scene embodies the following artistic characteristics: "

                # Extract characteristics dynamically with proper sentence structure
                characteristic_texts = []
                if prompt_size == "small":
                    char = style_characteristics[0]
                    char_desc = char.get("description", "").strip()
                    characteristic_texts.append(f"{char_desc}")
                else:
                    for char in style_characteristics:
                        if isinstance(char, dict):
                            # char_name = char.get("name", "").strip()
                            char_desc = char.get("description", "").strip()
                            # characteristic_texts.append(f"{char_name} – {char_desc}")
                            characteristic_texts.append(f"{char_desc}")
                
                # Join characteristics efficiently
                style_prompt += "; ".join(characteristic_texts)

                # Constructing the final full prompt
                full_prompt = (
                        f"{item['image']}, {style_prompt}"
                        # f"The composition is dynamic, with natural movement to capture attention. The scene evokes an educational and narrative element, as if from a storybook. "
                        # f"Cinematic lighting, National Geographic quality, ultra-sharp details, volumetric shadows, vibrant colors."
                    )

                # Negative prompt to avoid distortions
                negative_prompt = f"{neg}"

                # API request payload
                request_payload = {
                    "model": model,
                    "vae": "sd_xl_vae.safetensors",
                    "prompt": full_prompt,
                    "negative_prompt": neg,
                    "width": 768,
                    "height": 768,
                    "steps": 40,
                    "cfg_scale": 9.0,
                    "sampler_index": "DPM++ 2M",
                    "schedule_type": "Karras",
                    "seed": unique_seed,
                    "hr_scale": 1.0,
                    "hr_upscaler": "4x-UltraSharp",
                    "denoising_strength": 0.5,
                    "batch_size": 1,
                    "batch_count": 6,
                    "enable_hr": False,
                    "refiner_checkpoint": "sd_xl_refiner_1.0.safetensors",
                    "refiner_switch_at": 0.6,
                    "model_hash": "31e35c80fc",
                    "version": "v1.10.1"
                    }

                with open(os.path.join(prompt_log_dir, f"prompt_{image_counter}.json"), "w") as json_file:
                    json.dump(request_payload, json_file, indent=2)

                # Send request to Stable Diffusion API
                response = requests.post(
                    "http://127.0.0.1:7860/sdapi/v1/txt2img",
                    json=request_payload
                )

                # Check if the request was successful
                if response.status_code == 200:
                    response_data = response.json()
                    # Extract base64 string
                    image_data = response_data['images'][0]

                    # Decode the image
                    image_bytes = base64.b64decode(image_data)
                    temp_path = os.path.join(output_dir, "temp.png")
                    with open(temp_path, "wb") as f:
                        f.write(image_bytes)

                    if orientation == "portrait":
                        # Load and resize to 1792x1792
                        img = cv2.imread(temp_path)
                        img_resized = cv2.resize(img, (1792, 1792))
                        
                        # Get the center crop coordinates (1024x1792 from 1792x1792)
                        height, width = img_resized.shape[:2]
                        start_x = (width - 1024) // 2
                        end_x = start_x + 1024
                        
                        # Perform the center crop
                        cropped_img = img_resized[:, start_x:end_x]
                        
                        # Save the final cropped image
                        cv2.imwrite(os.path.join(output_dir, f"image_{image_counter}.png"), cropped_img)
                        
                        # Clean up temporary file
                        os.remove(temp_path)
                    else:
                        # Save the image directly for non-portrait orientations
                        with open(os.path.join(output_dir, f"image_{image_counter}.png"), "wb") as f:
                            f.write(image_bytes)
                else:
                    print(f"Error: Failed to generate image. Status code: {response.status_code}")

                image_counter += 1

# def generate(prompt, output_file, size="1024x1792"):
#     response = client.images.generate(
#         model="dall-e-3",
#         prompt=prompt,
#         size=size,
#         quality="standard",
#         response_format="b64_json",
#         n=1,
#     )

#     image_b64 = response.data[0].b64_json

#     with open(output_file, "wb") as f:
#         f.write(base64.b64decode(image_b64))