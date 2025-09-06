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

# Stable Diffusion API base URL (external service)
# Example: http://192.168.86.23:8000
IMAGE_API_BASE_URL = os.getenv("IMAGE_API_BASE_URL", "http://127.0.0.1:8000")
# Read timeout in seconds for image API (connect/read tuple uses 10s connect default)
try:
    IMAGE_API_TIMEOUT = float(os.getenv("IMAGE_API_TIMEOUT", "300"))
except ValueError:
    IMAGE_API_TIMEOUT = 300.0
# API kind: 'form' (sd-api style) or 'json' (A1111 style). Default 'form'.
IMAGE_API_KIND = os.getenv("IMAGE_API_KIND", "form").lower()

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
    prompt_size = image_settings.get("prompt_size", "small")
    neg2 = image_settings.get("negative", "multiple heads, multiple horns, extra limbs, missing limbs, fused features, disproportionate anatomy, symmetrical errors, unnatural joints, overly smooth textures, low-quality rendering, floating body parts, deformed anatomy, cartoonish, cgi, painting, unnatural poses, awkward jumps, gravity-defying, watermark, text, signature")
    size = str(width) + 'x' + str(height)
    image_counter = 1  # Initialize a counter for saved images

    for item in data["scenes"]:
            if "image" in item:
                art_style = item.get("art_style", {})
                # style_name = art_style.get("name", "").strip()
                style_characteristics = art_style.get("characteristics", [])
                neg = neg2
                neg += art_style.get("negative", "").strip()

                # Orientation and Effect Handling
                style_prompt = f" {effect.lower()}, "
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
                style_prompt += ", ".join(characteristic_texts)

                # Constructing the final full prompt
                full_prompt = (
                        f"{item['image']}, {style_prompt}"
                        # f"The composition is dynamic, with natural movement to capture attention. The scene evokes an educational and narrative element, as if from a storybook. "
                        # f"Cinematic lighting, National Geographic quality, ultra-sharp details, volumetric shadows, vibrant colors."
                    )

                # Negative prompt to avoid distortions
                # negative_prompt = f"{neg}"

                # Build payload based on configured API kind
                if IMAGE_API_KIND == "form":
                    # Minimal fields as used by sd-api example
                    request_payload = {
                        "prompt": full_prompt,
                        "negative_prompt": neg,
                        "width": image_settings.get("width", 512),
                        "height": image_settings.get("height", 512),
                        "steps": image_settings.get("steps", 28),
                        "guidance": image_settings.get("guidance", image_settings.get("cfg_scale", 7.0)),
                    }
                    request_headers = {
                        "accept": "application/json",
                        "Content-Type": "application/x-www-form-urlencoded",
                    }
                    request_kwargs = {"data": request_payload}
                else:
                    # JSON payload compatible with A1111
                    request_payload = dict(image_settings)
                    # Do not alter the structure or existing values except prompt/negative_prompt
                    request_payload['prompt'] = full_prompt
                    request_payload['negative_prompt'] = neg
                    request_headers = {"accept": "application/json"}
                    request_kwargs = {"json": request_payload}
                # API request payload
                # request_payload = {
                #     "prompt": full_prompt,
                #     "negative_prompt": neg,
                #     "model": image_settings.get("model", "v1-5-pruned-emaonly.safetensors"),
                #     "width": image_settings.get("width", 768),
                #     "height": image_settings.get("height", 768),
                #     "steps": image_settings.get("steps", 30),
                #     "cfg_scale": image_settings.get("cfg_scale", 7.0),
                #     "sampler_index":image_settings.get("sampler_index", "DPM++ 2M"),
                #     "seed": unique_seed,
                #     "batch_size": image_settings.get("batch_size", 1),
                #     "batch_count": image_settings.get("batch_count", 6),
                #     "enable_hr": image_settings.get("enable_hr", False),
                #     "hr_scale": image_settings.get("hr_scale", 1.0),
                #     "hr_upscaler": image_settings.get("hr_upscaler", "4x-UltraSharp"),
                #     "denoising_strength": image_settings.get("denoising_strength", 0.5),
                #     "refiner_checkpoint": image_settings.get("refiner_checkpoint", "sd_xl_refiner_1.0.safetensors"),
                #     "refiner_switch_at": image_settings.get("refiner_switch_at", 0.6),
                #     "model_hash": image_settings.get("model_hash", "31e35c80fc"),
                #     "version": image_settings.get("version", "v1.10.1")
                #     }

                with open(os.path.join(prompt_log_dir, f"prompt_{image_counter}.json"), "w") as json_file:
                    json.dump(
                        {
                            "endpoint": f"{IMAGE_API_BASE_URL.rstrip('/')}/txt2img",
                            "payload": request_payload,
                            },
                            json_file,
                            indent=2,
                        )

                # Send request to Stable Diffusion API
                try:
                    response = requests.post(
                        f"{IMAGE_API_BASE_URL.rstrip('/')}/txt2img",
                        headers=request_headers,
                        timeout=(10, IMAGE_API_TIMEOUT),
                        **request_kwargs,
                    )
                except requests.exceptions.ReadTimeout:
                    print(
                        f"Error: Image API timed out after {IMAGE_API_TIMEOUT}s: "
                        f"{IMAGE_API_BASE_URL.rstrip('/')}/txt2img"
                    )
                    image_counter += 1
                    continue

                # Check if the request was successful
                if response.status_code == 200:
                    response_data = response.json()
                    image_bytes = None

                    # Case 1: Automatic1111-style base64 response
                    if isinstance(response_data, dict) and 'images' in response_data:
                        image_data = response_data['images'][0]
                        image_bytes = base64.b64decode(image_data)

                    # Case 2: URL-based response { ok, path, url }
                    elif isinstance(response_data, dict) and response_data.get('ok') and response_data.get('url'):
                        file_url = response_data['url']
                        img_resp = requests.get(file_url, timeout=120)
                        if img_resp.status_code == 200:
                            image_bytes = img_resp.content
                        else:
                            print(f"Error: Failed to download image from {file_url}.")

                    if image_bytes is None:
                        # Print any error message from server response
                        if isinstance(response_data, dict):
                            err_msg = response_data.get('error') or response_data.get('detail')
                            if err_msg:
                                print(f"Image API error detail: {err_msg}")
                        print("Error: Unexpected image API response format.")
                        image_counter += 1
                        continue

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
                    # Log more detail to help diagnose 4xx/5xx
                    try:
                        err_text = response.text[:500]
                    except Exception:
                        err_text = "<no response body>"
                    print(
                        f"Error: Failed to generate image. Status code: {response.status_code}. "
                        f"Endpoint: {IMAGE_API_BASE_URL.rstrip('/')}/txt2img. Response: {err_text}"
                    )

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
