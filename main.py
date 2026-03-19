"""Punto de entrada de CampoBot — FastAPI."""

import json
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

    elif intencion == "INGRESO_HACIENDA":
        if not datos.get("cantidad"):
            guardado = False
            guardado_error = "No se pudo extraer la cantidad de animales"
        else:
            # Resolver potrero_id buscando por nombre (null si no se encuentra)
            potrero_id = None
            potrero_nombre = datos.get("potrero")
            if potrero_nombre:
                try:
                    supabase = db.get_client()
                    resp = (
                        supabase.table("potreros")
                        .select("id,nombre")
                        .ilike("nombre", f"%{potrero_nombre}%")
                        .limit(1)
                        .execute()
                    )
                    if resp.data:
                        potrero_id = resp.data[0]["id"]
                except Exception:
                    pass  # potrero no encontrado — queda null

            # Código de categoría para el nombre del lote
            _CAT_CODIGOS = {
                "vaquillona": "VAQ", "novillo": "NOV", "vaca": "VAC",
                "toro": "TOR", "ternero": "TER", "novillo gordo": "NOG",
            }
            categoria = (datos.get("categoria") or "otro").lower()
            cat_code = _CAT_CODIGOS.get(categoria, "LOT")
            anio = date.today().year

            # Nombre del lote: usar el extraído o generar el siguiente en secuencia
            if datos.get("nombre_lote"):
                nombre_lote = datos["nombre_lote"]
            else:
                try:
                    supabase = db.get_client()
                    resp = (
                        supabase.table("lotes")
                        .select("id")
                        .like("nombre", f"{cat_code}-{anio}-%")
                        .execute()
                    )
                    siguiente = len(resp.data) + 1
                except Exception:
                    siguiente = 1
                nombre_lote = f"{cat_code}-{anio}-{siguiente:02d}"

            lote = {
                "nombre": nombre_lote,
                "categoria": categoria,
                "potrero_id": potrero_id,
                "fecha_ingreso": datos.get("fecha") or date.today().isoformat(),
                "origen": datos.get("origen") or "compra",
                "activo": True,
            }
            movimiento = {
                "tipo": "ingreso",
                "potrero_destino_id": potrero_id,
                "fecha": lote["fecha_ingreso"],
                "observaciones": (
                    f"Ingreso de {datos['cantidad']} {categoria}"
                    + (f" al potrero {potrero_nombre}" if potrero_nombre else "")
                    + f" — Lote {nombre_lote}"
                ),
            }

            try:
                lote_creado = await db.insertar("lotes", lote)
                mov_creado = await db.insertar("movimientos_animales", movimiento)
                guardado = True
                # animales (trazabilidad individual) se carga en paso RF-02 con caravanas SNIG
                datos["_db"] = {"lote": lote_creado, "movimiento": mov_creado}
                datos["_nota_animales"] = "Registros individuales en tabla 'animales' se cargan al ingresar caravanas SNIG (RF-02)"
            except Exception as e:
                guardado = False
                guardado_error = str(e)

    elif intencion == "REGISTRO_SANIDAD":
        tipo = datos.get("tipo") or "dosificacion"
        producto = datos.get("producto")
        if not producto:
            guardado = False
            guardado_error = "No se pudo extraer el producto o tipo de evento sanitario"
        else:
            # Resolver lote_id desde el nombre de lote o potrero mencionado
            lote_id = None
            lote_o_potrero = datos.get("lote_o_potrero")
            if lote_o_potrero:
                try:
                    supabase = db.get_client()
                    # 1. Buscar como nombre de lote
                    resp = (
                        supabase.table("lotes")
                        .select("id,nombre,categoria")
                        .ilike("nombre", f"%{lote_o_potrero}%")
                        .eq("activo", True)
                        .limit(1)
                        .execute()
                    )
                    if resp.data:
                        lote_id = resp.data[0]["id"]
                    else:
                        # 2. Buscar como potrero → tomar el primer lote activo de ese potrero
                        resp_p = (
                            supabase.table("potreros")
                            .select("id,nombre")
                            .ilike("nombre", f"%{lote_o_potrero}%")
                            .limit(1)
                            .execute()
                        )
                        if resp_p.data:
                            resp_l = (
                                supabase.table("lotes")
                                .select("id,nombre,categoria")
                                .eq("potrero_id", resp_p.data[0]["id"])
                                .eq("activo", True)
                                .limit(1)
                                .execute()
                            )
                            if resp_l.data:
                                lote_id = resp_l.data[0]["id"]
                except Exception:
                    pass  # lote_id queda null

            evento = {
                "lote_id": lote_id,
                "tipo": tipo,
                "producto": producto,
                "cantidad": datos.get("cantidad"),
                "unidad": datos.get("unidad"),
                "costo_total": datos.get("costo_total"),
                "fecha_realizada": datos.get("fecha_realizada") or date.today().isoformat(),
                "fecha_programada": datos.get("fecha_programada"),
                "alerta_enviada": False,
                "observaciones": datos.get("observaciones"),
            }

            logger.info(
                "=== SUPABASE INSERT sanidad_eventos ===\n%s",
                json.dumps(evento, ensure_ascii=False, indent=2, default=str),
            )
            try:
                resultado = await db.insertar("sanidad_eventos", evento)
                guardado = True
                datos["_db"] = resultado
            except Exception as e:
                logger.error(
                    "=== SUPABASE ERROR sanidad_eventos ===\ntype=%s\nmessage=%s\ndetail=%s",
                    type(e).__name__,
                    str(e),
                    getattr(e, "details", getattr(e, "message", "")),
                )
                guardado = False
                guardado_error = f"{type(e).__name__}: {e}"

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
