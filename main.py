#!/usr/bin/env python3

import csv
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

from animalscript import get_new_animals, create_animal_scripts

# All media outputs write to the bind-mounted host videos directory
OUTPUT_ROOT = "/videos"
ANIMAL_CSV_PATH = Path("animal_names.csv")

# Globals configured during startup
ollama_client = None


def initialize_environment():
    """Load environment variables and configure shared clients."""
    global ollama_client

    load_dotenv()
    ollama_host = os.getenv("OLLAMA_HOST")

    try:
        if ollama_host:
            ollama_client = ollama.Client(host=ollama_host)
        else:
            ollama_client = ollama.Client()
    except Exception:
        ollama_client = None

# Resolve project paths relative to this file
BASE_DIR = Path(__file__).resolve().parent

art_styles_candidates = [
    BASE_DIR / "instructions" / "art-styles.json",
    Path.cwd() / "instructions" / "art-styles.json",
    Path("/instructions/art-styles.json"),
]
for candidate in art_styles_candidates:
    if candidate.exists():
        art_styles_path = candidate
        break
else:
    raise FileNotFoundError(
        "instructions/art-styles.json not found. Checked: "
        + ", ".join(str(p) for p in art_styles_candidates)
    )
with open(art_styles_path) as f:
    art_styles = json.load(f)["art_movements"]


def record_completed_animal(script_name: str) -> None:
    """Append the processed animal to animal_names.csv if not already present."""
    animal_name = (
        script_name.replace(".txt", "")
        .replace("-", " ")
        .replace("_", " ")
        .strip()
    )

    existing = set()
    if ANIMAL_CSV_PATH.exists():
        with ANIMAL_CSV_PATH.open("r", newline="") as csv_file:
            reader = csv.reader(csv_file)
            next(reader, None)  # skip header if present
            for row in reader:
                if row:
                    existing.add(row[0].strip().lower())
    else:
        with ANIMAL_CSV_PATH.open("w", newline="") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["Animal Name"])

    if animal_name.lower() in existing:
        return

    with ANIMAL_CSV_PATH.open("a", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow([animal_name])


def generate_narration_with_ollama(source_material):
    # Load your local model using Ollama
    model = 'mistral'  # or whatever model you want to use
    
    # Read the prompt from the file (path relative to source tree)
    prompt_candidates = [
        BASE_DIR / 'instructions' / 'prompt.txt',
        Path.cwd() / 'instructions' / 'prompt.txt',
        Path('/instructions/prompt.txt'),
    ]
    for candidate in prompt_candidates:
        if candidate.exists():
            prompt_path = candidate
            break
    else:
        raise FileNotFoundError(
            "instructions/prompt.txt not found. Ensure it exists. Checked: "
            + ", ".join(str(p) for p in prompt_candidates)
        )

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

def main():
    initialize_environment()

    # Expand the script list with a fresh animal before any other work
    try:
        new_animals = get_new_animals()
    except RuntimeError as exc:
        print(f"Could not fetch a unique animal: {exc}")
        return
    created_files = create_animal_scripts(new_animals)

    settings_file = "settings.json"
    single_script = None
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.endswith(".json"):
            settings_file = arg
        else:
            single_script = arg.replace(".txt", "")

    with open(settings_file) as f:
        settings = json.load(f)

    if single_script is not None:
        script_names = [single_script]
    elif created_files:
        script_names = [Path(name).stem for name in created_files]
    else:
        script_names = settings["script"].get("scripts", [])

    scripts_dir = "scripts"
    if not os.path.exists(scripts_dir):
        os.makedirs(scripts_dir)

    for script_name in script_names:
        if not script_name.endswith(".txt"):
            script_name += ".txt"
        script_path = os.path.join(scripts_dir, script_name)

        if not os.path.exists(script_path):
            print(f"Error: Script file not found: {script_path}")
            continue

        with open(script_path) as f:
            source_material = f.read()

        caption_settings = settings.get("captions", {})

        short_id = str(int(time.time()))
        basedir = os.path.join(OUTPUT_ROOT, short_id)
        if not os.path.exists(basedir):
            os.makedirs(basedir)

        print(f"Generating script for {script_name}...")

        response_text = generate_narration_with_ollama(source_material)
        response_text = (
            response_text.replace("`", "'")
            .replace("…", "...")
            .replace("“", '"')
            .replace("”", '"')
        )

        with open(os.path.join(basedir, "response.txt"), "w") as f:
            f.write(response_text)

        data, narrations = narration.parse(response_text)

        for item in data["scenes"]:
            art_style = get_random_art_style(settings["script"]["art"], art_styles)
            item["art_style"] = art_style

        with open(os.path.join(basedir, "data.json"), "w") as f:
            json.dump(data, f, ensure_ascii=False)

        print("Generating narration...")
        narration.create(data, os.path.join(basedir, "narrations"))

        print("Generating images...")
        images.create_from_data(data, os.path.join(basedir, "images"), settings)

        print("Generating video...")
        output_file = f"{script_name}.mp4"
        video.create(narrations, basedir, output_file, settings)

        print(f"DONE! Here's your video: {os.path.join(basedir, output_file)}")

        record_completed_animal(script_name)

        if settings.get("upload", {}).get("enabled", False):
            print("Uploading video to YouTube...")
            try:
                video_id = upload.upload_video(basedir, settings)
                print(f"Video uploaded successfully! ID: {video_id}")
            except Exception as e:
                print(f"Error uploading video: {str(e)}")

        print("Process complete!")

    print("All scripts processed.")


if __name__ == "__main__":
    main()
