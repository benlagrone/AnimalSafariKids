#!/usr/bin/env python3

import json
import os
import sys
import time
from dotenv import load_dotenv
import random
import narration
import images
import video
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()
eleven_api_key = os.getenv('ELEVEN_API_KEY')
openai_api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=openai_api_key)

# Load art styles
with open("instructions/art-styles.json") as f:
    art_styles = json.load(f)["art_movements"]

def get_random_art_style(script_art_styles, art_styles):
    """Get a random art style from the settings and retrieve its full data"""
    if not script_art_styles:
        print("Warning: No art styles specified in settings")
        return None

    # Select a random art style from the settings
    selected_style_name = random.choice(script_art_styles)
    print(f"Selected art style from settings: {selected_style_name}")

    # Find the full data for the selected style
    for style in art_styles:
        if style['name'] == selected_style_name:
            print(f"Retrieved full data for style: {style['name']}")
            return style

    print(f"Warning: Art style '{selected_style_name}' not found in art-styles.json")
    return None

# Determine the settings file
settings_file = "settings.json"
if len(sys.argv) > 1:
    # If the first argument is not a script, assume it's the settings file
    if sys.argv[1].endswith('.json'):
        settings_file = sys.argv[1]
    else:
        # Otherwise, treat it as a script name
        script_names = [sys.argv[1].replace('.txt', '')]

# Load settings from the determined settings file
with open(settings_file) as f:
    settings = json.load(f)

# Extract the list of script names from settings if not overridden by command-line
if 'script_names' not in locals():
    script_names = settings["script"].get("scripts", [])

scripts_dir = "scripts"

# Ensure the scripts directory exists
if not os.path.exists(scripts_dir):
    os.makedirs(scripts_dir)

# Process each script in the list
for script_name in script_names:
    # Ensure the script name has the correct extension
    if not script_name.endswith('.txt'):
        script_name += '.txt'
    script_path = os.path.join(scripts_dir, script_name)

    # Check if the script file exists
    if not os.path.exists(script_path):
        print(f"Error: Script file not found: {script_path}")
        continue

    # Load the script content
    with open(script_path) as f:
        source_material = f.read()

    # Load caption settings if available
    caption_settings = settings.get("captions", {})

    # Create a unique directory for each script's output
    short_id = str(int(time.time()))
    basedir = os.path.join("shorts", short_id)
    if not os.path.exists(basedir):
        os.makedirs(basedir)

    print(f"Generating script for {script_name}...")

    # Use source_material in the OpenAI API call
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": f"""You are a YouTube short narration generator. You should generate at least 8-10 sections of narration, each with its own image description. You generate {settings['script']['min-length']} to {settings['script']['max-length']} of narration. The shorts you create have a background that fades from image to image as the narration is going on.

You will need to generate descriptions of images for each of the sentences in the short. They will be passed to an AI image generator. 

DO NOT IN ANY CIRCUMSTANCES use names of celebrities or people in the image descriptions. It is illegal to generate images of celebrities. Only describe persons without their names. Do not reference any real person or group in the image descriptions. Don't mention the female figure or other sexual content in the images because they are not allowed.
- NO violence, hunting, or predatory behavior
- NO animals attacking or killing each other
- NO graphic or disturbing content
- Focus on peaceful, natural behaviors and interactions
- Show animals in their natural habitats doing everyday activities
- Emphasize positive, educational content
- Keep content family-friendly and suitable for all ages

You are however allowed to use any content, including real names in the narration. Only image descriptions are restricted.

Note that the narration will be fed into a text-to-speech engine, so don't use special characters.

Respond with a pair of an image description in square brackets and a narration below it. Both of them should be on their own lines, as follows:

###
Title: "Title of the video"

Description: "Description of the video"

[Description of a background image]

Narrator: "One to 2 sentences of narration"

[Description of a background image]

Narrator: "One to 2 sentences of narration"

[Description of a background image]

Narrator: "One to 2 sentences of narration"

###

You should add a description of a fitting background image in between all of the narrations. It will later be used to generate an image with AI.
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
            art_style = get_random_art_style(settings["script"]["art"], art_styles)
            item["art_style"] = art_style

    with open(os.path.join(basedir, "data.json"), "w") as f:
        json.dump(data, f, ensure_ascii=False)

    print(f"Generating narration...")
    narration.create(data, os.path.join(basedir, "narrations"))

    print("Generating images...")
    images.create_from_data(data, os.path.join(basedir, "images"), settings)

    print("Generating video...")
    output_file = f"{script_name}.mp4"
    video.create(narrations, basedir, output_file, settings)

    print(f"DONE! Here's your video: {os.path.join(basedir, output_file)}")

print("All scripts processed.")