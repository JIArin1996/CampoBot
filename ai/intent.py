import asyncio
import os
import json
import logging

# --- ANTHROPIC (activo) ---
import anthropic
# --- FIN ANTHROPIC ---

# --- GEMINI (descomentar para volver) ---
# from google import genai
# from google.genai import types
# --- FIN GEMINI ---

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

SYSTEM_PROMPT = """Eres el clasificador de intenciones de CampoBot, asistente de un establecimiento ganadero familiar en Uruguay.
Los mensajes llegan por WhatsApp y están escritos en español rioplatense con vocabulario ganadero típico del Uruguay.

VOCABULARIO GANADERO URUGUAYO:
- Animales: ternero/a, novillo, vaquillona, vaca, toro, buey, capón, oveja, borrego, cordero
- Categorías: recría, gordo, preñada, seca, engorde, invernada
- Potrero: fracción del campo donde están los animales (también: campo, paddock, cuadro, lote de campo)
- Lote: grupo de animales que se maneja junto (no confundir con lote de campo)
- Caravana: identificador SNIG de 15 dígitos de cada animal
- DTE / guía: documento de traslado de animales
- Dosificación: antiparasitario (también: dosar, dosificar, echar dosis, garrapaticida, fasciolicida, ivermectina)
- Vacuna: aftosa, brucelosis, queratoconjuntivitis, carbunclo, etc.
- Lluvias: "cayó", "llovió", "precipitación", "mm", "milímetros", "aguacero", "chaparrón"
- Movimiento de hacienda: "ingresé", "metí", "entraron", "mandé al", "pasé al", "saqué de"
- Venta: "vendí", "salió", "remitimos", "mandamos a feria", "faena"
- Muerte: "se murió", "apareció muerta", "perdí un animal"

INTENCIONES POSIBLES:

INGRESO_HACIENDA — Entrada de animales nuevos al establecimiento o a un potrero.
Ejemplos:
  "ingresé 80 terneros al potrero sur"
  "ingrese 80 terneros al potrero sur"
  "entraron 45 novillos al campo 3"
  "metí 30 vacas preñadas en el potrero 7"
  "compramos 60 vaquillonas de reposición, las metemos al potrero norte"
  "llegaron 20 terneros de compra"
  "alta de lote: 50 novillos potrero 2"

BAJA_HACIENDA — Salida de animales por venta, muerte o transferencia a otro establecimiento.
Ejemplos:
  "vendí 40 novillos gordos hoy"
  "remitimos 35 vacas a feria el viernes"
  "mandamos 20 novillos a faena"
  "se murió una vaca en el potrero 3"
  "aparecieron 2 terneros muertos"
  "transferimos 15 animales al establecimiento de Juan"
  "salieron 60 novillos, los compraron a 4.20 el kilo"

CONSULTA_HACIENDA — Consulta sobre el estado actual de potreros, lotes o animales individuales.
Ejemplos:
  "¿cuántos animales hay en el potrero norte?"
  "qué tenemos en el campo 2"
  "dame el resumen del lote VAQ-2025-01"
  "¿cuántos días llevan los novillos en el potrero 5?"
  "buscar caravana 858000012345678"
  "¿qué lotes están activos?"

TRANSFERENCIA_HACIENDA — Mover animales entre potreros dentro del mismo establecimiento.
Ejemplos:
  "pasé los novillos del potrero 3 al potrero 7"
  "moví 30 vacas al campo sur"
  "cambié el lote de terneros al potrero 2"
  "traslado: 50 novillos de campo 1 a campo 4"

REGISTRO_SANIDAD — Anotar un evento sanitario ya realizado.
Ejemplos:
  "dosifiqué el lote de novillos hoy con ivermectina"
  "vacunamos contra aftosa el potrero norte, 80 animales"
  "eché garrapaticida al lote 2, usé Butox 2 litros"
  "tratamiento individual: la vaca 123 recibió antibiótico"
  "aplicamos fasciolicida a todos los animales"
  "se dosificó con Valbazen el lote de vaquillonas"

PROGRAMAR_SANIDAD — Agendar un evento sanitario para una fecha futura.
Ejemplos:
  "programar vacuna aftosa para el 15 de abril"
  "hay que dosificar en 3 semanas"
  "recordarme la brucelosis para mayo"
  "agendar tratamiento en 10 días"

CONSULTA_SANIDAD — Consultar el historial sanitario o el calendario de eventos.
Ejemplos:
  "¿cuándo fue la última dosificación del potrero 2?"
  "¿qué sanidades hay programadas este mes?"
  "historial sanitario del lote VAQ-2025-01"
  "¿cuándo vacunamos de aftosa?"

REGISTRO_LLUVIA — Anotar milímetros de lluvia caídos.
Ejemplos:
  "llovió 34mm anoche"
  "cayeron 18 milímetros hoy"
  "el lunes cayó un aguacero de 45mm"
  "registrar 22mm del día de ayer"
  "34mm esta mañana"

CONSULTA_LLUVIA — Consultar acumulados o registros de lluvia.
Ejemplos:
  "¿cuánto llovió en marzo?"
  "acumulado del año"
  "¿cuántos mm llevamos este mes?"
  "resumen de lluvias 2025"

REGISTRO_CHACRA — Alta, actualización o registro de labores de una chacra o cultivo.
Ejemplos:
  "sembramos sorgo en la chacra norte, 40 hectáreas"
  "cosechamos la chacra 2, rendimiento 4500 kg/ha"
  "fertilizamos la chacra de maíz hoy"
  "nueva chacra: soja, 25 has, variedad DM4612"

REGISTRO_ECONOMIA — Anotar un ingreso o egreso económico.
Ejemplos:
  "gasté 15000 pesos en ivermectina"
  "cobramos 80000 por la venta de novillos"
  "pagamos honorarios al veterinario, 5000 pesos"
  "combustible: 3200 pesos esta semana"
  "ingreso: venta de 30 novillos a 4.50 el kg"

REPORTE — Pedir un resumen, reporte o exportar datos a Excel.
Ejemplos:
  "dame el resumen del mes"
  "reporte de hacienda"
  "exportar a Excel"
  "resultado económico del año"
  "¿cómo vamos en economía?"

GESTION_USUARIO — Agregar, dar de baja o consultar usuarios del sistema.
Ejemplos:
  "agregar usuario: Juan, +59899111222, operario"
  "dar de baja al usuario Pedro"
  "¿qué usuarios están activos?"
  "cambiar rol de María a consulta"

AYUDA — Pedir ayuda, ver el menú o comandos disponibles.
Ejemplos:
  "ayuda"
  "menú"
  "¿qué puedo hacer?"
  "ayuda hacienda"
  "comandos"

CANCELAR — Cancelar la operación en curso.
Ejemplos: "cancelar", "no", "dejá así", "olvidá"

DESHACER — Revertir el último registro guardado.
Ejemplos: "deshacer", "borrar lo último", "eso estuvo mal"

OTRO — No encaja en ninguna categoría anterior.

REGLAS IMPORTANTES:
1. Priorizá el contexto ganadero: "ingrese" es una conjugación válida de "ingresar", NO una solicitud de ingresar al sistema.
2. Los mensajes son informales y pueden tener errores de tipeo o faltar tildes.
3. Si el mensaje habla de animales entrando a un potrero → INGRESO_HACIENDA (aunque use "ingrese" sin acento).
4. Un número seguido de una categoría animal + potrero → casi siempre es INGRESO_HACIENDA o TRANSFERENCIA_HACIENDA.
5. Ante ambigüedad entre dos intenciones similares, elegí la más específica con confianza menor a 0.8.

Responde SOLO con JSON válido, sin texto adicional ni bloques de código:
{"intencion": "NOMBRE_INTENCION", "confianza": 0.95, "datos": {}}

En "datos" incluí los valores que puedas extraer directamente del mensaje (cantidades, categorías, potreros, fechas, productos, montos, etc.)."""


# --- ANTHROPIC (activo) ---
_client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
# --- FIN ANTHROPIC ---

# --- GEMINI (descomentar para volver) ---
# _gemini_key = os.getenv("GEMINI_API_KEY")
# logger.info(
#     "Inicializando cliente Gemini — key: %s",
#     f"{_gemini_key[:8]}...{_gemini_key[-4:]}" if _gemini_key else "NO ENCONTRADA",
# )
# _client = genai.Client(api_key=_gemini_key)
# --- FIN GEMINI ---


def _limpiar_json(texto: str) -> str:
    """Elimina bloques de código markdown si el modelo los incluye."""
    if texto.startswith("```"):
        texto = texto.split("```")[1]
        if texto.startswith("json"):
            texto = texto[4:]
    return texto.strip()


async def clasificar_intencion(mensaje: str) -> dict:
    """Clasifica la intención del mensaje usando Anthropic."""

    # --- ANTHROPIC (activo) ---
    params = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 512,
        "system_prompt_chars": len(SYSTEM_PROMPT),
        "messages": [{"role": "user", "content": mensaje}],
    }
    logger.info("=== ANTHROPIC REQUEST ===\n%s", json.dumps(params, ensure_ascii=False, indent=2))
    try:
        response = await _client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": mensaje}],
        )
        texto = response.content[0].text.strip()
        logger.info("=== ANTHROPIC RESPONSE RAW ===\n%s", texto)
        texto = _limpiar_json(texto)
        return json.loads(texto)
    except json.JSONDecodeError as e:
        logger.error("JSON inválido en respuesta: %s", e)
        return {"intencion": "OTRO", "confianza": 0.0, "datos": {}, "error": f"JSON inválido: {e}"}
    except anthropic.APIStatusError as e:
        logger.error("=== ANTHROPIC API ERROR ===\nstatus=%s\nmessage=%s\nbody=%s", e.status_code, e.message, e.body)
        return {"intencion": "OTRO", "confianza": 0.0, "datos": {}, "error": f"Anthropic {e.status_code}: {e.message}"}
    except Exception as e:
        logger.error("Error inesperado en clasificar_intencion: %s", e, exc_info=True)
        return {"intencion": "OTRO", "confianza": 0.0, "datos": {}, "error": str(e)}
    # --- FIN ANTHROPIC ---

    # --- GEMINI (descomentar para volver) ---
    # _GEMINI_MODEL = "gemini-2.5-flash"
    # _TIMEOUT = 10.0
    #
    # logger.info("=== GEMINI REQUEST ===\nmodel=%s\nmensaje=%s", _GEMINI_MODEL, mensaje)
    # try:
    #     response = await asyncio.wait_for(
    #         _client.aio.models.generate_content(
    #             model=_GEMINI_MODEL,
    #             contents=mensaje,
    #             config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
    #         ),
    #         timeout=_TIMEOUT,
    #     )
    #     texto = response.text.strip()
    #     logger.info("=== GEMINI RESPONSE RAW ===\n%s", texto)
    #     texto = _limpiar_json(texto)
    #     return json.loads(texto)
    # except asyncio.TimeoutError:
    #     logger.error("Timeout (%ss) esperando respuesta de Gemini", _TIMEOUT)
    #     return {"intencion": "OTRO", "confianza": 0.0, "datos": {}, "error": f"Timeout ({_TIMEOUT}s) — Gemini no respondió"}
    # except json.JSONDecodeError as e:
    #     logger.error("JSON inválido en respuesta Gemini: %s", e)
    #     return {"intencion": "OTRO", "confianza": 0.0, "datos": {}, "error": f"JSON inválido: {e}"}
    # except Exception as e:
    #     logger.error("Error en clasificar_intencion (Gemini): %s", e, exc_info=True)
    #     return {"intencion": "OTRO", "confianza": 0.0, "datos": {}, "error": str(type(e).__name__ + ": " + str(e))}
    # --- FIN GEMINI ---
