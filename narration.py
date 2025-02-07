# from elevenlabs import voices, generate, play, stream, save
from gtts import gTTS
import os
import re

# You can set this environment variable to choose the service
# export TTS_SERVICE=gtts  # or elevenlabs
TTS_SERVICE = os.getenv('TTS_SERVICE', 'gtts')  # Default to gtts if not set

def parse(text):
    """Parse the input text into data and narrations."""
    # Initialize lists to store the parsed data
    data = []
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
            # Extract the image description and add to data
            image_desc = line[1:-1]  # Remove the brackets
            data.append({"image": image_desc})
            
        # Check if this is narration
        elif line.startswith('Narrator:'):
            # Extract the narration text
            narration = line.replace('Narrator:', '').strip()
            # Remove quotes if present
            narration = narration.strip('"').strip('"').strip('"')
            # Add to both data and narrations
            data.append({"narration": narration})
            narrations.append(narration)
    
    return data, narrations

def create(data, output_dir):
    """Create audio files from the narration data."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    narration_count = 0
    
    for i, item in enumerate(data):
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
                    break
                else:
                    # Use ElevenLabs...
                    audio = generate(
                        text=item["narration"],
                        voice="Adam"
                    )
                    with open(output_file, 'wb') as f:
                        f.write(audio)
                    
            except Exception as e:
                if attempt == max_retries - 1:  # Last attempt
                    print(f"Error creating narration {narration_count}: {str(e)}")
                    raise
                print(f"Attempt {attempt + 1} failed, retrying...")
                time.sleep(2 ** attempt)  # Exponential backoff

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