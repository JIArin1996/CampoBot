"""Scheduler de alertas sanitarias automáticas (RF-07)."""

import os
import logging
from datetime import date, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from db import supabase_client as db

logger = logging.getLogger(__name__)
_scheduler = AsyncIOScheduler()


def iniciar_scheduler(send_whatsapp_func):
    """Inicia el scheduler de alertas. Requiere la función de envío de WhatsApp."""

    async def verificar_alertas():
        dias_antes = int(os.getenv("ALERT_DAYS_BEFORE", 2))
        fecha_alerta = (date.today() + timedelta(days=dias_antes)).isoformat()

        client = db.get_client()
        resp = (
            client.table("sanidad_eventos")
            .select("*")
            .eq("fecha_programada", fecha_alerta)
            .eq("alerta_enviada", False)
            .execute()
        )

        admin_phone = os.getenv("ADMIN_PHONE", "")

        for evento in resp.data:
            mensaje = (
                f"🔔 *Recordatorio sanitario*\n"
                f"  En {dias_antes} días: {evento['tipo'].capitalize()} — {evento['producto']}\n"
                f"  Fecha programada: {evento['fecha_programada']}\n"
                f"  Lote: {evento['lote_id']}"
            )
            try:
                await send_whatsapp_func(admin_phone, mensaje)
                client.table("sanidad_eventos").update({"alerta_enviada": True}).eq("id", evento["id"]).execute()
                logger.info(f"Alerta enviada para evento {evento['id']}")
            except Exception as e:
                logger.error(f"Error enviando alerta: {e}")

    _scheduler.add_job(verificar_alertas, "cron", hour=8, minute=0, id="alertas_sanitarias")
    _scheduler.start()
    logger.info("Scheduler de alertas iniciado.")


def detener_scheduler():
    if _scheduler.running:
        _scheduler.shutdown()
