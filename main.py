import uvicorn
from src.trueroas.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "src.trueroas.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        workers=1,  # DuckDB single-writer restriction
        reload=False
    )