# backend/app/main.py --- starts the whole backend
"""
CodeSense — FastAPI Application Entry Point
"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"  #get path of .env file
load_dotenv(dotenv_path=env_path)  #load env variables(secrets) to memory (IMPORTANT)


from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI #backend equivalent of react
from fastapi.responses import JSONResponse #allows return JSONResponse({...}) ---  Equivalent: return {"status":"ok"};

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app_logger import setup_logging
from app.core.middleware import register_middleware

setup_logging() #runs immediately when file starts

from app_logger import logger  # get logger object which writes to Console,Log files,Render logs,Docker logs
#Logger is a centralized debugging and monitoring tool used to track application events, warnings and failures.
#print cannot classify messages but logger can so it is used

# Without Async: download file,wait,download image,wait,download data,wait --- Everything waits
#   With Async : start file download,start image download,start data download,wait for all --- Much faster.
# FastAPI uses async because many users can access simultaneously.Server shouldn't block.
# Example: await connect_db() --- means: Start database connection. While waiting, let other tasks run.

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle: connect DB and pre-load ML models."""
    settings = get_settings()  #loads APP_NAME,APP_VERSION,MONGO_URI,JWT_SECRET,GEMINI_KEY from config
    logger.info("Starting {name} v{version} [{env}] …", name=settings.APP_NAME, version=settings.APP_VERSION, env=settings.APP_ENV)

    # ENV Check
    llm_provider = os.getenv("LLM_PROVIDER")
    openai_key_loaded = bool(os.getenv("OPENAI_API_KEY")) #open ai key check
    logger.info("[ENV CHECK] LLM_PROVIDER={provider} OPENAI_API_KEY loaded={key}", provider=llm_provider, key=openai_key_loaded) #print to logs

    # Startup validation
    from app.ml.llm_client import validate_startup
    try:
        # runs is gemini/openai/ollama/anthropic working before server starts
        await validate_startup() #(IMPORTANT)
    except Exception as exc: #exception handling if gemini fails dont crash just log error
        logger.exception("LLM Startup Validation Failed")

    # Database
    from app.db.mongodb import connect_db
    # connect mongodb
    await connect_db() #(IMPORTANT)

    logger.info("{name} is ready to serve requests.", name=settings.APP_NAME)
    
    #everything before yield is startup
    #this is where the server runs
    yield
    #evyrthing after yield is shutdown
    
    # Shutdown
    from app.db.mongodb import disconnect_db
    await disconnect_db()
    logger.info("{name} shutdown complete.", name=settings.APP_NAME)


# creates backend application

def create_app() -> FastAPI:
    settings = get_settings()
    #creates server
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "CodeSense — AI-powered semantic repository intelligence platform. "
            "Upload GitHub repos or ZIPs, then search, query, and analyse codebases with AI."
        ),
        docs_url="/docs", #creates: localhost:8000/docs --- Swagger UI
        redoc_url="/redoc", # swagger UI is auto-generated API documentation provided by FastAPI that allows developers to view and test endpoints directly from the browser.
        openapi_url="/openapi.json",
        lifespan=lifespan, #use startup/shutdown function defined above
    )

    # Middleware (order is important — see middleware.py)                   Adds:CORS,Security,Request processing before routes run
    # Handles CORS (Cross-Origin Resource Sharing) so the React frontend
    # can communicate with this backend across different ports/domains.     flow:request->middleware->route->response
    # CORS allows browsers to safely make requests between different domains.(frontend to backend)
    # security middleware checks authentication of user(like 2 step verification after being verified in frontend)
    register_middleware(app)

    # Exception handlers
    # formats them into clean, predictable JSON responses for the frontend.
    register_exception_handlers(app)

    # API routes --- import all end points(specific URL)
    # Pulls in all route definitions from api/router.py (/auth, /repos, /qa, etc.)
    from app.api.router import api_router #repositories.py,auth.py,qa.py,search.py all merged into api_router
    app.include_router(api_router) #attaches all APIs (IMPORTANT)
    #API is the complete communication interface exposed by a backend.
    #An endpoint is a specific URL within that API that performs one operation.
    
    # Root redirect
    @app.get("/", include_in_schema=False)
    async def root():
        return JSONResponse({"service": settings.APP_NAME, "version": settings.APP_VERSION, "docs": "/docs"})

    return app #give completed backend(IMPORTANT)


app = create_app()