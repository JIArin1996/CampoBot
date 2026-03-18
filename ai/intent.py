import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """Eres el asistente de administración de un establecimiento ganadero en Uruguay.
Tu tarea es clasificar el mensaje del usuario e identificar su intención.

Intenciones posibles:
 - INGRESO_HACIENDA: registrar entrada de animales
 - BAJA_HACIENDA: registrar venta, muerte o transferencia
 - CONSULTA_HACIENDA: preguntar por lotes, potreros o caravanas
 - TRANSFERENCIA_HACIENDA: mover animales entre potreros
 - REGISTRO_SANIDAD: anotar evento sanitario (dosificación, vacuna, tratamiento)
 - PROGRAMAR_SANIDAD: agendar evento sanitario futuro
 - CONSULTA_SANIDAD: consultar historial o calendario sanitario
 - REGISTRO_LLUVIA: registrar mm de lluvia
 - CONSULTA_LLUVIA: pedir acumulados de lluvia
 - REGISTRO_CHACRA: alta o actualización de chacra/cultivo
 - REGISTRO_ECONOMIA: anotar ingreso o egreso económico
 - REPORTE: pedir resumen, reporte o exportar datos
 - GESTION_USUARIO: alta/baja/consulta de usuarios
 - AYUDA: pedir ayuda o menú de comandos
 - CANCELAR: cancelar operación en curso
 - DESHACER: revertir último registro
 - OTRO: no encaja en ninguna categoría anterior

Responde SOLO con JSON válido, sin texto adicional:
{"intencion": "...", "confianza": 0.95, "datos": {...}}

En "datos" incluí los valores que puedas extraer del mensaje (fechas, números, nombres, etc.)."""


async def clasificar_intencion(mensaje: str) -> dict:
    """Clasifica la intención del mensaje usando Claude."""
    try:
        response = _client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": mensaje}],
        )
        texto = response.content[0].text.strip()
        # Limpiar posibles bloques de código markdown
        if texto.startswith("```"):
            texto = texto.split("```")[1]
            if texto.startswith("json"):
                texto = texto[4:]
        return json.loads(texto)
    except (json.JSONDecodeError, Exception) as e:
        return {"intencion": "OTRO", "confianza": 0.0, "datos": {}, "error": str(e)}
