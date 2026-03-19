import asyncio
import os
import json
import httpx

# --- ANTHROPIC (activo) ---
import base64
import anthropic
# --- FIN ANTHROPIC ---

# --- GEMINI (descomentar para volver) ---
# from google import genai
# from google.genai import types
# --- FIN GEMINI ---

from dotenv import load_dotenv

load_dotenv()

# --- ANTHROPIC (activo) ---
_client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
# --- FIN ANTHROPIC ---

# --- GEMINI (descomentar para volver) ---
# _client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
# --- FIN GEMINI ---

PROMPT_IMAGEN = """Analiza esta imagen que puede ser una guía de traslado, factura, remito o foto de caravanas.
Extrae todos los datos relevantes y devuelve JSON con la siguiente estructura:

{
  "tipo_documento": "guia_traslado | factura | remito | caravana | otro",
  "caravanas": ["858000012345678"],
  "cantidad_animales": null,
  "categoria": null,
  "origen": null,
  "destino": null,
  "fecha": "YYYY-MM-DD",
  "proveedor": null,
  "total": null,
  "concepto": null,
  "confianza": 0.9
}

Si no podés leer algún campo, usa null. No inventes datos.
Para caravanas, extrae todos los números SNIG de 15 dígitos que veas (empiezan con 858)."""


def _limpiar_json(texto: str) -> str:
    """Elimina bloques de código markdown si el modelo los incluye."""
    if texto.startswith("```"):
        texto = texto.split("```")[1]
        if texto.startswith("json"):
            texto = texto[4:]
    return texto.strip()


async def analizar_imagen_url(image_url: str, token: str) -> dict:
    """Descarga imagen de WhatsApp y la analiza con Vision."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            image_url,
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        image_bytes = response.content
        media_type = response.headers.get("content-type", "image/jpeg")

    # --- ANTHROPIC (activo) ---
    image_data = base64.standard_b64encode(image_bytes).decode("utf-8")
    result = await _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {"type": "text", "text": PROMPT_IMAGEN},
                ],
            }
        ],
    )
    texto = result.content[0].text.strip()
    # --- FIN ANTHROPIC ---

    # --- GEMINI (descomentar para volver) ---
    # image_part = types.Part.from_bytes(data=image_bytes, mime_type=media_type)
    # result = await asyncio.wait_for(
    #     _client.aio.models.generate_content(
    #         model="gemini-2.5-flash",
    #         contents=[image_part, PROMPT_IMAGEN],
    #     ),
    #     timeout=20.0,
    # )
    # texto = result.text.strip()
    # --- FIN GEMINI ---

    return json.loads(_limpiar_json(texto))
