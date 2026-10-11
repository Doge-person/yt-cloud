"""YT Cloud Player — download a YouTube video at 1080p with yt-dlp on this
cloud machine, then play it back in the browser.

Run:  python app.py   (then open port 8000)
"""
import os
import threading
import uuid

from flask import Flask, jsonify, request, send_from_directory, abort
import yt_dlp

BASE = os.path.dirname(os.path.abspath(__file__))
DL_DIR = os.path.join(BASE, "downloads")
COOKIES = os.path.join(BASE, "cookies.txt")
os.makedirs(DL_DIR, exist_ok=True)

app = Flask(__name__)
jobs = {}  # job_id -> dict(state, percent, title, file, height, error)

# Prefer H.264 + AAC at 1080p so it plays in every browser; fall back to any
# codec at <=1080p, then to a single combined file.
FORMAT = (
    "bv*[height<=1080][vcodec^=avc1]+ba[ext=m4a]/"
    "bv*[height<=1080]+ba/"
    "b[height<=1080]/b"
)


def run_job(job_id, url):
    job = jobs[job_id]

    def hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            if total:
                job["percent"] = round(d.get("downloaded_bytes", 0) * 100 / total, 1)
            job["speed"] = d.get("_speed_str", "").strip()
            job["state"] = "downloading"
        elif d["status"] == "finished":
            job["state"] = "merging"

    opts = {
        "format": FORMAT,
        "merge_output_format": "mp4",
        "outtmpl": os.path.join(DL_DIR, "%(id)s.%(ext)s"),
        "noplaylist": True,
        "progress_hooks": [hook],
        "quiet": True,
        "no_warnings": True,
    }
    if os.path.exists(COOKIES):
        opts["cookiefile"] = COOKIES

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            job["title"] = info.get("title", "")
            job["height"] = info.get("height")
            job["file"] = os.path.basename(ydl.prepare_filename(info)).rsplit(".", 1)[0] + ".mp4"
        job["state"] = "done"
        job["percent"] = 100
    except Exception as e:  # surface yt-dlp's message to the page
        job["state"] = "error"
        job["error"] = str(e).replace("\x1b[0;31m", "").replace("\x1b[0m", "")


@app.post("/api/download")
def start_download():
    url = (request.get_json(silent=True) or {}).get("url", "").strip()
    if not url.startswith(("http://", "https://")):
        return jsonify(error="Paste a full YouTube link."), 400
    job_id = uuid.uuid4().hex[:8]
    jobs[job_id] = {"state": "starting", "percent": 0, "title": "", "file": None}
    threading.Thread(target=run_job, args=(job_id, url), daemon=True).start()
    return jsonify(job=job_id)


@app.get("/api/status/<job_id>")
def status(job_id):
    if job_id not in jobs:
        abort(404)
    return jsonify(jobs[job_id])


@app.get("/api/library")
def library():
    files = sorted(
        (f for f in os.listdir(DL_DIR) if f.endswith(".mp4")),
        key=lambda f: os.path.getmtime(os.path.join(DL_DIR, f)),
        reverse=True,
    )
    return jsonify([
        {"file": f, "mb": round(os.path.getsize(os.path.join(DL_DIR, f)) / 1e6, 1)}
        for f in files
    ])


@app.post("/api/cookies")
def upload_cookies():
    f = request.files.get("cookies")
    if not f:
        return jsonify(error="No file"), 400
    f.save(COOKIES)
    return jsonify(ok=True)


@app.get("/video/<path:name>")
def video(name):
    # conditional=True enables HTTP range requests, so seeking works.
    return send_from_directory(DL_DIR, name, conditional=True)


@app.get("/")
def index():
    return PAGE


PAGE = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>YT Cloud Player</title>
<style>
:root{--bg:#0f1115;--card:#181b22;--line:#2a2f3a;--text:#e8eaf0;--muted:#8b93a5;--accent:#ff4d4d;--ok:#3ecf8e}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:960px;margin:0 auto;padding:28px 16px}
h1{font-size:20px;margin:0 0 4px}.sub{color:var(--muted);margin:0 0 20px;font-size:13px}
form{display:flex;gap:8px}input[type=url]{flex:1;min-width:0;background:var(--card);border:1px solid var(--line);color:var(--text);padding:12px 14px;border-radius:10px;font-size:15px}
button{background:var(--accent);color:#fff;border:0;border-radius:10px;padding:0 18px;font-weight:600;cursor:pointer}button:disabled{opacity:.5;cursor:default}
.bar{height:6px;background:var(--line);border-radius:3px;margin:16px 0 6px;overflow:hidden;display:none}.bar>div{height:100%;width:0;background:var(--accent);transition:width .3s}
#msg{color:var(--muted);font-size:13px;min-height:20px;white-space:pre-wrap}#msg.err{color:var(--accent)}
video{width:100%;margin-top:16px;border-radius:12px;background:#000;display:none;aspect-ratio:16/9}
#title{font-weight:600;margin-top:10px}
h2{font-size:14px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin:32px 0 8px}
ul{list-style:none;padding:0;margin:0}li{display:flex;justify-content:space-between;gap:8px;padding:10px 12px;border:1px solid var(--line);border-radius:8px;margin-bottom:6px;cursor:pointer;background:var(--card)}li:hover{border-color:var(--accent)}
li span:last-child{color:var(--muted);white-space:nowrap}
details{margin-top:28px;color:var(--muted);font-size:13px}summary{cursor:pointer}
</style></head><body><main>
<h1>YT Cloud Player</h1>
<p class="sub">Downloads at up to 1080p with yt-dlp on this cloud machine, then plays it here.</p>
<form id="f"><input id="u" type="url" placeholder="https://www.youtube.com/watch?v=..." required><button id="go">Download</button></form>
<div class="bar" id="bar"><div></div></div><div id="msg"></div>
<video id="v" controls playsinline></video><div id="title"></div>
<h2>Downloaded</h2><ul id="lib"></ul>
<details><summary>Getting "Sign in to confirm you're not a bot"?</summary>
<p>YouTube sometimes blocks cloud IPs. Export your YouTube cookies as <code>cookies.txt</code> (Netscape format, e.g. with a "Get cookies.txt LOCALLY" browser extension) and upload them here, then retry.</p>
<input type="file" id="ck" accept=".txt"></details>
</main><script>
const $=id=>document.getElementById(id), bar=$('bar'), fill=bar.firstElementChild, msg=$('msg'), v=$('v');
function play(file,title){v.src='/video/'+encodeURIComponent(file);v.style.display='block';$('title').textContent=title||file;v.play().catch(()=>{});}
async function loadLib(){const r=await fetch('/api/library');const l=await r.json();$('lib').innerHTML='';
 l.forEach(x=>{const li=document.createElement('li');li.innerHTML='<span></span><span></span>';li.children[0].textContent=x.file;li.children[1].textContent=x.mb+' MB';li.onclick=()=>play(x.file);$('lib').appendChild(li);});}
$('f').onsubmit=async e=>{e.preventDefault();$('go').disabled=true;msg.className='';msg.textContent='Starting…';bar.style.display='block';fill.style.width='0';
 const r=await fetch('/api/download',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:$('u').value})});const d=await r.json();
 if(!r.ok){msg.className='err';msg.textContent=d.error;$('go').disabled=false;return;}
 const t=setInterval(async()=>{const s=await (await fetch('/api/status/'+d.job)).json();fill.style.width=(s.percent||0)+'%';
  if(s.state==='downloading')msg.textContent=`Downloading… ${s.percent||0}% ${s.speed||''}`;
  if(s.state==='merging')msg.textContent='Merging video + audio with ffmpeg…';
  if(s.state==='done'){clearInterval(t);msg.textContent=`Done — ${s.height||'?'}p`;$('go').disabled=false;play(s.file,s.title);loadLib();}
  if(s.state==='error'){clearInterval(t);msg.className='err';msg.textContent=s.error;$('go').disabled=false;}},700);};
$('ck').onchange=async()=>{const fd=new FormData();fd.append('cookies',$('ck').files[0]);await fetch('/api/cookies',{method:'POST',body:fd});msg.className='';msg.textContent='Cookies saved — try the download again.';};
loadLib();
</script></body></html>"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), threaded=True)
