import os
import httpx
import tempfile
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Vocabulario ganadero para mejorar transcripción
PROMPT_GANADERO = (
    "Establecimiento ganadero Uruguay. Términos: potrero, caravana, SNIG, vaquillona, "
    "novillo, ternero, dosificación, vacuna aftosa, brucelosis, destete, recría, "
    "millímetros lluvia, hectáreas, lote, DTE, MGAP."
)


async def transcribir_audio(audio_url: str, token: str) -> dict:
    """Descarga audio de WhatsApp y lo transcribe con Whisper."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            audio_url,
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        audio_bytes = response.content

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as audio_file:
            result = await _client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="es",
                prompt=PROMPT_GANADERO,
            )
        return {"texto": result.text, "confianza": "ok"}
    except Exception as e:
        return {"texto": None, "error": str(e)}
    finally:
        os.unlink(tmp_path)
