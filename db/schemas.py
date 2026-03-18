from pydantic import BaseModel
from typing import Optional, Literal
from datetime import date, datetime
import uuid


# --- Usuarios ---

class Usuario(BaseModel):
    id: Optional[str] = None
    telefono: str
    nombre: str
    rol: Literal["admin", "operario", "consulta", "asesor"]
    activo: bool = True
    created_at: Optional[datetime] = None


# --- Potreros ---

class Potrero(BaseModel):
    id: Optional[str] = None
    nombre: str
    superficie_has: float
    estado: Literal["ocupado", "libre", "descanso"] = "libre"
    created_at: Optional[datetime] = None


# --- Lotes ---

class Lote(BaseModel):
    id: Optional[str] = None
    nombre: str
    categoria: str
    potrero_id: str
    fecha_ingreso: date
    origen: Literal["compra", "propio", "nacimiento"]
    activo: bool = True
    created_at: Optional[datetime] = None


# --- Animales (trazabilidad individual) ---

class Animal(BaseModel):
    caravana: str  # PK — 15 dígitos SNIG
    lote_id: str
    estado: Literal["activo", "vendido", "muerto", "transferido"] = "activo"
    fecha_ingreso_sistema: Optional[date] = None
    fecha_baja: Optional[date] = None
    motivo_baja: Optional[str] = None
    created_at: Optional[datetime] = None


# --- Movimientos de animales ---

class MovimientoAnimal(BaseModel):
    id: Optional[str] = None
    caravana: str
    tipo: Literal["ingreso", "venta", "muerte", "transferencia"]
    potrero_origen_id: Optional[str] = None
    potrero_destino_id: Optional[str] = None
    fecha: date
    usuario_id: str
    observaciones: Optional[str] = None


# --- Sanidad ---

class SanidadEvento(BaseModel):
    id: Optional[str] = None
    lote_id: str
    tipo: str  # dosificacion / vacuna / tratamiento
    producto: str
    cantidad: Optional[float] = None
    unidad: Optional[str] = None
    costo_total: Optional[float] = None
    fecha_realizada: Optional[date] = None
    fecha_programada: Optional[date] = None
    alerta_enviada: bool = False
    usuario_id: str


# --- Lluvias ---

class Lluvia(BaseModel):
    id: Optional[str] = None
    fecha: date
    mm: float
    observaciones: Optional[str] = None
    usuario_id: str


# --- Chacras ---

class Chacra(BaseModel):
    id: Optional[str] = None
    nombre: str
    superficie_has: float
    cultivo: str
    variedad: Optional[str] = None
    fecha_siembra: Optional[date] = None
    fecha_cosecha: Optional[date] = None
    rendimiento_kg_ha: Optional[float] = None
    estado: Literal["planificado", "sembrado", "cosechado"] = "planificado"


# --- Economía ---

class Economia(BaseModel):
    id: Optional[str] = None
    tipo: Literal["ingreso", "egreso"]
    categoria: str  # venta_hacienda / sanidad / semilla / labor / combustible / otro
    concepto: str
    monto: float
    precio_usd: Optional[float] = None
    fecha: date
    lote_id: Optional[str] = None
    chacra_id: Optional[str] = None
    usuario_id: str


# --- Auditoría ---

class Auditoria(BaseModel):
    id: Optional[str] = None
    usuario_id: str
    accion: str
    tabla_afectada: str
    datos_json: Optional[dict] = None
    timestamp: Optional[datetime] = None
