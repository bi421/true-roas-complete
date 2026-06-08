from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import os

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def get_landing_page():
    """
    Serves the conversion-focused landing page.
    """
    static_path = os.path.join("static", "index.html")
    with open(static_path, "r", encoding="utf-8") as f:
        content = f.read()
    return content
