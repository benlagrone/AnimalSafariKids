# from elevenlabs import voices, generate, play, stream, save
import time
from gtts import gTTS
import os
import re
import json

# You can set this environment variable to choose the service
# export TTS_SERVICE=gtts  # or elevenlabs
TTS_SERVICE = os.getenv('TTS_SERVICE', 'gtts')  # Default to gtts if not set

def parse(text):
    """Parse the input text into data and narrations."""
    # Initialize variables to store the parsed data
    data = {"scenes": []}
    narrations = []
    
    # Split the text into lines and remove empty lines
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Process each line
    for line in lines:
        # Skip ### markers
        if line == '###':
            continue
            
        # Check if this is an image description
        if line.startswith('[') and line.endswith(']'):
            # Extract the image description and add to scenes
            image_desc = line[1:-1]  # Remove the brackets
            data["scenes"].append({"image": image_desc})
            
        # Check if this is narration
        elif line.startswith('Narrator:'):
            # Extract the narration text
            narration = line.replace('Narrator:', '').strip()
            # Remove quotes if present
            narration = narration.strip('"').strip('"').strip('"')
            # Add to both scenes and narrations
            data["scenes"].append({"narration": narration})
            narrations.append(narration)

        elif line.startswith('Title:'):
            # Extract the title text
            title = line.replace('Title:', '').strip()
            # Remove quotes if present
            title = title.strip('"').strip('"').strip('"')
            # Add to data
            data["title"] = title

        elif line.startswith('Description:'):
            # Extract the description text
            description = line.replace('Description:', '').strip()
            # Remove quotes if present
            description = description.strip('"').strip('"').strip('"')
            # Add to data
            data["description"] = description

        elif line.startswith('Tags:'):
            # Extract the tags text
            tags = line.replace('Tags:', '').strip()
            tags_array = json.loads(tags)
            # Add to data
            data["tags"] = tags_array
    
    return data, narrations

def create(data, output_dir):
    """Create audio files from the narration data."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    narration_count = 0
    narration_data = []
    
    for i, item in enumerate(data["scenes"]):
        if "narration" not in item:
            continue
            
        narration_count += 1
        output_file = os.path.join(output_dir, f"narration_{narration_count}.mp3")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if TTS_SERVICE.lower() == 'gtts':
                    print(f"Creating narration {narration_count} with gTTS... (attempt {attempt + 1})")
                    tts = gTTS(
                        text=item["narration"],
                        lang='en',
                        tld='com',
                        slow=False
                    )
                    tts.save(output_file)
                    print(f"Successfully created narration {narration_count}")
                    
                    # Get audio duration using AudioSegment
                    from pydub import AudioSegment
                    audio = AudioSegment.from_mp3(output_file)
                    duration = len(audio)
                    
                    # Add to narration data
                    narration_data.append({
                        "filename": f"narration_{narration_count}.mp3",
                        "duration": duration,
                        "text":item["narration"]
                    })
                    
                    break
                else:
                    # Use ElevenLabs...
                    audio = generate(
                        text=item["narration"],
                        voice="Adam"
                    )
                    with open(output_file, 'wb') as f:
                        f.write(audio)
                    
                    # Get audio duration using AudioSegment
                    audio = AudioSegment.from_mp3(output_file)
                    duration = len(audio)
                    
                    # Add to narration data
                    narration_data.append({
                        "filename": f"narration_{narration_count}.mp3",
                        "duration": duration,
                        "text":item["narration"]
                    })
                    
            except Exception as e:
                if attempt == max_retries - 1:  # Last attempt
                    print(f"Error creating narration {narration_count}: {str(e)}")
                    raise
                print(f"Attempt {attempt + 1} failed, retrying...")
                time.sleep(2 ** attempt)  # Exponential backoff
        
    parent_dir = os.path.dirname(output_dir)
    with open(os.path.join(parent_dir, "narration.json"), "w") as f:
        json.dump(narration_data, f, indent=2)


def generate_narration(text, output_file):
    """Generate a single narration file."""
    try:
        if TTS_SERVICE.lower() == 'gtts':
            # Use Google TTS
            tts = gTTS(text=text, lang='en', tld='com')
            tts.save(output_file)
        else:
            # Use ElevenLabs
            audio = generate(
                text=text,
                voice="Adam"
            )
            with open(output_file, 'wb') as f:
                f.write(audio)
        return True
    except Exception as e:
        print(f"Error generating narration: {str(e)}")
        return False

def concatenate_narrations(narration_files, output_file):
    """Concatenate multiple narration files into one."""
    from pydub import AudioSegment
    
    try:
        # Load the first file
        combined = AudioSegment.from_mp3(narration_files[0])
        
        # Add the rest of the files
        for file in narration_files[1:]:
            audio = AudioSegment.from_mp3(file)
            combined += audio
            
        # Export the combined audio
        combined.export(output_file, format="mp3")
        return True
    except Exception as e:
        print(f"Error concatenating narrations: {str(e)}")
        return False