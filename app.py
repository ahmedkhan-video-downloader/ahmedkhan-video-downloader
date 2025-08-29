import os, re, subprocess, shlex, tempfile, uuid, json
from datetime import datetime
from flask import Flask, render_template, request, send_file, redirect, url_for, flash, session, abort
from yt_dlp import YoutubeDL

app = Flask(__name__, static_url_path="/static")
app.secret_key = "change-this-secret"

FFMPEG_BIN = "ffmpeg"
WATERMARK_TEXT = "AHMED KHAN • IG:_98sf • TT:_98ak • TG:AHMED_KHANA"

DOWNLOAD_ROOT = os.path.abspath("downloads")
os.makedirs(DOWNLOAD_ROOT, exist_ok=True)

def safe_filename(name):
    return re.sub(r"[^-\u0621-\u064Aa-zA-Z0-9_. ]+", "", name).strip() or "video"

def detect_ffmpeg():
    try:
        subprocess.run([FFMPEG_BIN, "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except Exception:
        return False

def process_download(url):
    if not detect_ffmpeg():
        raise RuntimeError("ffmpeg غير متوفر")

    task_id = datetime.utcnow().strftime("%Y%m%d%H%M%S") + "_" + uuid.uuid4().hex[:8]
    task_dir = os.path.join(DOWNLOAD_ROOT, task_id)
    os.makedirs(task_dir, exist_ok=True)
    raw_path = os.path.join(task_dir, "raw.%(ext)s")

    ydl_opts = {
        "outtmpl": raw_path,
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "quiet": True,
        "noplaylist": True,
    }
    info = {}
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    downloaded_files = [f for f in os.listdir(task_dir) if f.startswith("raw.")]
    if not downloaded_files:
        downloaded_files = [f for f in os.listdir(task_dir) if f.endswith(".mp4")]
    if not downloaded_files:
        raise RuntimeError("لم يتم العثور على الملف بعد التحميل")

    raw_file = os.path.join(task_dir, downloaded_files[0])
    output_file = os.path.join(task_dir, "output.mp4")

    drawtext = f"drawbox=x=0:y=h-60:w=w:h=60:color=black@0.5:t=fill,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='{WATERMARK_TEXT}':fontcolor=white:fontsize=24:x=10:y=h-45"
    cmd = f'{FFMPEG_BIN} -y -i {shlex.quote(raw_file)} -vf "{drawtext}" -c:a copy {shlex.quote(output_file)}'
    subprocess.run(cmd, shell=True, check=True)

    meta = {
        "title": info.get("title"),
        "uploader": info.get("uploader"),
        "task_id": task_id
    }
    return task_id, output_file, meta

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("url","").strip()
        if not url:
            flash("ضع رابط الفيديو!", "error")
            return redirect(url_for("index"))
        try:
            task_id, output_file, meta = process_download(url)
            return send_file(output_file, as_attachment=True, download_name=f"{safe_filename(meta['title'])}.mp4")
        except Exception as e:
            flash(f"خطأ بالتحميل: {e}", "error")
            return redirect(url_for("index"))
    return render_template("index.html", watermark=WATERMARK_TEXT)

@app.errorhandler(404)
def nf(e):
    return render_template("404.html"), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
