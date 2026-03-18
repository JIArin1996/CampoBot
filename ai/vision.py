import os
import json
import base64
import httpx
import anthropic
from dotenv import load_dotenv

load_dotenv()

_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

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


async def analizar_imagen_url(image_url: str, token: str) -> dict:
    """Descarga imagen de WhatsApp y la analiza con Claude Vision."""
    # Descargar imagen desde la URL de Meta
    async with httpx.AsyncClient() as client:
        response = await client.get(
            image_url,
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        image_data = base64.standard_b64encode(response.content).decode("utf-8")
        media_type = response.headers.get("content-type", "image/jpeg")

    result = _client.messages.create(
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
    if texto.startswith("```"):
        texto = texto.split("```")[1]
        if texto.startswith("json"):
            texto = texto[4:]
    return json.loads(texto)
