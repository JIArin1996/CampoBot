-- CampoBot — Schema de base de datos para Supabase (PostgreSQL)
-- Ejecutar en el SQL Editor de Supabase

-- Habilitar extensión UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- USUARIOS
-- ============================================================
CREATE TABLE IF NOT EXISTS usuarios (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    telefono    VARCHAR(20) UNIQUE NOT NULL,
    nombre      VARCHAR(100) NOT NULL,
    rol         VARCHAR(20) NOT NULL CHECK (rol IN ('admin', 'operario', 'consulta', 'asesor')),
    activo      BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- POTREROS
-- ============================================================
CREATE TABLE IF NOT EXISTS potreros (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre          VARCHAR(100) NOT NULL,
    superficie_has  DECIMAL(10, 2),
    estado          VARCHAR(20) DEFAULT 'libre' CHECK (estado IN ('ocupado', 'libre', 'descanso')),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- LOTES
-- ============================================================
CREATE TABLE IF NOT EXISTS lotes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre          VARCHAR(100) NOT NULL,
    categoria       VARCHAR(100) NOT NULL,
    potrero_id      UUID REFERENCES potreros(id),
    fecha_ingreso   DATE NOT NULL,
    origen          VARCHAR(20) DEFAULT 'compra' CHECK (origen IN ('compra', 'propio', 'nacimiento')),
    activo          BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- ANIMALES (trazabilidad individual SNIG)
-- ============================================================
CREATE TABLE IF NOT EXISTS animales (
    caravana                VARCHAR(15) PRIMARY KEY,  -- 15 dígitos SNIG
    lote_id                 UUID REFERENCES lotes(id),
    estado                  VARCHAR(20) DEFAULT 'activo' CHECK (estado IN ('activo', 'vendido', 'muerto', 'transferido')),
    fecha_ingreso_sistema   DATE,
    fecha_baja              DATE,
    motivo_baja             VARCHAR(50),
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- MOVIMIENTOS DE ANIMALES
-- ============================================================
CREATE TABLE IF NOT EXISTS movimientos_animales (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    caravana            VARCHAR(15) REFERENCES animales(caravana),
    tipo                VARCHAR(20) NOT NULL CHECK (tipo IN ('ingreso', 'venta', 'muerte', 'transferencia')),
    potrero_origen_id   UUID REFERENCES potreros(id),
    potrero_destino_id  UUID REFERENCES potreros(id),
    fecha               DATE NOT NULL,
    usuario_id          UUID REFERENCES usuarios(id),
    observaciones       TEXT
);

-- ============================================================
-- SANIDAD EVENTOS
-- ============================================================
CREATE TABLE IF NOT EXISTS sanidad_eventos (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lote_id             UUID REFERENCES lotes(id),
    tipo                VARCHAR(50) NOT NULL,
    producto            VARCHAR(200) NOT NULL,
    cantidad            DECIMAL(10, 3),
    unidad              VARCHAR(20),
    costo_total         DECIMAL(12, 2),
    fecha_realizada     DATE,
    fecha_programada    DATE,
    alerta_enviada      BOOLEAN DEFAULT FALSE,
    usuario_id          UUID REFERENCES usuarios(id)
);

-- ============================================================
-- LLUVIAS
-- ============================================================
CREATE TABLE IF NOT EXISTS lluvias (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fecha           DATE NOT NULL,
    mm              DECIMAL(6, 1) NOT NULL,
    observaciones   VARCHAR(500),
    usuario_id      UUID REFERENCES usuarios(id)
);

-- Índice para consultas por fecha
CREATE INDEX IF NOT EXISTS idx_lluvias_fecha ON lluvias(fecha);

-- ============================================================
-- CHACRAS
-- ============================================================
CREATE TABLE IF NOT EXISTS chacras (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre              VARCHAR(100) NOT NULL,
    superficie_has      DECIMAL(10, 2),
    cultivo             VARCHAR(100),
    variedad            VARCHAR(100),
    fecha_siembra       DATE,
    fecha_cosecha       DATE,
    rendimiento_kg_ha   DECIMAL(10, 2),
    estado              VARCHAR(20) DEFAULT 'planificado' CHECK (estado IN ('planificado', 'sembrado', 'cosechado'))
);

-- ============================================================
-- ECONOMÍA
-- ============================================================
CREATE TABLE IF NOT EXISTS economia (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tipo        VARCHAR(10) NOT NULL CHECK (tipo IN ('ingreso', 'egreso')),
    categoria   VARCHAR(50) NOT NULL,
    concepto    VARCHAR(500) NOT NULL,
    monto       DECIMAL(14, 2) NOT NULL,
    precio_usd  DECIMAL(14, 2),
    fecha       DATE NOT NULL,
    lote_id     UUID REFERENCES lotes(id),
    chacra_id   UUID REFERENCES chacras(id),
    usuario_id  UUID REFERENCES usuarios(id)
);

-- Índice para consultas por fecha
CREATE INDEX IF NOT EXISTS idx_economia_fecha ON economia(fecha);

-- ============================================================
-- AUDITORÍA
-- ============================================================
CREATE TABLE IF NOT EXISTS auditoria (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id      UUID REFERENCES usuarios(id),
    accion          VARCHAR(500) NOT NULL,
    tabla_afectada  VARCHAR(100),
    datos_json      JSONB,
    timestamp       TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- ROW LEVEL SECURITY (opcional — recomendado en producción)
-- ============================================================
-- ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE lluvias ENABLE ROW LEVEL SECURITY;
-- (configurar políticas según necesidad)

-- ============================================================
-- DATOS INICIALES DE EJEMPLO
-- ============================================================
-- Insertar administrador inicial (reemplazar teléfono)
INSERT INTO usuarios (telefono, nombre, rol)
VALUES ('+59899999999', 'Administrador', 'admin')
ON CONFLICT (telefono) DO NOTHING;
