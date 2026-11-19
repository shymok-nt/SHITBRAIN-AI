"""SHITBRAIN AI — dependency-free local creative reference studio."""
from __future__ import annotations

import base64
import json
import os
import re
import sqlite3
import subprocess
import tempfile
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
UPLOADS = DATA / "uploads"
DB = DATA / "shitbrain.sqlite3"
HOST = os.environ.get("SHITBRAIN_HOST", "127.0.0.1")
PORT = int(os.environ.get("SHITBRAIN_PORT", "8765"))
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
TEXT_MODEL = os.environ.get("SHITBRAIN_TEXT_MODEL", "gemma3:4b")
VISION_MODEL = os.environ.get("SHITBRAIN_VISION_MODEL", "gemma3:4b")
MAX_FILE = 25 * 1024 * 1024
ALLOWED = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif", "video/mp4": ".mp4", "video/webm": ".webm", "video/quicktime": ".mov"}


def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db


def init():
    UPLOADS.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS examples (
          id TEXT PRIMARY KEY, kind TEXT NOT NULL, filename TEXT NOT NULL,
          media_type TEXT NOT NULL, note TEXT NOT NULL DEFAULT '',
          analysis TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'saved',
          created_at TEXT NOT NULL)""")


def ollama(payload):
    req = urllib.request.Request(OLLAMA_URL + "/api/generate", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=150) as resp:
            return json.load(resp).get("response", "").strip()
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError("Ollama yanıt vermiyor. Ollama'yı aç ve gerekli modeli indir. " + str(exc)) from exc


def video_frame(path):
    """Extract a representative JPEG in memory without retaining temporary frames."""
    try:
        result = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-ss", "1", "-i", str(path), "-frames:v", "1", "-vf", "scale=640:-2", "-f", "image2pipe", "-vcodec", "mjpeg", "-"], capture_output=True, timeout=20, check=True)
        return result.stdout or None
    except (OSError, subprocess.SubprocessError):
        return None


def analyze_row(row):
    path = UPLOADS / row["filename"]
    img = path.read_bytes() if row["kind"] == "image" else video_frame(path)
    if row["kind"] == "video" and not img:
        raise RuntimeError("Video karesi çıkarılamadı. FFmpeg kurulu olmalı; şimdilik örneğe not ekleyebilirsin.")
    if len(img) > 9_000_000:
        raise RuntimeError("Görsel analiz için çok büyük. Daha küçük bir görsel dene.")
    prompt = ("Bu görsel Türkçe internet absürt mizahı için bir REFERANS. Gördüklerini tarif et, varsa görseldeki yazıyı oku; "
              "espri mekanizmasını, tonunu, beklenmedik karşıtlığı ve neden komik olabileceğini kısaca analiz et. "
              "Videoysa yalnızca TEK KARE görüyorsun, hareket ve sesi biliyormuş gibi davranma. "
              "Kullanıcının notu: " + row["note"] + "\nYanıt Türkçe olsun. Gereksiz uzun yazma.")
    return ollama({"model": VISION_MODEL, "prompt": prompt, "images": [base64.b64encode(img).decode()], "stream": False, "options": {"temperature": .4}})


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, obj):
        raw = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def read_json(self):
        size = int(self.headers.get("Content-Length", "0"))
        if size < 1 or size > MAX_FILE * 2:
            raise ValueError("İstek boyutu geçersiz (en fazla 25 MB dosya).")
        return json.loads(self.rfile.read(size))

    def do_GET(self):
        if self.path == "/":
            raw = (ROOT / "static" / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        elif self.path == "/api/examples":
            with connect() as db:
                rows = db.execute("SELECT * FROM examples ORDER BY created_at DESC").fetchall()
            self.send_json(200, {"examples": [dict(r) for r in rows]})
        elif self.path.startswith("/media/"):
            name = self.path.removeprefix("/media/")
            if not re.fullmatch(r"[a-f0-9]{32}\.(png|jpg|webp|gif|mp4|webm|mov)", name):
                return self.send_json(404, {"error": "Dosya bulunamadı."})
            path = UPLOADS / name
            if not path.is_file():
                return self.send_json(404, {"error": "Dosya bulunamadı."})
            import mimetypes
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(path.stat().st_size))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            with path.open("rb") as f:
                while chunk := f.read(1024 * 1024):
                    self.wfile.write(chunk)
        else:
            self.send_json(404, {"error": "Bilinmeyen adres."})

    def do_POST(self):
        try:
            if self.path == "/api/upload":
                body = self.read_json()
                media_type = body.get("type", "")
                if media_type not in ALLOWED:
                    raise ValueError("Bu dosya türü desteklenmiyor.")
                try:
                    encoded = body["data"].split(",", 1)[-1]
                    blob = base64.b64decode(encoded, validate=True)
                except (KeyError, ValueError) as exc:
                    raise ValueError("Dosya okunamadı.") from exc
                if not blob or len(blob) > MAX_FILE:
                    raise ValueError("Dosya boş veya 25 MB sınırını aşıyor.")
                signature = {"image/png": blob.startswith(b"\x89PNG\r\n\x1a\n"), "image/jpeg": blob.startswith(b"\xff\xd8"), "image/webp": blob[8:12] == b"WEBP", "image/gif": blob.startswith((b"GIF87a", b"GIF89a")), "video/mp4": b"ftyp" in blob[:16], "video/quicktime": b"ftyp" in blob[:16], "video/webm": blob.startswith(b"\x1a\x45\xdf\xa3")}
                if not signature[media_type]:
                    raise ValueError("Dosyanın içeriği bildirilen türle uyuşmuyor.")
                name = uuid.uuid4().hex + ALLOWED[media_type]
                (UPLOADS / name).write_bytes(blob)
                example_id = uuid.uuid4().hex
                note = str(body.get("note", ""))[:1500]
                kind = media_type.split("/")[0]
                with connect() as db:
                    db.execute("INSERT INTO examples (id, kind, filename, media_type, note, created_at) VALUES (?, ?, ?, ?, ?, ?)", (example_id, kind, name, media_type, note, datetime.now(timezone.utc).isoformat()))
                self.send_json(201, {"id": example_id})
            elif self.path == "/api/analyze":
                body = self.read_json()
                with connect() as db:
                    row = db.execute("SELECT * FROM examples WHERE id = ?", (body.get("id"),)).fetchone()
                    if not row:
                        return self.send_json(404, {"error": "Örnek bulunamadı."})
                    result = analyze_row(row)
                    db.execute("UPDATE examples SET analysis = ?, status = 'analyzed' WHERE id = ?", (result, row["id"]))
                self.send_json(200, {"analysis": result})
            elif self.path == "/api/generate":
                body = self.read_json()
                idea = str(body.get("idea", ""))[:1200].strip()
                with connect() as db:
                    rows = db.execute("SELECT note, analysis FROM examples ORDER BY created_at DESC LIMIT 12").fetchall()
                references = "\n".join("- " + (r["analysis"] or r["note"])[:600] for r in rows if r["analysis"] or r["note"])
                if not references:
                    raise ValueError("Önce birkaç örnek yükleyip analiz et veya not ekle.")
                prompt = ("Sen özgün, doğal ve absürt Türkçe internet mizahı üreten yaratıcı yazarsın. "
                          "Aşağıdakiler üslup/komedi mekanizması referansıdır; cümleleri kopyalama, gerçek kişileri taklit etme. "
                          "Yapay zekâ klişeleri, emoji, hashtag, açıklama ve giriş cümlesi kullanma. "
                          "Her biri 280 karakterden kısa, birbirinden farklı 5 özgün kısa paylaşım yaz. "
                          "Yalnızca numaralı paylaşımlar dön.\nREFERANSLAR:\n" + references + "\nKONU: " + (idea or "rastgele gündelik absürtlük"))
                result = ollama({"model": TEXT_MODEL, "prompt": prompt, "stream": False, "options": {"temperature": .95}})
                self.send_json(200, {"result": result})
            else:
                self.send_json(404, {"error": "Bilinmeyen adres."})
        except (ValueError, json.JSONDecodeError) as exc:
            self.send_json(400, {"error": str(exc)})
        except RuntimeError as exc:
            self.send_json(503, {"error": str(exc)})
        except Exception as exc:
            print("SERVER ERROR:", repr(exc))
            self.send_json(500, {"error": "Sunucu hatası. Terminal çıktısını kontrol et."})


if __name__ == "__main__":
    init()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"SHITBRAIN AI hazır: http://{HOST}:{PORT}")
    print(f"Veriler: {DATA}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nKapatılıyor...")
    finally:
        server.server_close()
