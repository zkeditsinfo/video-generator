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
    img = Image.new('RGB', (width, height), color=(20, 20, 20))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 55)
    except:
        font = ImageFont.load_default()
    lines = textwrap.wrap(text, width=22)
    y = height // 2 - (len(lines) * 70) // 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        draw.text(((width - w) / 2, y), line, font=font, fill=(255, 255, 255))
        y += 75
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
    tmp_mp3 = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp_mp3.write(response.content)
    tmp_mp3.close()
    tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    subprocess.run([
        "ffmpeg", "-i", tmp_mp3.name,
        "-ar", "44100", "-ac", "2",
        "-y", tmp_wav.name
    ], check=True)
    return tmp_wav.name

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/generate", methods=["POST"])
def generate():
    try:
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
    except Exception as e:
        return jsonify({"error": str(e), "status": "failed"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
