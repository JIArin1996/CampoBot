"""Punto de entrada de CampoBot — FastAPI."""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv

from webhook import router as webhook_router, enviar_mensaje
from notifications.scheduler import iniciar_scheduler, detener_scheduler

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida: startup y shutdown."""
    logger.info("Iniciando CampoBot...")
    iniciar_scheduler(enviar_mensaje)
    yield
    logger.info("Deteniendo CampoBot...")
    detener_scheduler()


app = FastAPI(
    title="CampoBot",
    description="Chatbot de WhatsApp para administración de establecimiento agropecuario",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(webhook_router)


@app.get("/")
async def raiz():
    return {
        "app": "CampoBot",
        "version": "1.0.0",
        "estado": "operativo",
        "entorno": os.getenv("ENVIRONMENT", "development"),
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("ENVIRONMENT") == "development",
    )
