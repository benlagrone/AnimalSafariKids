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

        # Get branding settings
    branding_settings = settings.get("branding", {})
    logo_path = os.path.join("branding", branding_settings.get("logo", ""))
    logo_x = branding_settings.get("logo-x", 5)  # offset from right
    logo_y = branding_settings.get("logo-y", 5)  # offset from bottom
    logo_scale = branding_settings.get("logo-scale", 0.1)
        # Load and resize logo if it exists
    logo = None
    if os.path.exists(logo_path):
        logo = cv2.imread(logo_path, cv2.IMREAD_UNCHANGED)  # Read with alpha channel
        # Resize logo if needed (adjust size as needed)
        logo_height = int(height * logo_scale)  # 10% of video height
        aspect_ratio = logo.shape[1] / logo.shape[0]
        logo_width = int(logo_height * aspect_ratio)
        logo = cv2.resize(logo, (logo_width, logo_height))
    
        # Load narration data from JSON
    with open(os.path.join(output_dir, "narration.json"), "r") as f:
        narration_data = json.load(f)


    # Create a VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*codec)
    temp_video = os.path.join(output_dir, "temp_video.mp4")
    out = cv2.VideoWriter(temp_video, fourcc, frame_rate, (width, height))
    # Fallback if the requested codec isn't available (e.g., avc1/H.264)
    if not out.isOpened():
        fallback_codec = 'mp4v'
        fourcc = cv2.VideoWriter_fourcc(*fallback_codec)
        out = cv2.VideoWriter(temp_video, fourcc, frame_rate, (width, height))
        if out.isOpened():
            print(f"Warning: Requested codec '{codec}' unavailable. Using fallback '{fallback_codec}'.")
        else:
            raise RuntimeError("Failed to initialize VideoWriter with both primary and fallback codecs.")

    def add_logo_to_frame(frame):
        if logo is None:
            return frame
        
        # Create a copy of the frame
        result = frame.copy()
        
        # Calculate logo position from bottom right
        pos_x = width - logo.shape[1] - logo_x
        pos_y = height - logo.shape[0] - logo_y
        
        # If logo has alpha channel (PNG)
        if logo.shape[2] == 4:
            # Get alpha channel
            alpha = logo[:, :, 3] / 255.0
            # Get RGB channels
            for c in range(3):
                result[pos_y:pos_y+logo.shape[0], pos_x:pos_x+logo.shape[1], c] = \
                    (1 - alpha) * result[pos_y:pos_y+logo.shape[0], pos_x:pos_x+logo.shape[1], c] + \
                    alpha * logo[:, :, c]
        else:
            # If no alpha channel, just overlay the logo
            result[pos_y:pos_y+logo.shape[0], pos_x:pos_x+logo.shape[1]] = logo[:, :, :3]
            
        return result

    # Ensure at least one generated image exists before proceeding
    first_image_path = os.path.join(output_dir, "images", "image_1.png")
    if not os.path.exists(first_image_path):
        raise RuntimeError(
            f"No generated images found at {os.path.dirname(first_image_path)}. "
            "Image generation likely failed earlier. Check the logs above."
        )

    for i, narration_item in enumerate(narration_data):
        current_image_path = os.path.join(output_dir, "images", f"image_{i+1}.png")
        current_image = cv2.imread(current_image_path)
        if current_image is None:
            raise RuntimeError(f"Failed to load image: {current_image_path}")
        current_image = cv2.resize(current_image, (width, height))

        # Load the next image if it exists
        if i + 1 < len(narration_data):
            next_image_path = os.path.join(output_dir, "images", f"image_{i+2}.png")
            next_image = cv2.imread(next_image_path)
            if next_image is None:
                # If the next image is missing, just use a black frame as fallback for transition
                next_image = np.zeros((height, width, 3), dtype=np.uint8)
            else:
                next_image = cv2.resize(next_image, (width, height))
        else:
            next_image = np.zeros((height, width, 3), dtype=np.uint8)

        # Calculate frames for this narration
        duration_ms = narration_item["duration"]
        frames_for_narration = int((duration_ms / 1000) * frame_rate)

        if i + 1 < len(narration_data):
            # For images with transitions, reserve frames for the slide effect
            slide_frames = int(frame_rate / slide_speed_multiplier)
            static_frames = frames_for_narration - slide_frames
            
            # Write the static image frames with logo
            for _ in range(static_frames):
                frame_with_logo = add_logo_to_frame(current_image)
                out.write(frame_with_logo)

            # Add sliding effect with logo
            for frame in range(slide_frames):
                offset = int((frame / slide_frames) * width)
                offset = min(offset, width - 1)
                
                slide_image = next_image.copy()
                slide_image[:, :width-offset] = current_image[:, offset:]
                
                # Add logo to the slide frame
                frame_with_logo = add_logo_to_frame(slide_image)
                out.write(frame_with_logo)
        else:
            # For the last image, no transition needed
            for _ in range(frames_for_narration):
                frame_with_logo = add_logo_to_frame(current_image)
                out.write(frame_with_logo)

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
