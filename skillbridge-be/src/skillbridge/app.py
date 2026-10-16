import asyncio
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from skillbridge.api.api_v1.api import api_router
from skillbridge.api.services.moderation_service import preload_model
from skillbridge.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dynamically calculate the path to the 'src' directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    src_path = os.path.join(project_root, "src")
    sys.path.append(src_path)

    # Preload the Detoxify model now, off the event loop, so the first
    # moderation request doesn't pay the download+load cost.
    if settings.OPENAI_MODERATION_ENABLED:
        await asyncio.to_thread(preload_model)

    yield
    # (no teardown needed today; this is where you'd close connections, etc.)


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_STR}/openapi.json",
    root_path="/api",
    lifespan=lifespan,
)


class TrailingSlashMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Allow OpenAPI docs, favicon, etc.
        if "/api/v1" + request.url.path in [
            "/openapi.json",
            "/docs",
            "/redoc",
            "/favicon.ico",
        ]:
            return await call_next(request)

        # If not ending with a slash, reject
        if not request.url.path.endswith("/"):
            return JSONResponse(
                status_code=404,  # or 400, or 308 (Permanent Redirect) if you prefer
                content={
                    "detail": "Trailing slash '/' required at the end of the URL."
                },
            )

        return await call_next(request)


allow_origins = (
    [str(origin).rstrip("/") for origin in settings.BACKEND_CORS_ORIGINS]
    if settings.BACKEND_CORS_ORIGINS
    else (
        ["http://localhost:4200", "http://localhost:4201"]
        if settings.ENV.lower() not in {"deployment", "production", "prod"}
        else []
    )
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        field = error["loc"][-1]
        error_message = error["msg"]
        if error_message.lower().startswith("value error, "):
            error_message = error_message[len("Value error, "):]
        errors.append({"field": field, "message": f"{field}: {error_message}"})
    message = "; ".join(error["message"] for error in errors)
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": message or "Please check the submitted data.",
            "detail": errors,
        },
    )


# Set all CORS enabled origins
# if settings.BACKEND_CORS_ORIGINS:
#     app.add_middleware(
#         CORSMiddleware,
#         # allow_origins=["*"],
#         allow_origins=["http://localhost:4200"],
#         allow_credentials=False,
#         allow_methods=["*"],
#         allow_headers=["*"],
#         expose_headers=["Content-Disposition"],
#     )


# Routes
app.include_router(api_router, prefix=settings.API_STR)


@app.get("/")
async def root():
    return {"message": "Welcome to SkillBridge API"}


# Add the middleware
# app.add_middleware(TrailingSlashMiddleware)
