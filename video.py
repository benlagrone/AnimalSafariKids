import os
import cv2
import numpy as np
import math
from pydub import AudioSegment
import subprocess
import captacity
import json
import math

def get_audio_duration(audio_file):
    return len(AudioSegment.from_file(audio_file))

def resize_image(image, width, height, extra_width=10, extra_height=10):
    aspect_ratio = image.shape[1] / image.shape[0]
    if aspect_ratio > (width / height):
        new_width = width
        new_height = int(width / aspect_ratio)
    else:
        new_height = height
        new_width = int(height * aspect_ratio)
    
    # Resize the image to fit within the specified dimensions
    resized_image = cv2.resize(image, (new_width, new_height))
    
    # Add extra pixels to both dimensions
    final_width = new_width + extra_width
    final_height = new_height + extra_height
    final_image = cv2.resize(resized_image, (final_width, final_height))
    
    return final_image

def create(narrations, output_dir, output_filename, settings):
    # Retrieve video settings
    video_settings = settings.get("video", {})
    width = video_settings.get("width", 720)  # 9:16 aspect ratio
    height = video_settings.get("height", 1280)
    frame_rate = video_settings.get("fps", 30)
    codec = video_settings.get("codec", "avc1")
    slide_speed_multiplier = video_settings.get("slide_speed_multiplier", 1)  # Default to 1 if not set
    
        # Load narration data from JSON
    with open(os.path.join(output_dir, "narration.json"), "r") as f:
        narration_data = json.load(f)


    # Create a VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*codec)
    temp_video = os.path.join(output_dir, "temp_video.mp4")
    out = cv2.VideoWriter(temp_video, fourcc, frame_rate, (width, height))

    for i, narration_item in enumerate(narration_data):
        current_image_path = os.path.join(output_dir, "images", f"image_{i+1}.png")
        current_image = cv2.imread(current_image_path)
        
        # Resize the current image to the target dimensions
        current_image = cv2.resize(current_image, (width, height))

        # Load the next image if it exists
        if i + 1 < len(narration_data):
            next_image_path = os.path.join(output_dir, "images", f"image_{i+2}.png")
            next_image = cv2.imread(next_image_path)
            next_image = cv2.resize(next_image, (width, height))
        else:
            next_image = np.zeros((height, width, 3), dtype=np.uint8)  # Black if no next image

        # Display the current image for its duration
        # narration = os.path.join(output_dir, "narrations", f"narration_{i+1}.mp3")
        # duration = get_audio_duration(narration)
        # frames_for_image = int((duration / 1000) * frame_rate)
        frames_for_narration = int((narration_item["duration"] / 1000) * frame_rate)

        if i + 1 < len(narration_data):
            # For images with transitions, reserve frames for the slide effect
            slide_frames = int(frame_rate / slide_speed_multiplier)
            static_frames = frames_for_narration - slide_frames
            
            # Write the static image frames
            for _ in range(static_frames):
                out.write(current_image)

            # Add sliding effect
            for frame in range(slide_frames):
                offset = int((frame / slide_frames) * width)
                offset = min(offset, width - 1)
                
                slide_image = next_image.copy()
                slide_image[:, :width-offset] = current_image[:, offset:]
                out.write(slide_image)
        else:
            # For the last image, no transition needed
            for _ in range(frames_for_narration):
                out.write(current_image)

    out.release()
    cv2.destroyAllWindows()

    # Add narration and captions as before
    with_narration = "with_narration.mp4"
    add_narration_to_video(narrations, temp_video, output_dir, with_narration)

    # Add captions to video
    output_path = os.path.join(output_dir, output_filename)
    input_path = os.path.join(output_dir, with_narration)
    segments = create_segments(narrations, output_dir)

    caption_settings = settings.get("captions", {})
    captacity.add_captions(
        video_file=input_path,
        output_file=output_path,
        segments=segments,
        print_info=True,
        **caption_settings,
    )

    # Clean up temporary files
    os.remove(input_path)
    os.remove(temp_video)

    # Reprocess the final video to ensure compatibility
    reprocess_video(output_path, output_dir, "final_output.mp4")

def add_narration_to_video(narrations, input_video, output_dir, output_file):
# test
    ffprobe_command = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'stream=codec_type,codec_name',
        '-of', 'default=noprint_wrappers=1',
        input_video
    ]

    result = subprocess.run(ffprobe_command, capture_output=True, text=True)

    if result.returncode != 0:
        print("Failed to probe the video file.")
        print("FFprobe stderr:", result.stderr)
    else:
        print("Video properties:")
        print(result.stdout)
# end test

    full_narration = AudioSegment.empty()
    for i, _ in enumerate(narrations):
        audio = os.path.join(output_dir, "narrations", f"narration_{i+1}.mp3")
        full_narration += AudioSegment.from_file(audio)

    temp_narration = os.path.join(output_dir, "narration.mp3")
    full_narration.export(temp_narration, format="mp3")

    ffmpeg_command = [
        'ffmpeg',
        '-y',
        '-i', input_video,
        '-i', temp_narration,
        '-map', '0:v',  # Map video from the first input
        '-map', '1:a',  # Map audio from the second input
        # '-c:v', 'libx264',
        '-c:v', 'copy',  # Copy the video stream without re-encoding
        '-c:a', 'aac',   # Encode audio with AAC
        '-b:a', '192k',  # Set audio bitrate
        '-ar', '44100',  # Set audio sample rate
        os.path.join(output_dir, output_file)
    ]

    result = subprocess.run(ffmpeg_command, capture_output=True, text=True)

    if result.returncode != 0:
        print("FFmpeg failed to create the video with narration.")
        print("FFmpeg stdout:", result.stdout)
        print("FFmpeg stderr:", result.stderr)
    else:
        print("Video with narration created successfully.")

    os.remove(temp_narration)

def create_segments(narrations, output_dir):
    segments = []
    offset = 0
    for i, narration in enumerate(narrations):
        audio_file = os.path.join(output_dir, "narrations", f"narration_{i+1}.mp3")
        try:
            t_segments = captacity.transcriber.transcribe_locally(
                audio_file=audio_file,
                prompt=narration,
            )
        except ImportError:
            t_segments = captacity.transcriber.transcribe_with_api(
                audio_file=audio_file,
                prompt=narration,
            )

        o_segments = offset_segments(t_segments, offset)
        segments += o_segments
        offset += get_audio_duration(audio_file) / 1000

    return segments

def offset_segments(segments, offset):
    for segment in segments:
        segment["start"] += offset
        segment["end"] += offset
        for word in segment["words"]:
            word["start"] += offset
            word["end"] += offset
    return segments

def reprocess_video(input_video, output_dir, output_file):
    final_output_path = os.path.join(output_dir, output_file)

    ffmpeg_command = [
        'ffmpeg',
        '-y',  # Overwrite output files without asking
        '-i', input_video,
        '-c:v', 'libx264',  # Use H.264 for video encoding
        '-c:a', 'aac',      # Use AAC for audio encoding
        '-b:a', '192k',     # Set audio bitrate
        '-ar', '44100',     # Set audio sample rate
        final_output_path
    ]

    result = subprocess.run(ffmpeg_command, capture_output=True, text=True)

    if result.returncode != 0:
        print("FFmpeg failed to reprocess the video.")
        print("FFmpeg stdout:", result.stdout)
        print("FFmpeg stderr:", result.stderr)
    else:
        print("Video reprocessed successfully.")

