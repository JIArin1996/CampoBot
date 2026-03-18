"""Módulo de sanidad animal: eventos, calendario y alertas (RF-06, RF-07)."""

from datetime import date
from db import supabase_client as db
from ai import extractor
from utils import formatter


async def registrar_evento(mensaje: str, usuario_id: str) -> str:
    datos = await extractor.extraer_datos_sanidad(mensaje)

    if not datos.get("producto") or not datos.get("lote_o_potrero"):
        return formatter.advertencia(
            "Para registrar sanidad necesito:\n"
            "  • Tipo de evento (dosificación, vacuna, tratamiento)\n"
            "  • Producto usado\n"
            "  • Lote o potrero\n\n"
            "Ejemplo: \"Dosificamos el lote VAQ-2025-01 con Ivomec 5 litros\""
        )

    # Buscar lote por nombre o potrero
    lote_id = await _resolver_lote(datos["lote_o_potrero"])
    if not lote_id:
        return formatter.error(
            f"No encontré el lote o potrero \"{datos['lote_o_potrero']}\"."
        )

    es_programado = bool(datos.get("fecha_programada")) and not datos.get("fecha_realizada")

    evento = {
        "lote_id": lote_id,
        "tipo": datos.get("tipo", "tratamiento"),
        "producto": datos["producto"],
        "cantidad": datos.get("cantidad"),
        "unidad": datos.get("unidad"),
        "costo_total": datos.get("costo_total"),
        "fecha_realizada": datos.get("fecha_realizada") or (None if es_programado else date.today().isoformat()),
        "fecha_programada": datos.get("fecha_programada"),
        "alerta_enviada": False,
        "usuario_id": usuario_id,
    }

    await db.insertar("sanidad_eventos", evento)
    await db.registrar_auditoria(
        usuario_id,
        f"Registró evento sanitario: {evento['tipo']} {evento['producto']}",
        "sanidad_eventos",
        evento,
    )

    if es_programado:
        return formatter.confirmacion(
            f"Evento sanitario *programado* para el {datos['fecha_programada']}.\n"
            f"  Producto: {datos['producto']}\n"
            f"  Recibirás un recordatorio 2 días antes. 🔔"
        )

    return formatter.sanidad_confirmacion(
        evento["tipo"],
        evento["producto"],
        datos["lote_o_potrero"],
        evento.get("fecha_realizada") or "hoy",
    )


async def programar_evento(mensaje: str, usuario_id: str) -> str:
    """Programa un evento sanitario futuro."""
    return await registrar_evento(mensaje, usuario_id)


async def consultar_calendario(mensaje: str) -> str:
    """Consulta eventos sanitarios programados."""
    msg_lower = mensaje.lower()
    hoy = date.today()

    if "mes" in msg_lower or "este mes" in msg_lower:
        inicio = f"{hoy.year}-{hoy.month:02d}-01"
        if hoy.month == 12:
            fin = f"{hoy.year + 1}-01-01"
        else:
            fin = f"{hoy.year}-{hoy.month + 1:02d}-01"
    else:
        # Próximos 30 días
        from datetime import timedelta
        inicio = hoy.isoformat()
        fin = (hoy + timedelta(days=30)).isoformat()

    client = db.get_client()
    resp = (
        client.table("sanidad_eventos")
        .select("*")
        .gte("fecha_programada", inicio)
        .lt("fecha_programada", fin)
        .order("fecha_programada")
        .execute()
    )

    if not resp.data:
        return "💊 No hay eventos sanitarios programados para este período."

    lineas = ["💊 *Calendario sanitario*"]
    for e in resp.data:
        lineas.append(
            f"  🔔 {e['fecha_programada']} — {e['tipo'].capitalize()}: {e['producto']} (lote {e['lote_id'][:8]}...)"
        )
    return "\n".join(lineas)


async def _resolver_lote(nombre: str) -> str | None:
    """Busca lote por nombre o por potrero."""
    client = db.get_client()
    # Intentar por nombre de lote
    resp = client.table("lotes").select("id").ilike("nombre", f"%{nombre}%").eq("activo", True).execute()
    if resp.data:
        return resp.data[0]["id"]
    # Intentar por potrero
    resp_pot = client.table("potreros").select("id").ilike("nombre", f"%{nombre}%").execute()
    if resp_pot.data:
        potrero_id = resp_pot.data[0]["id"]
        resp_lote = client.table("lotes").select("id").eq("potrero_id", potrero_id).eq("activo", True).execute()
        if resp_lote.data:
            return resp_lote.data[0]["id"]
    return None
