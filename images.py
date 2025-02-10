from openai import OpenAI
import requests
import base64
import os
import cv2
from dotenv import load_dotenv

  # Load environment variables from .env file
load_dotenv()

   # Access the API key
openai_api_key = os.getenv('OPENAI_API_KEY')

   # Initialize the OpenAI client with the API key
client = OpenAI(api_key=openai_api_key)

def create_from_data(data, output_dir, caption_settings=None):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    # Get image settings from caption_settings
    image_settings = caption_settings.get("image", {}) if caption_settings else {}
    model = image_settings.get("model", "dall-e-3")
    # size = image_settings.get("size", "1024x1024")
    width = image_settings.get("width", 1024)
    height = image_settings.get("height", 1024)
    orientation = image_settings.get("orientation", "1024x1024")
    quality = image_settings.get("quality", "standard")
    n = image_settings.get("n", 1)
    subject = image_settings.get("subject", "Cro-Magnons")
    effect = image_settings.get("effect", "Cinematic")
    size = str(width) + 'x' + str(height)
    image_counter = 1  # Initialize a counter for saved images

    for item in data:
        if "image" in item:
            art_style = item.get("art_style", {})
            style_name = art_style.get("name", "")
            style_characteristics = art_style.get("characteristics", [])
            
            # Create a detailed prompt that incorporates the art style
            style_prompt = f"Create an {orientation} oriented image in the style of {style_name} art with a {effect} touch. "
            style_prompt += "The  {orientation} oriented artwork should incorporate these characteristics: "
            
            # Extract characteristic descriptions from the dictionaries
            characteristic_texts = []
            for char in style_characteristics:
                if isinstance(char, dict):
                    char_text = f"{char.get('name', '')}: {char.get('description', '')}"
                    characteristic_texts.append(char_text)
                else:
                    characteristic_texts.append(str(char))
                    
            style_prompt += "; ".join(characteristic_texts)
            
            # Combine the style prompt with the original image description
            full_prompt = f"{orientation} oriented, {style_prompt}\n\n {orientation} oriented Scene to create: {subject}, {item['image']}"
            
            response = client.images.generate(
                model=model,
                prompt=full_prompt,
                size=size,
                quality=quality,
                n=n
            )

            image_url = response.data[0].url
            
            # Download and save the image
            img_response = requests.get(image_url)
            
            if orientation == "portrait":
                # Save the original image temporarily
                temp_path = os.path.join(output_dir, "temp.png")
                with open(temp_path, "wb") as f:
                    f.write(img_response.content)
                
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
                    f.write(img_response.content)

            image_counter += 1

def generate(prompt, output_file, size="1024x1792"):
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size=size,
        quality="standard",
        response_format="b64_json",
        n=1,
    )

    image_b64 = response.data[0].b64_json

    with open(output_file, "wb") as f:
        f.write(base64.b64decode(image_b64))