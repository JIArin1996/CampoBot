"""Módulo de registro y consulta de precipitaciones (RF-08)."""

from datetime import date, datetime, timedelta
from db import supabase_client as db
from ai import extractor
from utils import formatter


async def registrar_lluvia(mensaje: str, usuario_id: str) -> str:
    """Extrae mm y fecha del mensaje y guarda el registro."""
    datos = await extractor.extraer_datos_lluvia(mensaje)

    if not datos.get("mm"):
        return formatter.error("No pude entender la cantidad de lluvia. Ejemplo: \"Llovió 34mm\"")

    fecha_str = datos.get("fecha") or date.today().isoformat()
    mm = float(datos["mm"])
    observaciones = datos.get("observaciones")

    registro = {
        "fecha": fecha_str,
        "mm": mm,
        "observaciones": observaciones,
        "usuario_id": usuario_id,
    }

    await db.insertar("lluvias", registro)
    await db.registrar_auditoria(usuario_id, f"Registró lluvia {mm}mm el {fecha_str}", "lluvias", registro)

    # Calcular acumulados
    fecha = date.fromisoformat(fecha_str)
    acum_mes = await _acumulado_mes(fecha.year, fecha.month)
    acum_anio = await _acumulado_anio(fecha.year)

    return formatter.lluvia_confirmacion(fecha, mm, acum_mes, acum_anio)


async def consultar_lluvia(mensaje: str) -> str:
    """Responde consultas sobre acumulados de lluvia."""
    msg_lower = mensaje.lower()

    # Detectar si pide anual
    if "anual" in msg_lower or "año" in msg_lower or "anio" in msg_lower:
        anio = date.today().year
        acum = await _acumulado_anio(anio)
        return f"🌧 Acumulado anual {anio}: *{acum} mm*"

    # Detectar mes específico
    meses = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
        "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
        "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    }
    for nombre, num in meses.items():
        if nombre in msg_lower:
            anio = date.today().year
            acum = await _acumulado_mes(anio, num)
            registros = await _registros_mes(anio, num)
            detalle = "\n".join(
                f"  {r['fecha']}: {r['mm']} mm" for r in registros
            ) or "  (sin registros)"
            return f"🌧 *Lluvias de {nombre.capitalize()} {anio}*\n{detalle}\n\n  *Total: {acum} mm*"

    # Por defecto: mes actual
    hoy = date.today()
    acum_mes = await _acumulado_mes(hoy.year, hoy.month)
    acum_anio = await _acumulado_anio(hoy.year)
    return (
        f"🌧 *Resumen de lluvias*\n"
        f"  Mes actual: *{acum_mes} mm*\n"
        f"  Acumulado {hoy.year}: *{acum_anio} mm*"
    )


async def _acumulado_mes(anio: int, mes: int) -> float:
    client = db.get_client()
    inicio = f"{anio}-{mes:02d}-01"
    # Último día del mes
    if mes == 12:
        fin = f"{anio + 1}-01-01"
    else:
        fin = f"{anio}-{mes + 1:02d}-01"
    resp = client.table("lluvias").select("mm").gte("fecha", inicio).lt("fecha", fin).execute()
    return round(sum(r["mm"] for r in resp.data), 1)


async def _acumulado_anio(anio: int) -> float:
    client = db.get_client()
    resp = (
        client.table("lluvias")
        .select("mm")
        .gte("fecha", f"{anio}-01-01")
        .lt("fecha", f"{anio + 1}-01-01")
        .execute()
    )
    return round(sum(r["mm"] for r in resp.data), 1)


async def _registros_mes(anio: int, mes: int) -> list:
    client = db.get_client()
    inicio = f"{anio}-{mes:02d}-01"
    if mes == 12:
        fin = f"{anio + 1}-01-01"
    else:
        fin = f"{anio}-{mes + 1:02d}-01"
    resp = (
        client.table("lluvias")
        .select("fecha,mm")
        .gte("fecha", inicio)
        .lt("fecha", fin)
        .order("fecha")
        .execute()
    )
    return resp.data
