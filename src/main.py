"""AgentGaia - Multi-LLM RFP Analysis Platform."""

import argparse
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from src.core.settings import get_settings, Settings
from src.core.database import init_database, close_database
from src.api.routes.chat import router as chat_router
from src.api.routes.upload import router as upload_router
from src.utils.logger import setup_logger, logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    settings = get_settings()
    logger.info(f"Starting AgentGaia v{settings.app_version} ({settings.app_env})")
    logger.info(f"Primary LLM: {settings.llm.primary_provider}")
    logger.info(f"Backup chain: {settings.llm.backup_chain}")

    # Pre-load API keys
    keys = settings.load_api_keys()
    available = [k for k, v in keys.items() if v]
    logger.info(f"Available API keys: {available}")

    # Initialize database connection pool
    try:
        await init_database()
        logger.info("Database connection pool initialized")
    except Exception as e:
        logger.warning(f"Database initialization failed (will use config fallback): {e}")

    yield

    # Shutdown
    try:
        await close_database()
    except Exception as e:
        logger.warning(f"Database close error: {e}")
    logger.info("Shutting down AgentGaia")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create FastAPI application.

    Args:
        settings: Application settings (uses global settings if not provided)

    Returns:
        FastAPI application instance
    """
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title="AgentGaia",
        description="Multi-LLM RFP Analysis Platform",
        version=settings.app_version,
        lifespan=lifespan,
        debug=settings.debug
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Static files and templates
    static_path = Path(__file__).parent / "static"
    templates_path = Path(__file__).parent / "templates"

    app.mount("/static", StaticFiles(directory=static_path), name="static")
    templates = Jinja2Templates(directory=templates_path)

    # Routes
    app.include_router(chat_router)
    app.include_router(upload_router)

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """Render main page."""
        return templates.TemplateResponse("index.html", {"request": request})

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        settings = get_settings()
        keys = settings.load_api_keys()

        return {
            "status": "healthy",
            "version": settings.app_version,
            "environment": settings.app_env,
            "providers": {
                provider: bool(key)
                for provider, key in keys.items()
            }
        }

    return app


# Create default app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser(description="AgentGaia Server")
    parser.add_argument(
        "--env",
        type=str,
        default="local",
        choices=["local", "dev", "prod"],
        help="Environment (local, dev, prod)"
    )
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host")
    parser.add_argument("--port", type=int, default=9003, help="Port")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()

    # Setup logger
    setup_logger(level="DEBUG" if args.env == "local" else "INFO")

    # Update settings
    import os
    os.environ["APP_ENV"] = args.env

    settings = get_settings(args.env)

    uvicorn.run(
        "src.main:app",
        host=args.host or settings.server.host,
        port=args.port or settings.server.port,
        reload=args.reload or settings.server.reload,
        workers=1 if args.reload else settings.server.workers
    )
