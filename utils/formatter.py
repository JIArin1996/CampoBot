"""Formatea respuestas para WhatsApp (texto plano con emojis)."""

from datetime import date, datetime


def confirmacion(mensaje: str) -> str:
    return f"✅ {mensaje}"


def error(mensaje: str) -> str:
    return f"❌ {mensaje}"


def advertencia(mensaje: str) -> str:
    return f"⚠️ {mensaje}"


def lista(titulo: str, items: list[str]) -> str:
    if not items:
        return f"📋 {titulo}\n_(sin registros)_"
    lineas = "\n".join(f"  • {item}" for item in items)
    return f"📋 *{titulo}*\n{lineas}"


def reporte(titulo: str, datos: dict) -> str:
    lineas = [f"📊 *{titulo}*"]
    for clave, valor in datos.items():
        lineas.append(f"  {clave}: {valor}")
    return "\n".join(lineas)


def lluvia_confirmacion(fecha: date, mm: float, acum_mes: float, acum_anio: float) -> str:
    return (
        f"🌧 *Lluvia registrada*\n"
        f"  Fecha: {_fecha(fecha)}\n"
        f"  Registrado: *{mm} mm*\n"
        f"  Acumulado del mes: {acum_mes} mm\n"
        f"  Acumulado del año: {acum_anio} mm"
    )


def hacienda_lote_confirmacion(nombre: str, categoria: str, potrero: str, cantidad: int) -> str:
    return (
        f"🐄 *Lote registrado*\n"
        f"  Lote: {nombre}\n"
        f"  Categoría: {categoria}\n"
        f"  Potrero: {potrero}\n"
        f"  Cabezas: {cantidad}"
    )


def sanidad_confirmacion(tipo: str, producto: str, lote: str, fecha: str) -> str:
    return (
        f"💊 *Evento sanitario registrado*\n"
        f"  Tipo: {tipo}\n"
        f"  Producto: {producto}\n"
        f"  Lote/Potrero: {lote}\n"
        f"  Fecha: {fecha}"
    )


def economia_confirmacion(tipo: str, concepto: str, monto: float, fecha: str) -> str:
    emoji = "💰" if tipo == "ingreso" else "💸"
    return (
        f"{emoji} *Movimiento económico registrado*\n"
        f"  Tipo: {tipo.upper()}\n"
        f"  Concepto: {concepto}\n"
        f"  Monto: $ {monto:,.0f}\n"
        f"  Fecha: {fecha}"
    )


def menu_ayuda(rol: str) -> str:
    base = (
        "📋 *CampoBot — Comandos disponibles*\n\n"
        "🌧 *Lluvias*\n"
        "  • \"Llovió 34mm\" / \"34mm hoy\" / \"ayer 12mm\"\n"
        "  • \"¿Cuánto llovió en marzo?\"\n"
        "  • \"acumulado anual\"\n\n"
        "🐄 *Hacienda*\n"
        "  • \"Ingresaron 50 vaquillonas al potrero 3\"\n"
        "  • \"¿Qué hay en el potrero 2?\"\n"
        "  • \"Vendimos el lote VAQ-2025-01\"\n\n"
        "💊 *Sanidad*\n"
        "  • \"Dosificamos el lote 1 con Ivomec\"\n"
        "  • \"Vacuna aftosa al potrero 3 el viernes\"\n"
        "  • \"¿Qué sanidades hay programadas este mes?\"\n\n"
    )
    if rol in ("admin", "asesor"):
        base += (
            "💰 *Economía*\n"
            "  • \"Egreso $5000 combustible hoy\"\n"
            "  • \"Ingreso $50000 venta hacienda\"\n"
            "  • \"resumen del mes\"\n\n"
        )
    if rol == "admin":
        base += (
            "👤 *Usuarios*\n"
            "  • \"Agregar usuario +59891234567 operario\"\n\n"
        )
    base += (
        "ℹ️ *Otros*\n"
        "  • \"cancelar\" — cancela la operación actual\n"
        "  • \"deshacer\" — revierte el último registro\n"
        "  • \"ayuda [módulo]\" — ayuda específica"
    )
    return base


def _fecha(d) -> str:
    if isinstance(d, (date, datetime)):
        return d.strftime("%d/%m/%Y")
    return str(d)
