import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.models.schemas import QueryRequest, QueryResponse
from app.services.research_pipeline import ResearchPipeline


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Research assistant API that searches arXiv, downloads PDFs, builds embeddings, "
        "retrieves evidence, and returns structured cited answers."
    ),
)
pipeline = ResearchPipeline(settings)
frontend_dir = Path(__file__).parent / "frontend"

app.mount("/static", StaticFiles(directory=frontend_dir / "static"), name="static")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Invalid request payload.",
            "errors": exc.errors(),
            "path": str(request.url.path),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error while serving %s", request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc) or "Internal server error.",
            "path": str(request.url.path),
        },
    )


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(frontend_dir / "index.html")


@app.get("/health")
async def healthcheck() -> dict[str, str | int]:
    return {"status": "ok", "version": settings.app_version, "max_papers": settings.max_papers}


@app.post("/query", response_model=QueryResponse)
async def query_research(request: QueryRequest) -> QueryResponse:
    return await pipeline.run(request)
