"""Módulo de agricultura: chacras y cultivos (RF-09)."""

from datetime import date
from db import supabase_client as db
from utils import formatter


async def registrar_chacra(datos: dict, usuario_id: str) -> str:
    chacra = {
        "nombre": datos.get("nombre", "Chacra sin nombre"),
        "superficie_has": datos.get("superficie_has", 0),
        "cultivo": datos.get("cultivo", ""),
        "variedad": datos.get("variedad"),
        "fecha_siembra": datos.get("fecha_siembra"),
        "estado": "planificado",
    }
    await db.insertar("chacras", chacra)
    await db.registrar_auditoria(usuario_id, f"Alta de chacra {chacra['nombre']}", "chacras", chacra)
    return formatter.confirmacion(
        f"Chacra *{chacra['nombre']}* registrada.\n"
        f"  Cultivo: {chacra['cultivo']}\n"
        f"  Superficie: {chacra['superficie_has']} has"
    )


async def consultar_chacras() -> str:
    chacras = await db.consultar("chacras")
    if not chacras:
        return formatter.lista("Chacras", [])

    lineas = ["🌱 *Estado de chacras*"]
    for c in chacras:
        dias = _dias_desde_siembra(c.get("fecha_siembra"))
        lineas.append(
            f"  • *{c['nombre']}* — {c['cultivo']} ({c['estado']})"
            + (f", {dias} días desde siembra" if dias else "")
        )
    return "\n".join(lineas)


def _dias_desde_siembra(fecha_str: str | None) -> int | None:
    if not fecha_str:
        return None
    try:
        desde = date.fromisoformat(str(fecha_str)[:10])
        return (date.today() - desde).days
    except Exception:
        return None
