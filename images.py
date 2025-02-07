from openai import OpenAI
import requests
import base64
import os

client = OpenAI()

def create_from_data(data, output_dir, caption_settings=None):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    # Get image settings from caption_settings
    image_settings = caption_settings.get("image", {}) if caption_settings else {}
    model = image_settings.get("model", "dall-e-3")
    size = image_settings.get("size", "1024x1024")
    quality = image_settings.get("quality", "standard")
    n = image_settings.get("n", 1)

    image_counter = 1  # Initialize a counter for saved images

    for item in data:
        if "image" in item:
            art_style = item.get("art_style", {})
            style_name = art_style.get("name", "")
            style_characteristics = art_style.get("characteristics", [])
            
            # Create a detailed prompt that incorporates the art style
            style_prompt = f"Create an image in the style of {style_name} art. "
            style_prompt += "The artwork should incorporate these characteristics: "
            
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
            full_prompt = f"{style_prompt}\n\nScene to create: {item['image']}"
            
            response = client.images.generate(
                model=model,
                prompt=full_prompt,
                size=size,
                quality=quality,
                n=n
            )

            image_url = response.data[0].url
            
            # Download and save the image
            response = requests.get(image_url)
            with open(os.path.join(output_dir, f"image_{image_counter}.png"), "wb") as f:
                f.write(response.content)
            
            image_counter += 1  # Increment the counter for each saved image

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