"""Enrutador de intenciones — dirige cada mensaje al módulo correcto."""

from ai.intent import clasificar_intencion
from modules import lluvias, hacienda, sanidad, economia
from utils import formatter


# Roles que pueden ver información económica
ROLES_ECONOMIA = {"admin", "asesor"}
# Roles que solo pueden leer
ROLES_SOLO_LECTURA = {"consulta"}


async def procesar_texto(mensaje: str, usuario: dict) -> str:
    """Clasifica la intención del mensaje y llama al módulo correspondiente."""
    telefono = usuario.get("telefono", "")
    rol = usuario.get("rol", "consulta")
    usuario_id = usuario.get("id", telefono)

    resultado = await clasificar_intencion(mensaje)
    intencion = resultado.get("intencion", "OTRO")
    confianza = resultado.get("confianza", 0.0)

    # Si la confianza es muy baja, pedir aclaración
    if confianza < 0.4 and intencion != "AYUDA":
        return formatter.advertencia(
            "No entendí bien tu mensaje. ¿Podés ser más específico?\n"
            "Escribí *ayuda* para ver los comandos disponibles."
        )

    # Verificar permisos de escritura
    if rol in ROLES_SOLO_LECTURA and intencion not in {
        "CONSULTA_HACIENDA", "CONSULTA_LLUVIA", "CONSULTA_SANIDAD", "AYUDA", "OTRO"
    }:
        return formatter.error("No tenés permisos para registrar datos. Solo podés consultar.")

    # Comandos generales
    if intencion == "AYUDA" or mensaje.lower() in ("ayuda", "menú", "menu"):
        return formatter.menu_ayuda(rol)

    if intencion == "CANCELAR" or mensaje.lower() == "cancelar":
        return formatter.confirmacion("Operación cancelada. ¿En qué más puedo ayudarte?")

    # Módulo lluvias
    if intencion == "REGISTRO_LLUVIA":
        return await lluvias.registrar_lluvia(mensaje, usuario_id)

    if intencion == "CONSULTA_LLUVIA":
        return await lluvias.consultar_lluvia(mensaje)

    # Módulo hacienda
    if intencion == "INGRESO_HACIENDA":
        if rol in ROLES_SOLO_LECTURA:
            return formatter.error("No tenés permisos para registrar hacienda.")
        return await hacienda.registrar_ingreso(mensaje, usuario_id)

    if intencion == "BAJA_HACIENDA":
        if rol in ROLES_SOLO_LECTURA:
            return formatter.error("No tenés permisos para dar de baja hacienda.")
        return await hacienda.registrar_baja(mensaje, usuario_id)

    if intencion == "CONSULTA_HACIENDA":
        return await hacienda.consultar(mensaje)

    if intencion == "TRANSFERENCIA_HACIENDA":
        if rol in ROLES_SOLO_LECTURA:
            return formatter.error("No tenés permisos para transferir hacienda.")
        return await hacienda.transferir(mensaje, usuario_id)

    # Módulo sanidad
    if intencion == "REGISTRO_SANIDAD":
        if rol in ROLES_SOLO_LECTURA:
            return formatter.error("No tenés permisos para registrar sanidad.")
        return await sanidad.registrar_evento(mensaje, usuario_id)

    if intencion == "PROGRAMAR_SANIDAD":
        if rol in ROLES_SOLO_LECTURA:
            return formatter.error("No tenés permisos para programar sanidad.")
        return await sanidad.programar_evento(mensaje, usuario_id)

    if intencion == "CONSULTA_SANIDAD":
        return await sanidad.consultar_calendario(mensaje)

    # Módulo economía (solo admin y asesor)
    if intencion == "REGISTRO_ECONOMIA":
        if rol not in ROLES_ECONOMIA:
            return formatter.error("No tenés permisos para acceder a información económica.")
        return await economia.registrar_movimiento(mensaje, usuario_id)

    if intencion == "REPORTE":
        if rol not in ROLES_ECONOMIA:
            return formatter.error("No tenés permisos para ver reportes económicos.")
        return await economia.resumen_mes()

    # No reconocido
    return formatter.advertencia(
        "No entendí tu mensaje. Escribí *ayuda* para ver los comandos disponibles.\n\n"
        "Ejemplos:\n"
        "  • \"Llovió 34mm\"\n"
        "  • \"Ingresaron 50 vaquillonas al potrero 3\"\n"
        "  • \"Dosificamos el lote 1 con Ivomec\""
    )
