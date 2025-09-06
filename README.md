# AnimalSafariKids

AnimalSafariKids is a tool for making AI generated short videos ("shorts" or "reels") with a ChatGPT generated script, narrated by ElevenLabs or OpenAI text-to-speech. DALL-E 3 generated background images are also added to the background. Captions with word highlighting are generated with [Captacity](https://github.com/unconv/captacity), which uses [OpenAI Whisper](https://github.com/openai/whisper).

## Quick Start
use python3.11
First, add your API-keys to the environment:

```console
$ export OPENAI_API_KEY=YOUR_OPENAI_API_KEY
$ export ELEVEN_API_KEY=YOUR_ELEVENLABS_API_KEY
```

Then, put your source content in a file, for example `source.txt` and run the `main.py`:

```console
$ ./main.py source.txt
Generating script...
Generating narration...
Generating images...
Generating video...
DONE! Your video is saved under your host Videos directory.
```

## Setup

- Create the external Docker network used by both services:
  - docker network create fortress-phronesis-net

- Start the image generation API (sd-api) on that network using its docker-compose.yml:
  - docker compose up -d

- Create/update `.env` with all required variables for this app (overwrites existing):
  - cat > .env <<'ENV'
IMAGE_API_BASE_URL=http://sd-api:8000
IMAGE_API_KIND=form
OLLAMA_HOST=http://ollama:11434
HOST_VIDEOS=$HOME/Videos
PROMPT_FILE=/app/instructions/prompt.txt
TTS_SERVICE=gtts
OPENAI_API_KEY=
ELEVEN_API_KEY=
IMAGE_API_TIMEOUT=300
ENV

- Build this app’s image:
  - docker build -t animalsafarikids .

- Run this app on the same network (loads .env from the mounted project):
  - docker run --rm --network fortress-phronesis-net -v "$(pwd)":/app animalsafarikids source.txt

## Image API (Stable Diffusion)

Configure the external Stable Diffusion HTTP API via `IMAGE_API_BASE_URL`. Only the root and path are configurable; the request body structure remains as defined by the app. The request is sent to `/txt2img` and the client supports both base64-style responses and URL-based responses.

- Set `IMAGE_API_BASE_URL` (example): `http://192.168.86.23:8000`
- Endpoint used by the app: `${IMAGE_API_BASE_URL}/txt2img`
- Response formats supported: A1111 base64 or `{ ok, path, url }`

You can also place this in a `.env` file in the project root; it is loaded automatically.

## Caption styling

Optionally, you can specify a settings file to define settings for the caption styling:

```console
$ ./main.py source.txt settings.json
```

The settings file can look like this, for example:

```json
{
    "font": "Bangers-Regular.ttf",
    "font_size": 130,
    "font_color": "yellow",

    "stroke_width": 3,
    "stroke_color": "black",

    "highlight_current_word": true,
    "word_highlight_color": "red",

    "line_count": 2,

    "padding": 50,

    "shadow_strength": 1.0,
    "shadow_blur": 0.1
}
```

## Docker

Build the Docker image:

```bash
docker build -t animalsafarikids .
```

Run the tool by mounting your working directory and providing a source file:

```bash
docker run --rm -v "$(pwd)":/app \
  -e OPENAI_API_KEY=YOUR_OPENAI_API_KEY \
  -e ELEVEN_API_KEY=YOUR_ELEVENLABS_API_KEY \
  -e IMAGE_API_BASE_URL=http://192.168.86.23:8000 \
  animalsafarikids source.txt
```

Replace `source.txt` with the path to your input text file. The generated video will be saved under your host `Videos/` directory.

Run with Docker Compose (recommended for host Videos mapping):

```bash
docker compose build
docker compose run --rm animalsafarikids
```

The generated shorts are written to your host directory set in `HOST_VIDEOS`.
If `HOST_VIDEOS` is not set, they default to a local folder `./host-videos` in this repo.
