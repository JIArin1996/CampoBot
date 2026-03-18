"""Módulo de hacienda: lotes, potreros y movimientos de animales (RF-01 a RF-05)."""

import re
from datetime import date
from db import supabase_client as db
from ai import extractor
from utils import formatter


# --- Alta de lote (RF-01) ---

async def registrar_ingreso(mensaje: str, usuario_id: str) -> str:
    datos = await extractor.extraer_datos_hacienda(mensaje)

    if not datos.get("cantidad") or not datos.get("potrero"):
        return formatter.advertencia(
            "Para registrar un ingreso necesito saber:\n"
            "  • Cantidad de animales\n"
            "  • Categoría (vaquillona, novillo, etc.)\n"
            "  • Potrero de destino\n\n"
            "Ejemplo: \"Ingresaron 50 vaquillonas al potrero 3\""
        )

    # Buscar potrero
    potrero = await _buscar_potrero(datos["potrero"])
    if not potrero:
        potreros_disp = await _listar_potreros()
        return formatter.error(
            f"No encontré el potrero \"{datos['potrero']}\".\n"
            f"Potreros disponibles:\n{potreros_disp}"
        )

    # Generar nombre de lote
    categoria_corta = _categoria_codigo(datos.get("categoria", "otro"))
    anio = date.today().year
    nombre_lote = datos.get("nombre_lote") or f"{categoria_corta}-{anio}-{_siguiente_numero_lote(categoria_corta, anio)}"

    lote = {
        "nombre": nombre_lote,
        "categoria": datos.get("categoria", "sin categoría"),
        "potrero_id": potrero["id"],
        "fecha_ingreso": datos.get("fecha") or date.today().isoformat(),
        "origen": datos.get("origen") or "compra",
        "activo": True,
    }

    lote_creado = await db.insertar("lotes", lote)

    # Registrar movimiento
    await db.insertar("movimientos_animales", {
        "tipo": "ingreso",
        "potrero_destino_id": potrero["id"],
        "fecha": lote["fecha_ingreso"],
        "usuario_id": usuario_id,
        "observaciones": f"Ingreso de {datos['cantidad']} {lote['categoria']} — Lote {nombre_lote}",
    })

    # Actualizar estado del potrero
    await db.actualizar("potreros", {"id": potrero["id"]}, {"estado": "ocupado"})

    await db.registrar_auditoria(usuario_id, f"Ingresó lote {nombre_lote}", "lotes", lote)

    return formatter.hacienda_lote_confirmacion(
        nombre_lote,
        lote["categoria"],
        potrero["nombre"],
        datos["cantidad"],
    )


# --- Consulta de lote o potrero (RF-03) ---

async def consultar(mensaje: str) -> str:
    msg_lower = mensaje.lower()

    # Consulta por potrero específico
    for palabra in ["potrero", "campo"]:
        if palabra in msg_lower:
            # Extraer número o nombre del potrero
            match = re.search(r'potrero\s+(\w+)', msg_lower)
            if match:
                potrero = await _buscar_potrero(match.group(1))
                if potrero:
                    return await _resumen_potrero(potrero)

    # Listar todos los potreros
    potreros = await db.consultar("potreros")
    if not potreros:
        return formatter.lista("Potreros", [])

    lineas = []
    for p in potreros:
        lotes = await db.consultar("lotes", {"potrero_id": p["id"], "activo": True})
        estado_emoji = "🟢" if p["estado"] == "libre" else "🔴" if p["estado"] == "ocupado" else "🟡"
        lineas.append(f"{estado_emoji} *{p['nombre']}* ({p.get('superficie_has', '?')} has) — {p['estado']}")
        for l in lotes:
            lineas.append(f"   └ {l['nombre']} ({l['categoria']})")

    return "🐄 *Estado de potreros*\n" + "\n".join(lineas)


async def _resumen_potrero(potrero: dict) -> str:
    lotes = await db.consultar("lotes", {"potrero_id": potrero["id"], "activo": True})
    if not lotes:
        return (
            f"🐄 *Potrero {potrero['nombre']}*\n"
            f"  Superficie: {potrero.get('superficie_has', '?')} has\n"
            f"  Estado: {potrero.get('estado', '?')}\n"
            f"  Sin lotes activos"
        )

    lineas = [
        f"🐄 *Potrero {potrero['nombre']}*",
        f"  Superficie: {potrero.get('superficie_has', '?')} has",
        f"  Estado: {potrero.get('estado', '?')}",
    ]
    for l in lotes:
        dias = _dias_desde(l.get("fecha_ingreso"))
        lineas.append(f"\n  📋 Lote: *{l['nombre']}*")
        lineas.append(f"     Categoría: {l['categoria']}")
        lineas.append(f"     Ingresó hace: {dias} días")
        lineas.append(f"     Origen: {l.get('origen', '?')}")

    return "\n".join(lineas)


# --- Baja de animales (RF-04) ---

async def registrar_baja(mensaje: str, usuario_id: str) -> str:
    msg_lower = mensaje.lower()

    tipo_baja = "venta"
    if "muri" in msg_lower or "muerte" in msg_lower or "muerto" in msg_lower:
        tipo_baja = "muerte"
    elif "transfer" in msg_lower or "traslad" in msg_lower:
        tipo_baja = "transferencia"

    # Buscar lote mencionado
    lote = await _buscar_lote_en_mensaje(mensaje)
    if not lote:
        return formatter.advertencia(
            "No encontré el lote. Indicá el nombre del lote o potrero.\n"
            "Ejemplo: \"Vendimos el lote VAQ-2025-01\""
        )

    await db.actualizar("lotes", {"id": lote["id"]}, {"activo": False})
    await db.insertar("movimientos_animales", {
        "tipo": tipo_baja,
        "potrero_origen_id": lote.get("potrero_id"),
        "fecha": date.today().isoformat(),
        "usuario_id": usuario_id,
        "observaciones": f"Baja por {tipo_baja} — Lote {lote['nombre']}",
    })

    # Liberar potrero si no quedan más lotes
    lotes_restantes = await db.consultar("lotes", {"potrero_id": lote["potrero_id"], "activo": True})
    if not lotes_restantes:
        await db.actualizar("potreros", {"id": lote["potrero_id"]}, {"estado": "libre"})

    await db.registrar_auditoria(usuario_id, f"Baja de lote {lote['nombre']} por {tipo_baja}", "lotes")

    return formatter.confirmacion(f"Lote *{lote['nombre']}* dado de baja por *{tipo_baja}*.")


# --- Transferencia entre potreros (RF-05) ---

async def transferir(mensaje: str, usuario_id: str) -> str:
    lote = await _buscar_lote_en_mensaje(mensaje)
    if not lote:
        return formatter.advertencia(
            "No encontré el lote a transferir. Indicá: lote de origen y potrero destino.\n"
            "Ejemplo: \"Mover lote VAQ-2025-01 al potrero 4\""
        )

    match = re.search(r'potrero\s+(\w+)', mensaje.lower())
    if not match:
        return formatter.advertencia("No pude identificar el potrero destino.")

    potrero_dest = await _buscar_potrero(match.group(1))
    if not potrero_dest:
        return formatter.error(f"No encontré el potrero \"{match.group(1)}\".")

    potrero_origen_id = lote.get("potrero_id")
    await db.actualizar("lotes", {"id": lote["id"]}, {"potrero_id": potrero_dest["id"]})
    await db.actualizar("potreros", {"id": potrero_dest["id"]}, {"estado": "ocupado"})
    await db.insertar("movimientos_animales", {
        "tipo": "transferencia",
        "potrero_origen_id": potrero_origen_id,
        "potrero_destino_id": potrero_dest["id"],
        "fecha": date.today().isoformat(),
        "usuario_id": usuario_id,
        "observaciones": f"Transferencia lote {lote['nombre']}",
    })

    return formatter.confirmacion(
        f"Lote *{lote['nombre']}* transferido al potrero *{potrero_dest['nombre']}*."
    )


# --- Registro de caravanas SNIG (RF-02) ---

def validar_caravana(caravana: str) -> bool:
    """Valida formato SNIG: 15 dígitos, prefijo 858."""
    limpia = re.sub(r'\s+', '', caravana)
    return bool(re.match(r'^858\d{12}$', limpia))


async def registrar_caravanas(caravanas: list[str], lote_id: str, usuario_id: str) -> str:
    validas = [c for c in caravanas if validar_caravana(c)]
    invalidas = [c for c in caravanas if not validar_caravana(c)]

    duplicadas = []
    guardadas = 0

    for caravana in validas:
        existente = await db.consultar_uno("animales", {"caravana": caravana})
        if existente:
            duplicadas.append(caravana)
            continue
        await db.insertar("animales", {
            "caravana": caravana,
            "lote_id": lote_id,
            "estado": "activo",
            "fecha_ingreso_sistema": date.today().isoformat(),
        })
        guardadas += 1

    respuesta = [formatter.confirmacion(f"Se registraron *{guardadas}* caravanas.")]
    if invalidas:
        respuesta.append(formatter.advertencia(f"Caravanas con formato inválido: {', '.join(invalidas[:5])}"))
    if duplicadas:
        respuesta.append(formatter.advertencia(f"Ya existían en el sistema: {', '.join(duplicadas[:5])}"))

    return "\n".join(respuesta)


# --- Helpers ---

async def _buscar_potrero(nombre_o_numero: str) -> dict | None:
    client = db.get_client()
    # Búsqueda por nombre exacto o parcial
    resp = client.table("potreros").select("*").ilike("nombre", f"%{nombre_o_numero}%").execute()
    return resp.data[0] if resp.data else None


async def _buscar_lote_en_mensaje(mensaje: str) -> dict | None:
    client = db.get_client()
    # Buscar patrón tipo VAQ-2025-01
    match = re.search(r'\b([A-Z]{2,4}-\d{4}-\d{2,3})\b', mensaje.upper())
    if match:
        resp = client.table("lotes").select("*").eq("nombre", match.group(1)).execute()
        return resp.data[0] if resp.data else None
    return None


async def _listar_potreros() -> str:
    potreros = await db.consultar("potreros")
    return "\n".join(f"  • {p['nombre']}" for p in potreros) or "  (sin potreros registrados)"


def _categoria_codigo(categoria: str) -> str:
    mapa = {
        "vaquillona": "VAQ",
        "novillo": "NOV",
        "vaca": "VAC",
        "toro": "TOR",
        "ternero": "TER",
        "novillo gordo": "NOG",
    }
    return mapa.get(categoria.lower(), "LOT")


def _siguiente_numero_lote(codigo: str, anio: int) -> str:
    # Simplificado — en producción consultar el último número en BD
    import random
    return f"{random.randint(1, 99):02d}"


def _dias_desde(fecha_str: str | None) -> int:
    if not fecha_str:
        return 0
    try:
        desde = date.fromisoformat(str(fecha_str)[:10])
        return (date.today() - desde).days
    except Exception:
        return 0
