import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL y SUPABASE_KEY deben estar configuradas en .env")
        _client = create_client(url, key)
    return _client


async def insertar(tabla: str, datos: dict) -> dict:
    client = get_client()
    response = client.table(tabla).insert(datos).execute()
    return response.data[0] if response.data else {}


async def actualizar(tabla: str, filtros: dict, datos: dict) -> list:
    client = get_client()
    query = client.table(tabla).update(datos)
    for campo, valor in filtros.items():
        query = query.eq(campo, valor)
    response = query.execute()
    return response.data


async def consultar(tabla: str, filtros: dict = None, select: str = "*") -> list:
    client = get_client()
    query = client.table(tabla).select(select)
    if filtros:
        for campo, valor in filtros.items():
            query = query.eq(campo, valor)
    response = query.execute()
    return response.data


async def consultar_uno(tabla: str, filtros: dict, select: str = "*") -> dict | None:
    resultados = await consultar(tabla, filtros, select)
    return resultados[0] if resultados else None


async def registrar_auditoria(usuario_id: str, accion: str, tabla: str, datos: dict = None):
    from datetime import datetime, timezone
    await insertar("auditoria", {
        "usuario_id": usuario_id,
        "accion": accion,
        "tabla_afectada": tabla,
        "datos_json": datos,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
