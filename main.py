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
import upload
import ollama
from pathlib import Path

from animalslist import create_animal_csv
from animalscript import get_new_animals, create_animal_scripts

# Get new animals and create scripts
new_animals = get_new_animals()
created_files = create_animal_scripts(new_animals)

# Load environment variables from .env file
load_dotenv()
eleven_api_key = os.getenv('ELEVEN_API_KEY')
openai_api_key = os.getenv('OPENAI_API_KEY')
ollama_host = os.getenv('OLLAMA_HOST')
# client = OpenAI(api_key=openai_api_key)

# Configure Ollama client (respects OLLAMA_HOST if provided)
try:
    if ollama_host:
        ollama_client = ollama.Client(host=ollama_host)
    else:
        ollama_client = ollama.Client()
except Exception:
    ollama_client = None

# Resolve project paths relative to this file
BASE_DIR = Path(__file__).resolve().parent

# Load art styles
with open(BASE_DIR / "instructions" / "art-styles.json") as f:
    art_styles = json.load(f)["art_movements"]


def update_settings_json(created_files):
    # Read the current settings
    with open('settings.json', 'r') as f:
        settings = json.load(f)
    
    # Remove .txt extension from filenames
    animal_names = [file.replace('.txt', '') for file in created_files]
    
    # Update the scripts list in settings
    settings['script']['scripts'] = animal_names
    
    # Write the updated settings back to the file
    with open('settings.json', 'w') as f:
        json.dump(settings, f, indent=4)
    
    print(f"Updated settings.json with new animals: {', '.join(animal_names)}")


def generate_narration_with_ollama(source_material):
    # Load your local model using Ollama
    model = 'mistral'  # or whatever model you want to use
    
    # Read the prompt from the file (path relative to source tree)
    prompt_path = BASE_DIR / 'instructions' / 'prompt.txt'
    with open(prompt_path, 'r') as file:
        prompt_template = file.read()
    
    # Construct the full prompt
    prompt = prompt_template + f"\n\nCreate a YouTube short narration based on the following source material:\n\n{source_material}"
    
    # Generate the narration using the model
    # Prefer configured client; fall back to module-level generate
    if ollama_client is not None:
        response = ollama_client.generate(model=model, prompt=prompt)
    else:
        response = ollama.generate(model=model, prompt=prompt)
    return response['response']  # Ollama returns a dict with 'response' key

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

update_settings_json(created_files)

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


    # response_text = response.choices[0].message.content
    response_text = generate_narration_with_ollama(source_material)

    response_text = response_text.replace("'", "'").replace("`", "'").replace("…", "...").replace(""", '"').replace(""", '"')

    with open(os.path.join(basedir, "response.txt"), "w") as f:
        f.write(response_text)

    data, narrations = narration.parse(response_text)

    # Add art style to each image description
    for item in data["scenes"]:
        # if "image" in item:
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

        # Upload the video if enabled in settings
    if settings.get("upload", {}).get("enabled", False):
        print("Uploading video to YouTube...")
        try:
            video_id = upload.upload_video(basedir, settings)
            print(f"Video uploaded successfully! ID: {video_id}")
        except Exception as e:
            print(f"Error uploading video: {str(e)}")
    
    print("Process complete!")

print("All scripts processed.")

# Call the function when needed
animal_names = create_animal_csv()
