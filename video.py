import os
import cv2
import numpy as np
import math
from pydub import AudioSegment
import subprocess
import captacity
import json

def get_audio_duration(audio_file):
    return len(AudioSegment.from_file(audio_file))

def resize_image(image, width, height):
    aspect_ratio = image.shape[1] / image.shape[0]
    if aspect_ratio > (width / height):
        new_width = width
        new_height = int(width / aspect_ratio)
    else:
        new_height = height
        new_width = int(height * aspect_ratio)
    return cv2.resize(image, (new_width, new_height))

def create(narrations, output_dir, output_filename, settings):
    # Retrieve video settings
    # video_settings = settings.get("video", {})
    # width = video_settings.get("width", 1080)
    # height = video_settings.get("height", 1920)
    # frame_rate = video_settings.get("fps", 30)
    # codec = video_settings.get("codec", "avc1")
    # fade_time = video_settings.get("fade_time", 1000)
    video_settings = {}
    width = video_settings.get("width", 1024)
    height = video_settings.get("height", 1024)
    frame_rate = video_settings.get("fps", 30)
    codec = video_settings.get("codec", "avc1")
    fade_time = video_settings.get("fade_time", 1000)

    # Create a VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*codec)
    temp_video = os.path.join(output_dir, "temp_video.mp4")
    out = cv2.VideoWriter(temp_video, fourcc, frame_rate, (width, height))

    # Load images and create video
    image_paths = os.listdir(os.path.join(output_dir, "images"))
    image_count = len(image_paths)

    for i in range(image_count):
        image1 = cv2.imread(os.path.join(output_dir, "images", f"image_{i+1}.png"))
        image2 = cv2.imread(os.path.join(output_dir, "images", f"image_{i+2}.png")) if i+1 < image_count else cv2.imread(os.path.join(output_dir, "images", f"image_1.png"))

        image1 = resize_image(image1, width, height)
        image2 = resize_image(image2, width, height)

        narration = os.path.join(output_dir, "narrations", f"narration_{i+1}.mp3")
        duration = get_audio_duration(narration)

        if i > 0:
            duration -= fade_time
        if i == image_count-1:
            duration -= fade_time

        for _ in range(math.floor(duration/1000*frame_rate)):
            vertical_video_frame = np.zeros((height, width, 3), dtype=np.uint8)
            vertical_video_frame[:image1.shape[0], :] = image1
            out.write(vertical_video_frame)

        for alpha in np.linspace(0, 1, math.floor(fade_time/1000*frame_rate)):
            blended_image = cv2.addWeighted(image1, 1 - alpha, image2, alpha, 0)
            vertical_video_frame = np.zeros((height, width, 3), dtype=np.uint8)
            vertical_video_frame[:image1.shape[0], :] = blended_image
            out.write(vertical_video_frame)

    out.release()
    cv2.destroyAllWindows()

    # Add narration to video
    with_narration = "with_narration.mp4"
    add_narration_to_video(narrations, temp_video, output_dir, with_narration)

    # Add captions to video
    output_path = os.path.join(output_dir, output_filename)
    input_path = os.path.join(output_dir, with_narration)
    segments = create_segments(narrations, output_dir)

    caption_settings = settings.get("captions", {})
    print('***')
    print(caption_settings)
    try:
        captacity.add_captions(
            video_file=input_path,
            output_file=output_path,
            segments=segments,
            print_info=True,
            **caption_settings,
        )
        print("Captions added successfully.")
    except Exception as e:
        print("Failed to add captions:", str(e))

    # Clean up temporary files only if the final output is successful
    if os.path.exists(output_path):
        os.remove(input_path)
        os.remove(temp_video)
    else:
        print("Final output not created, skipping cleanup.")

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