from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import time

app = Flask(__name__)
# Enable CORS so your GitHub Pages frontend can talk directly to this server
CORS(app, resources={r"/*": {"origins": "*"}})

TMP_DIR = "/tmp/dall_streams"
os.makedirs(TMP_DIR, exist_ok=True)

@app.route("/info", methods=["POST"])
def info():
    try:
        data = request.get_json(force=True)
        url = data.get("url", "").strip()
        if not url:
            return jsonify({"error": "No URL provided"}), 400
        
        ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
        formats = []
        seen_resolutions = set()
        
        # Audio default profile preset
        formats.append({"id": "bestaudio", "label": "Extract MP3 Audio", "ext": "mp3"})
        
        for f in info.get("formats", []):
            vcodec = f.get("vcodec", "none")
            height = f.get("height")
            
            if vcodec != "none" and height and height >= 360:
                if f"video_{height}p" not in seen_resolutions:
                    seen_resolutions.add(f"video_{height}p")
                    formats.append({
                        "id": f"bv*[height={height}]+ba/b[height={height}]",
                        "label": f"{height}p HD Quality",
                        "ext": "mp4"
                    })
                    
        return jsonify({
            "title": info.get("title", "DALL Shared Video"),
            "thumbnail": info.get("thumbnail", ""),
            "formats": formats
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/download", methods=["POST"])
def download():
    try:
        data = request.get_json(force=True)
        url = data.get("url", "").strip()
        format_id = data.get("format_id", "best").strip()
        
        if not url:
            return jsonify({"error": "No URL specified"}), 400
            
        timestamp = int(time.time())
        
        if format_id == "bestaudio":
            out_template = os.path.join(TMP_DIR, f"dall_{timestamp}.%(ext)s")
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": out_template,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
                "quiet": True
            }
        else:
            out_template = os.path.join(TMP_DIR, f"dall_{timestamp}.mp4")
            ydl_opts = {
                "format": format_id,
                "outtmpl": out_template,
                "merge_output_format": "mp4",
                "quiet": True
            }
            
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            meta = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(meta)
            if format_id == "bestaudio":
                filename = os.path.splitext(filename)[0] + ".mp3"

        if os.path.exists(filename):
            return send_file(filename, as_attachment=True, download_name=os.path.basename(filename))
        else:
            return jsonify({"error": "File processing timeout error"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
