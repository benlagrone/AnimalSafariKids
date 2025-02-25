from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import json
import os

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def authenticate():
    flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
    credentials = flow.run_local_server(port=0)
    return build("youtube", "v3", credentials=credentials)

def upload_video(basedir, settings):
    try:
        print("Starting upload process...")
        
        # Load data.json for video metadata
        with open(os.path.join(basedir, "data.json"), "r") as f:
            data = json.load(f)
        
        # Get upload settings
        upload_settings = settings.get("upload", {})
        youtube_channel = upload_settings.get("youtube_channel")
        category_id = upload_settings.get("youtube_category", "22")
        
        print(f"Authenticating with YouTube for channel: {youtube_channel}")
        youtube = authenticate()
        
        # Verify video file exists and size
        video_path = os.path.join(basedir, "final_output.mp4")
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found at: {video_path}")
        
        file_size = os.path.getsize(video_path)
        print(f"Found video file: {video_path} (Size: {file_size/1024/1024:.2f} MB)")
        
        # Prepare the video upload request
        request_body = {
            "snippet": {
                "title": data.get("title", ""),
                "description": data.get("description", ""),
                "tags": data.get("tags", []),
                "categoryId": category_id
            },
            "status": {
                "privacyStatus": "private",
                "selfDeclaredMadeForKids": False
            }
        }
        
        print("Creating upload request...")
        media = MediaFileUpload(
            video_path,
            mimetype="video/mp4",
            resumable=True,
            chunksize=1024*1024
        )
        
        if not media.has_stream():
            raise ValueError("Failed to create media file upload stream")
        
        # Execute the upload request
        request = youtube.videos().insert(
            part="snippet,status",
            body=request_body,
            media_body=media
        )
        
        print(f"Starting upload to YouTube channel: {youtube_channel}")
        
        # Handle chunked upload with progress
        response = None
        while response is None:
            try:
                status, response = request.next_chunk()
                if status:
                    print(f"Uploaded {int(status.progress() * 100)}%")
            except Exception as e:
                print(f"An error occurred during upload: {str(e)}")
                print(f"Request body: {request_body}")
                print(f"Media file size: {file_size/1024/1024:.2f} MB")
                if hasattr(e, 'content'):
                    try:
                        error_content = json.loads(e.content.decode('utf-8'))
                        print(f"Error details: {json.dumps(error_content, indent=2)}")
                    except json.JSONDecodeError:
                        print("Failed to decode error content")
                raise
        
        print("Upload completed, saving response data...")
        
        # Check if response is a list and handle accordingly
        if isinstance(response, list):
            print("Unexpected response format: list")
            print(f"Response content: {response}")
            raise ValueError("Unexpected response format: list")
        
        # Save complete response plus additional metadata to upload.json
        upload_data = {
            "youtube_response": response,
            "metadata": {
                "video_id": response.get("id"),
                "title": data.get("title", ""),
                "url": f"https://youtu.be/{response.get('id')}",
                "short_url": f"https://youtube.com/shorts/{response.get('id')}",
                "upload_time": response.get("snippet", {}).get("publishedAt", ""),
                "channel_id": youtube_channel,
                "original_request": request_body
            }
        }
        
        with open(os.path.join(basedir, "upload.json"), "w") as f:
            json.dump(upload_data, f, indent=2)
        
        video_id = response.get("id")
        if video_id:
            print(f"Upload complete! Video ID: {video_id}")
            print(f"Video URL: https://youtu.be/{video_id}")
            print(f"Shorts URL: https://youtube.com/shorts/{video_id}")
            print(f"Upload data saved to {os.path.join(basedir, 'upload.json')}")
            return video_id
        else:
            raise ValueError("No video ID in response")
        
    except Exception as e:
        print(f"Upload failed with error: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Video path: {video_path}")
        if 'file_size' in locals():
            print(f"File size: {file_size/1024/1024:.2f} MB")
        if 'request_body' in locals():
            print(f"Request body: {request_body}")
        if hasattr(e, 'content'):
            try:
                error_content = json.loads(e.content.decode('utf-8'))
                print(f"Error details: {json.dumps(error_content, indent=2)}")
            except json.JSONDecodeError:
                print("Failed to decode error content")
        raise
        print(f"Upload failed with error: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Video path: {video_path}")
        if 'file_size' in locals():
            print(f"File size: {file_size/1024/1024:.2f} MB")
        if 'request_body' in locals():
            print(f"Request body: {request_body}")
        if hasattr(e, 'content'):
            try:
                error_content = json.loads(e.content.decode('utf-8'))
                print(f"Error details: {json.dumps(error_content, indent=2)}")
            except json.JSONDecodeError:
                print("Failed to decode error content")
        raise