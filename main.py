"""Punto de entrada de CampoBot — FastAPI."""

import os
import logging
from contextlib import asynccontextmanager
from datetime import date
from fastapi import FastAPI
from pydantic import BaseModel

from dotenv import load_dotenv

from webhook import router as webhook_router, enviar_mensaje
from notifications.scheduler import iniciar_scheduler, detener_scheduler
from ai.intent import clasificar_intencion
from ai import extractor
from db import supabase_client as db

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


# --- Endpoint de prueba ---

class MensajeInput(BaseModel):
    mensaje: str


# Extractores implementados por intención
_EXTRACTORES = {
    "REGISTRO_LLUVIA":    extractor.extraer_datos_lluvia,
    "CONSULTA_LLUVIA":    extractor.extraer_datos_lluvia,
    "INGRESO_HACIENDA":   extractor.extraer_datos_hacienda,
    "BAJA_HACIENDA":      extractor.extraer_datos_hacienda,
    "TRANSFERENCIA_HACIENDA": extractor.extraer_datos_hacienda,
    "CONSULTA_HACIENDA":  extractor.extraer_datos_hacienda,
    "REGISTRO_SANIDAD":   extractor.extraer_datos_sanidad,
    "PROGRAMAR_SANIDAD":  extractor.extraer_datos_sanidad,
    "CONSULTA_SANIDAD":   extractor.extraer_datos_sanidad,
    "REGISTRO_ECONOMIA":  extractor.extraer_datos_economia,
}

# Datos de ejemplo para intenciones sin extractor dedicado
_EJEMPLOS = {
    "REPORTE":         {"periodo": "mes_actual", "tipo": "resumen"},
    "GESTION_USUARIO": {"accion": "alta", "telefono": None, "rol": None},
    "REGISTRO_CHACRA": {"nombre": None, "cultivo": None, "superficie_has": None, "fecha_siembra": None},
    "AYUDA":           {"modulo": None},
    "CANCELAR":        {},
    "DESHACER":        {},
    "OTRO":            {},
}


@app.post("/test")
async def test_mensaje(body: MensajeInput):
    """
    Clasifica la intención del mensaje y extrae sus datos estructurados.
    Si la intención es REGISTRO_LLUVIA, guarda en Supabase.
    """
    clasificacion = await clasificar_intencion(body.mensaje)
    intencion = clasificacion.get("intencion", "OTRO")
    confianza = clasificacion.get("confianza", 0.0)
    datos_ia = clasificacion.get("datos", {})

    extractor_fn = _EXTRACTORES.get(intencion)
    if extractor_fn:
        datos = await extractor_fn(body.mensaje)
    else:
        datos = _EJEMPLOS.get(intencion, {})
        datos["_nota"] = "extractor no implementado aún — datos de ejemplo"

    # --- Guardar en DB según intención ---
    guardado = None
    guardado_error = None

    if intencion == "REGISTRO_LLUVIA":
        mm = datos.get("mm")
        if mm is None:
            guardado = False
            guardado_error = "No se pudo extraer la cantidad de mm"
        else:
            registro = {
                "fecha": datos.get("fecha") or date.today().isoformat(),
                "mm": float(mm),
                "observaciones": datos.get("observaciones"),
            }
            try:
                resultado = await db.insertar("lluvias", registro)
                guardado = True
                datos["_db"] = resultado
            except Exception as e:
                guardado = False
                guardado_error = str(e)

    respuesta = {
        "intencion": intencion,
        "confianza": confianza,
        "datos": datos,
        "datos_clasificador": datos_ia,
        "guardado": guardado,
    }
    if guardado_error:
        respuesta["guardado_error"] = guardado_error
    return respuesta


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("ENVIRONMENT") == "development",
    )
