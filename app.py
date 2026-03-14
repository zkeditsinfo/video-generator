from flask import Flask, request, jsonify
import requests
import os
from PIL import Image, ImageDraw, ImageFont
import textwrap
import tempfile
import base64
import subprocess

app = Flask(__name__)

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
VOICE_ID = os.environ.get("VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

def create_text_image(text, width=1080, height=1920):
    img = Image.new('RGB', (width, height), color=(15, 15, 15))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
    except:
        font = ImageFont.load_default()
    wrapped = textwrap.fill(text, width=20)
    draw.text((540, 960), wrapped, font=font, fill=(255, 255, 255), anchor="mm", align="center")
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img.save(tmp.name)
    return tmp.name

def generate_voice(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
    }
    response = requests.post(url, json=data, headers=headers)
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp.write(response.content)
    tmp.close()
    return tmp.name

@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    script = data.get("script", "")
    img_path = create_text_image(script)
    audio_path = generate_voice(script)
    output = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    cmd = [
        "ffmpeg", "-loop", "1", "-i", img_path,
        "-i", audio_path,
        "-c:v", "libx264", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-y", output.name
    ]
    subprocess.run(cmd, check=True)
    with open(output.name, "rb") as f:
        video_b64 = base64.b64encode(f.read()).decode()
    return jsonify({"video_base64": video_b64, "status": "success"})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
