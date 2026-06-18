import json
import queue
import shutil
import threading
from pathlib import Path

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse

from src.inventory import extract_inventory
from src.run import run_pipeline

app = FastAPI()

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_run_lock = threading.Lock()
_DONE = object()
DOWNLOAD_ALLOWED = {"model.ifc", "model_ir.json", "debug.log"}


@app.get("/", response_class=HTMLResponse)
def index():
    return Path("frontend/index.html").read_text(encoding="utf-8")


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    dest = UPLOAD_DIR / file.filename
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    inv = extract_inventory(str(dest))
    inv["server_path"] = str(dest)
    inv["filename"] = file.filename
    return JSONResponse(inv)


@app.post("/run")
async def run(request: Request):
    payload = await request.json()
    cfg = payload.get("config", payload)

    if not _run_lock.acquire(blocking=False):
        return JSONResponse({"error": "이미 실행 중인 작업이 있다."}, status_code=409)

    q = queue.Queue()

    def worker():
        try:
            result = run_pipeline(cfg, stream_queue=q)
            q.put(("done", result["report"]["summary"]))
        except Exception as e:
            q.put(("failed", str(e)))
        finally:
            q.put(_DONE)
            _run_lock.release()

    threading.Thread(target=worker, daemon=True).start()

    def stream():
        while True:
            item = q.get()
            if item is _DONE:
                break
            if isinstance(item, tuple):
                kind, body = item
                data = {"summary": body} if kind == "done" else {"error": body}
                yield f"event: {kind}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
            else:
                yield f"data: {json.dumps({'line': item}, ensure_ascii=False)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/download/{name}")
def download(name: str):
    if name not in DOWNLOAD_ALLOWED:
        return JSONResponse({"error": "허용되지 않은 파일"}, status_code=404)
    path = Path("out") / name
    if not path.exists():
        return JSONResponse({"error": "파일 없음"}, status_code=404)
    return FileResponse(path, filename=name)


@app.get("/ir")
def ir():
    """Plan Audit 2D + 3D 폴백용 IR(JSON). 없으면 404."""
    path = Path("out") / "model_ir.json"
    if not path.exists():
        return JSONResponse({"error": "아직 IR이 없다. Run을 먼저 실행하라."}, status_code=404)
    return FileResponse(path, media_type="application/json")


SAMPLE_DXF = Path("data/지하주차장_1층_평면도.dxf")


@app.get("/sample")
def sample():
    """번들 샘플 DXF를 analyze한 결과(Sample 버튼용)."""
    if not SAMPLE_DXF.exists():
        return JSONResponse({"error": "번들 샘플 DXF가 없다."}, status_code=404)
    inv = extract_inventory(str(SAMPLE_DXF))
    inv["server_path"] = str(SAMPLE_DXF)
    inv["filename"] = SAMPLE_DXF.name
    return JSONResponse(inv)
