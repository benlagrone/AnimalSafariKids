#!/usr/bin/env python3

from openai import OpenAI
import time
import json
import sys
import os
import random

import narration
import images
import video

client = OpenAI()

# Load art styles
with open("instructions/art-styles-bible.json") as f:
    art_styles = json.load(f)["art_movements"]
    # art_styles = json.load(f)
    # print(art_styles)

scripts_dir = "scripts"
if not os.path.exists(scripts_dir):
    os.makedirs(scripts_dir)

if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} <script_name> [settings_file]")
    sys.exit(1)

script_name = sys.argv[1]
# Remove .txt extension if it's already there
script_name = script_name.replace('.txt', '')
script_path = os.path.join(scripts_dir, f"{script_name}.txt")

if not os.path.exists(script_path):
    print(f"Error: Script file not found: {script_path}")
    sys.exit(1)

with open(script_path) as f:
    source_material = f.read()

caption_settings = {}
if len(sys.argv) > 2:
    with open(sys.argv[2]) as f:
        settings = json.load(f)
        print("Loaded settings:", settings)  
        caption_settings = settings.get("captions", {})
        print("Caption settings:", caption_settings) 

short_id = str(int(time.time()))
output_file = "short.mp4"

basedir = os.path.join("shorts", short_id)
if not os.path.exists(basedir):
    os.makedirs(basedir)

print("Generating script...")

# Select random art style for each image
def get_random_art_style():
    """Get a random art style from the loaded styles"""
    if not art_styles:
        print("Warning: No art styles loaded")
        return None
    style = random.choice(art_styles)
    print(f"Selected art style: {style['name']}")
    return style

response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {
            "role": "system",
            "content": """You are a YouTube short narration generator. You generate 30 seconds to 1 minute of narration. The shorts you create have a background that fades from image to image as the narration is going on.

You will need to generate descriptions of images for each of the sentences in the short. They will be passed to an AI image generator. DO NOT IN ANY CIRCUMSTANCES use names of celebrities or people in the image descriptions. It is illegal to generate images of celebrities. Only describe persons without their names. Do not reference any real person or group in the image descriptions. Don't mention the female figure or other sexual content in the images because they are not allowed.

You are however allowed to use any content, including real names in the narration. Only image descriptions are restricted.

Note that the narration will be fed into a text-to-speech engine, so don't use special characters.

Respond with a pair of an image description in square brackets and a narration below it. Both of them should be on their own lines, as follows:

###

[Description of a background image]

Narrator: "One sentence of narration"

[Description of a background image]

Narrator: "One sentence of narration"

[Description of a background image]

Narrator: "One sentence of narration"

###

The short should be 6 sentences maximum.

You should add a description of a fitting backround image in between all of the narrations. It will later be used to generate an image with AI.
"""
        },
        {
            "role": "user",
            "content": f"Create a YouTube short narration based on the following source material:\n\n{source_material}"
        }
    ]
)

response_text = response.choices[0].message.content
response_text = response_text.replace("'", "'").replace("`", "'").replace("…", "...").replace(""", '"').replace(""", '"')

with open(os.path.join(basedir, "response.txt"), "w") as f:
    f.write(response_text)

data, narrations = narration.parse(response_text)

# Add art style to each image description
for item in data:
    if "image" in item:
        art_style = get_random_art_style()
        item["art_style"] = art_style

with open(os.path.join(basedir, "data.json"), "w") as f:
    json.dump(data, f, ensure_ascii=False)

print(f"Generating narration...")
narration.create(data, os.path.join(basedir, "narrations"))

print("Generating images...")
images.create_from_data(data, os.path.join(basedir, "images"), settings)

print("Generating video...")
video.create(narrations, basedir, output_file, settings)

print(f"DONE! Here's your video: {os.path.join(basedir, output_file)}")