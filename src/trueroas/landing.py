from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from trueroas.core.config import settings
import anyio

router = APIRouter()


def _read_file_sync(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@router.get("/", response_class=HTMLResponse)
async def get_landing_page() -> str:
    """
    Serves the conversion-focused landing page.
    """
    static_path = settings.BASE_DIR / "static" / "index.html"
    try:
        content = await anyio.to_thread.run_sync(_read_file_sync, str(static_path))
        return content
    except FileNotFoundError:
        return "<html><body><h1>TrueROAS</h1></body></html>"
