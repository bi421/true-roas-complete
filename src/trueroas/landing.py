from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import os
import anyio

router = APIRouter()

def _read_file_sync(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

@router.get("/", response_class=HTMLResponse)
async def get_landing_page():
    """
    Serves the conversion-focused landing page.
    """
    static_path = os.path.join("static", "index.html")
    # Production Fix: Use thread pool for blocking file I/O
    content = await anyio.to_thread.run_sync(_read_file_sync, static_path)
    return content