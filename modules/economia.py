"""Módulo económico: ingresos, egresos y reportes (RF-10, RF-11)."""

from datetime import date
from db import supabase_client as db
from ai import extractor
from utils import formatter, excel_export


async def registrar_movimiento(mensaje: str, usuario_id: str) -> str:
    datos = await extractor.extraer_datos_economia(mensaje)

    if not datos.get("concepto") or not datos.get("monto"):
        return formatter.advertencia(
            "Para registrar un movimiento económico necesito:\n"
            "  • Tipo (ingreso/egreso)\n"
            "  • Concepto o descripción\n"
            "  • Monto\n\n"
            "Ejemplo: \"Egreso $5000 combustible hoy\"\n"
            "Ejemplo: \"Ingreso $80000 venta hacienda\""
        )

    # Resolver lote si se mencionó
    lote_id = None
    if datos.get("lote"):
        client = db.get_client()
        resp = client.table("lotes").select("id").ilike("nombre", f"%{datos['lote']}%").execute()
        if resp.data:
            lote_id = resp.data[0]["id"]

    movimiento = {
        "tipo": datos.get("tipo", "egreso"),
        "categoria": datos.get("categoria", "otro"),
        "concepto": datos["concepto"],
        "monto": float(datos["monto"]),
        "precio_usd": datos.get("precio_usd"),
        "fecha": datos.get("fecha") or date.today().isoformat(),
        "lote_id": lote_id,
        "chacra_id": None,
        "usuario_id": usuario_id,
    }

    await db.insertar("economia", movimiento)
    await db.registrar_auditoria(
        usuario_id,
        f"Registró {movimiento['tipo']} $ {movimiento['monto']}",
        "economia",
        movimiento,
    )

    return formatter.economia_confirmacion(
        movimiento["tipo"],
        movimiento["concepto"],
        movimiento["monto"],
        movimiento["fecha"],
    )


async def resumen_mes(anio: int = None, mes: int = None) -> str:
    hoy = date.today()
    anio = anio or hoy.year
    mes = mes or hoy.month

    inicio = f"{anio}-{mes:02d}-01"
    if mes == 12:
        fin = f"{anio + 1}-01-01"
    else:
        fin = f"{anio}-{mes + 1:02d}-01"

    client = db.get_client()
    resp = (
        client.table("economia")
        .select("tipo,monto,categoria")
        .gte("fecha", inicio)
        .lt("fecha", fin)
        .execute()
    )

    ingresos = sum(r["monto"] for r in resp.data if r["tipo"] == "ingreso")
    egresos = sum(r["monto"] for r in resp.data if r["tipo"] == "egreso")
    resultado = ingresos - egresos

    emoji_resultado = "📈" if resultado >= 0 else "📉"
    meses_nombres = [
        "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]

    return (
        f"💰 *Resumen económico — {meses_nombres[mes]} {anio}*\n\n"
        f"  Ingresos:  $ {ingresos:>12,.0f}\n"
        f"  Egresos:   $ {egresos:>12,.0f}\n"
        f"  ─────────────────────\n"
        f"  {emoji_resultado} Resultado: $ {resultado:>12,.0f}"
    )


async def exportar_excel(anio: int = None, mes: int = None) -> bytes:
    """Genera Excel con movimientos del período."""
    hoy = date.today()
    anio = anio or hoy.year

    if mes:
        inicio = f"{anio}-{mes:02d}-01"
        if mes == 12:
            fin = f"{anio + 1}-01-01"
        else:
            fin = f"{anio}-{mes + 1:02d}-01"
        periodo = f"{anio}-{mes:02d}"
    else:
        inicio = f"{anio}-01-01"
        fin = f"{anio + 1}-01-01"
        periodo = str(anio)

    client = db.get_client()
    resp = (
        client.table("economia")
        .select("*")
        .gte("fecha", inicio)
        .lt("fecha", fin)
        .order("fecha")
        .execute()
    )

    return excel_export.reporte_economia(resp.data, periodo)
