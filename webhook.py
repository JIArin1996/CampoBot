"""Receptor y procesador de mensajes entrantes de WhatsApp (Meta Cloud API)."""

import os
import logging
import httpx
from fastapi import APIRouter, Request, Response, HTTPException
from db import supabase_client as db
from ai import vision, whisper
from router import procesar_texto
from utils import formatter

logger = logging.getLogger(__name__)
router = APIRouter()

WHATSAPP_API_URL = "https://graph.facebook.com/v20.0"


# --- Verificación del webhook (GET) ---

@router.get("/webhook")
async def verificar_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == os.getenv("VERIFY_TOKEN"):
        logger.info("Webhook verificado correctamente.")
        return Response(content=challenge, media_type="text/plain")

    raise HTTPException(status_code=403, detail="Token de verificación inválido")


# --- Recepción de mensajes (POST) ---

@router.post("/webhook")
async def recibir_mensaje(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Payload inválido")

    # Meta envía un array de entries
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages = value.get("messages", [])

            for msg in messages:
                await _procesar_mensaje(msg)

    # WhatsApp requiere siempre 200
    return {"status": "ok"}


async def _procesar_mensaje(msg: dict):
    """Procesa un mensaje individual según su tipo."""
    telefono = msg.get("from", "")
    msg_type = msg.get("type", "")

    # Verificar si el usuario está registrado
    usuario = await db.consultar_uno("usuarios", {"telefono": telefono, "activo": True})
    if not usuario:
        logger.warning(f"Mensaje de número no registrado: {telefono}")
        await enviar_mensaje(telefono, formatter.error(
            "Tu número no está registrado en CampoBot. "
            "Contactá al administrador para obtener acceso."
        ))
        return

    try:
        if msg_type == "text":
            texto = msg.get("text", {}).get("body", "")
            respuesta = await procesar_texto(texto, usuario)

        elif msg_type == "audio":
            audio_id = msg.get("audio", {}).get("id", "")
            audio_url = await _obtener_media_url(audio_id)
            if not audio_url:
                respuesta = formatter.error("No pude acceder al audio. Intentá tipear el mensaje.")
            else:
                resultado = await whisper.transcribir_audio(audio_url, os.getenv("WHATSAPP_TOKEN", ""))
                if not resultado.get("texto"):
                    respuesta = formatter.advertencia(
                        "No pude entender el audio. ¿Podés tipear el mensaje?"
                    )
                else:
                    transcripcion = resultado["texto"]
                    await enviar_mensaje(telefono, f"🎤 Escuché: _{transcripcion}_")
                    respuesta = await procesar_texto(transcripcion, usuario)

        elif msg_type == "image":
            image_id = msg.get("image", {}).get("id", "")
            caption = msg.get("image", {}).get("caption", "")
            image_url = await _obtener_media_url(image_id)
            if not image_url:
                respuesta = formatter.error("No pude acceder a la imagen.")
            else:
                datos_imagen = await vision.analizar_imagen_url(image_url, os.getenv("WHATSAPP_TOKEN", ""))
                respuesta = await _procesar_datos_imagen(datos_imagen, caption, usuario)

        else:
            respuesta = formatter.advertencia(
                f"Tipo de mensaje no soportado: {msg_type}.\n"
                "Podés enviar texto, audio o imágenes."
            )

        await enviar_mensaje(telefono, respuesta)

    except Exception as e:
        logger.error(f"Error procesando mensaje de {telefono}: {e}", exc_info=True)
        await enviar_mensaje(telefono, formatter.error(
            "Ocurrió un error procesando tu mensaje. Intentá de nuevo."
        ))


async def _procesar_datos_imagen(datos: dict, caption: str, usuario: dict) -> str:
    """Procesa los datos extraídos de una imagen."""
    tipo_doc = datos.get("tipo_documento", "otro")
    confianza = datos.get("confianza", 0)

    if confianza < 0.5:
        return formatter.advertencia(
            "La imagen no es muy clara. ¿Podés enviar una foto más nítida o tipear los datos?"
        )

    if tipo_doc == "guia_traslado":
        caravanas = datos.get("caravanas", [])
        cantidad = datos.get("cantidad_animales", len(caravanas))
        categoria = datos.get("categoria", "sin especificar")
        fecha = datos.get("fecha", "sin fecha")

        resumen = (
            f"⚠️ *Guía de traslado detectada*\n"
            f"  Fecha: {fecha}\n"
            f"  Categoría: {categoria}\n"
            f"  Cantidad: {cantidad}\n"
            f"  Caravanas extraídas: {len(caravanas)}\n"
        )
        if caravanas:
            resumen += f"  Primeras 5: {', '.join(caravanas[:5])}\n"

        resumen += "\n¿Confirmás el ingreso? Respondé *sí* para guardar o *no* para cancelar."
        return resumen

    elif tipo_doc in ("factura", "remito"):
        total = datos.get("total")
        proveedor = datos.get("proveedor", "?")
        concepto = datos.get("concepto") or caption or "sin concepto"
        fecha = datos.get("fecha", "sin fecha")

        return (
            f"⚠️ *Documento detectado*\n"
            f"  Tipo: {tipo_doc}\n"
            f"  Proveedor: {proveedor}\n"
            f"  Concepto: {concepto}\n"
            f"  Monto: {f'$ {total:,.0f}' if total else '?'}\n"
            f"  Fecha: {fecha}\n\n"
            f"¿Registramos como egreso? Respondé *sí* para guardar o *no* para cancelar."
        )

    return formatter.advertencia(
        "No pude identificar el tipo de documento. "
        "¿Es una guía de traslado, factura o remito? Indicámelo."
    )


async def _obtener_media_url(media_id: str) -> str | None:
    """Obtiene la URL de descarga de un media de WhatsApp."""
    token = os.getenv("WHATSAPP_TOKEN", "")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{WHATSAPP_API_URL}/{media_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code == 200:
            return resp.json().get("url")
    return None


async def enviar_mensaje(telefono: str, texto: str):
    """Envía un mensaje de WhatsApp al número indicado."""
    token = os.getenv("WHATSAPP_TOKEN", "")
    phone_id = os.getenv("WHATSAPP_PHONE_ID", "")

    if not token or not phone_id:
        logger.warning("WHATSAPP_TOKEN o WHATSAPP_PHONE_ID no configurados.")
        return

    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "text",
        "text": {"body": texto},
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{WHATSAPP_API_URL}/{phone_id}/messages",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if resp.status_code != 200:
            logger.error(f"Error enviando mensaje a {telefono}: {resp.text}")
