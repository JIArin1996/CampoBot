import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


async def extraer_datos_lluvia(mensaje: str) -> dict:
    """Extrae fecha y mm de lluvia de un mensaje en lenguaje natural."""
    from datetime import date
    prompt = f"""Extrae los datos de lluvia del siguiente mensaje.
La fecha de hoy es {date.today().isoformat()}.

Mensaje: "{mensaje}"

Responde SOLO con JSON:
{{"fecha": "YYYY-MM-DD", "mm": 12.5, "observaciones": null}}

Si no hay fecha explícita, asumí hoy. Si hay "anoche" o "ayer", usá la fecha de ayer.
Si no hay mm claro, usa null."""

    response = _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    texto = response.content[0].text.strip()
    if texto.startswith("```"):
        texto = texto.split("```")[1]
        if texto.startswith("json"):
            texto = texto[4:]
    return json.loads(texto)


async def extraer_datos_hacienda(mensaje: str) -> dict:
    """Extrae datos de movimiento de hacienda del mensaje."""
    from datetime import date
    prompt = f"""Extrae los datos de hacienda del siguiente mensaje.
La fecha de hoy es {date.today().isoformat()}.

Mensaje: "{mensaje}"

Responde SOLO con JSON:
{{
  "cantidad": 50,
  "categoria": "vaquillona",
  "potrero": "potrero 3",
  "origen": "compra",
  "nombre_lote": null,
  "peso_promedio": null,
  "precio_compra": null,
  "fecha": "YYYY-MM-DD",
  "observaciones": null
}}

Usa null para campos que no se mencionan. Para categoria usa: vaquillona, novillo, vaca, toro, ternero, novillo gordo."""

    response = _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    texto = response.content[0].text.strip()
    if texto.startswith("```"):
        texto = texto.split("```")[1]
        if texto.startswith("json"):
            texto = texto[4:]
    return json.loads(texto)


async def extraer_datos_sanidad(mensaje: str) -> dict:
    """Extrae datos de evento sanitario del mensaje."""
    from datetime import date
    prompt = f"""Extrae los datos del evento sanitario del siguiente mensaje.
La fecha de hoy es {date.today().isoformat()}.

Mensaje: "{mensaje}"

Responde SOLO con JSON:
{{
  "tipo": "dosificacion",
  "producto": "nombre del producto",
  "lote_o_potrero": "nombre del lote o potrero",
  "cantidad": null,
  "unidad": null,
  "costo_total": null,
  "fecha_realizada": "YYYY-MM-DD",
  "fecha_programada": null,
  "observaciones": null
}}

Para tipo usa: dosificacion, vacuna, tratamiento.
Usa null para campos no mencionados."""

    response = _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    texto = response.content[0].text.strip()
    if texto.startswith("```"):
        texto = texto.split("```")[1]
        if texto.startswith("json"):
            texto = texto[4:]
    return json.loads(texto)


async def extraer_datos_economia(mensaje: str) -> dict:
    """Extrae datos económicos del mensaje."""
    from datetime import date
    prompt = f"""Extrae los datos económicos del siguiente mensaje.
La fecha de hoy es {date.today().isoformat()}.

Mensaje: "{mensaje}"

Responde SOLO con JSON:
{{
  "tipo": "egreso",
  "categoria": "sanidad",
  "concepto": "descripción",
  "monto": 5000.0,
  "precio_usd": null,
  "fecha": "YYYY-MM-DD",
  "lote": null,
  "chacra": null
}}

Para tipo usa: ingreso, egreso.
Para categoria usa: venta_hacienda, sanidad, semilla, labor, combustible, otro.
Usa null para campos no mencionados."""

    response = _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    texto = response.content[0].text.strip()
    if texto.startswith("```"):
        texto = texto.split("```")[1]
        if texto.startswith("json"):
            texto = texto[4:]
    return json.loads(texto)
