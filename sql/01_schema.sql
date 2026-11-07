-- ============================================================================
-- sql/01_schema.sql 
-- se encuentra los datos para los login y registrarse + la del modulo de creacion de clientes
-- ============================================================================
IF DB_ID('Taller') IS NULL CREATE DATABASE Taller;
GO
USE Taller;
GO

-- Configuración (el IVA lo lee la pantalla de ventas)
IF OBJECT_ID('Configuracion', 'U') IS NULL
BEGIN
    CREATE TABLE Configuracion (clave VARCHAR(30) PRIMARY KEY, valor VARCHAR(50) NOT NULL);
    INSERT INTO Configuracion VALUES ('IVA', '0.13');
END
GO

-- Usuarios y roles
-- pendiente = 1: la cuenta se registró sola desde el login y espera que un administrador la apruebe.
-- Solo puede iniciar sesión si activo = 1 (aprobar = activo 1 y pendiente 0).
IF OBJECT_ID('Usuarios', 'U') IS NULL
CREATE TABLE Usuarios (
    id_usuario     INT IDENTITY PRIMARY KEY,
    usuario        VARCHAR(30)  NOT NULL UNIQUE,
    nombre         VARCHAR(100) NOT NULL,
    password_hash  VARCHAR(100) NOT NULL,
    rol            VARCHAR(20)  NOT NULL,
    activo         BIT NOT NULL DEFAULT 1,
    pendiente      BIT NOT NULL DEFAULT 0,
    fecha_creacion DATETIME NOT NULL DEFAULT GETDATE(),
    CONSTRAINT CK_Usuarios_rol CHECK (rol IN ('Administrador', 'Vendedor', 'Mecanico', 'Bodega'))
);
GO

-- Actualización para bases creadas con la versión anterior (si la tabla ya está al día, no hace nada)
IF COL_LENGTH('Usuarios', 'pendiente') IS NULL
    ALTER TABLE Usuarios ADD pendiente BIT NOT NULL CONSTRAINT DF_Usuarios_pendiente DEFAULT 0;
GO
IF COL_LENGTH('Usuarios', 'fecha_creacion') IS NULL
    ALTER TABLE Usuarios ADD fecha_creacion DATETIME NOT NULL CONSTRAINT DF_Usuarios_fecha DEFAULT GETDATE();
GO
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints
               WHERE name = 'CK_Usuarios_rol' AND parent_object_id = OBJECT_ID('Usuarios'))
BEGIN
    DECLARE @ck NVARCHAR(200) = (SELECT TOP 1 name FROM sys.check_constraints
                                 WHERE parent_object_id = OBJECT_ID('Usuarios') AND definition LIKE '%rol%');
    IF @ck IS NOT NULL EXEC('ALTER TABLE Usuarios DROP CONSTRAINT [' + @ck + ']');
    ALTER TABLE Usuarios ADD CONSTRAINT CK_Usuarios_rol
        CHECK (rol IN ('Administrador', 'Vendedor', 'Mecanico', 'Bodega'));
END
GO

-- Comprobación: deben verse las 8 columnas
SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Usuarios' ORDER BY ORDINAL_POSITION;
GO

-- para MODULO CLIENTES

-- Clientes: se registran UNA sola vez. 'visitas' lo incrementa el módulo de órdenes.
IF OBJECT_ID('Clientes', 'U') IS NULL
CREATE TABLE Clientes (
    id_cliente     INT IDENTITY PRIMARY KEY,
    codigo         AS ('CLI-' + RIGHT('00000' + CAST(id_cliente AS VARCHAR(10)), 5)) PERSISTED,
    tipo_persona   VARCHAR(10)  NOT NULL DEFAULT 'Natural',
    nombre         VARCHAR(120) NOT NULL,
    dui            VARCHAR(10)  NULL,          -- formato 00000000-0
    nit            VARCHAR(17)  NULL,
    telefono       VARCHAR(20)  NOT NULL,
    correo         VARCHAR(100) NULL,
    direccion      VARCHAR(200) NULL,
    visitas        INT NOT NULL DEFAULT 0,     -- visitas completadas (base del descuento)
    fecha_creacion DATETIME NOT NULL DEFAULT GETDATE(),
    CONSTRAINT CK_Clientes_tipo CHECK (tipo_persona IN ('Natural', 'Juridica'))
);
GO

-- DUI único solo cuando existe (varios clientes pueden tener DUI vacío)
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'UX_Clientes_dui' AND object_id = OBJECT_ID('Clientes'))
    CREATE UNIQUE INDEX UX_Clientes_dui ON Clientes(dui) WHERE dui IS NOT NULL;
GO

-- Vehículos: un cliente puede tener varios (autos y motos). Placa única.
IF OBJECT_ID('Vehiculos', 'U') IS NULL
CREATE TABLE Vehiculos (
    id_vehiculo  INT IDENTITY PRIMARY KEY,
    id_cliente   INT NOT NULL REFERENCES Clientes(id_cliente),
    placa        VARCHAR(12) NOT NULL UNIQUE,
    tipo         VARCHAR(5)  NOT NULL,         -- Auto | Moto
    marca        VARCHAR(40) NOT NULL,
    modelo       VARCHAR(40) NOT NULL,
    anio         INT NOT NULL,
    color        VARCHAR(30) NULL,
    kilometraje  INT NOT NULL DEFAULT 0,
    puertas      INT NULL,                     -- solo Auto
    transmision  VARCHAR(12) NULL,             -- solo Auto: Manual | Automática
    cilindraje   INT NULL,                     -- solo Moto (cc)
    fecha_creacion DATETIME NOT NULL DEFAULT GETDATE(),
    CONSTRAINT CK_Vehiculos_tipo CHECK (tipo IN ('Auto', 'Moto'))
);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Vehiculos_cliente' AND object_id = OBJECT_ID('Vehiculos'))
    CREATE INDEX IX_Vehiculos_cliente ON Vehiculos(id_cliente);
GO

-- Descuento por frecuencia: 25% en las visitas 5, 10, 15, 20...
-- Se le pasa cuántas visitas YA tiene el cliente; devuelve el descuento de la visita que va a hacer.
--   0..3 previas -> 0 | 4 previas (visita 5) -> 0.25 | 5..8 -> 0 | 9 (visita 10) -> 0.25 ...
CREATE OR ALTER FUNCTION dbo.fn_descuento_visita (@visitas_previas INT)
RETURNS DECIMAL(4,2)
AS
BEGIN
    RETURN CASE WHEN (@visitas_previas + 1) % 5 = 0 THEN 0.25 ELSE 0 END;
END
GO

-- Comprobación
SELECT 'Clientes' AS tabla, COUNT(*) AS columnas FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Clientes'
UNION ALL
SELECT 'Vehiculos', COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Vehiculos';
SELECT visitas_previas = v, descuento = dbo.fn_descuento_visita(v) FROM (VALUES (0),(3),(4),(5),(8),(9),(14)) t(v);
GO

--Ventas
-- 1. Tabla de Insumos (Repuestos y accesorios)
IF OBJECT_ID('Insumos', 'U') IS NULL
CREATE TABLE Insumos (
    InsumoID INT IDENTITY PRIMARY KEY,
    Codigo VARCHAR(20) NOT NULL UNIQUE,
    Nombre VARCHAR(100) NOT NULL,
    Marca VARCHAR(50) NULL,
    Costo DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    PrecioVenta DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    Stock INT NOT NULL DEFAULT 0,
    StockMinimo INT NOT NULL DEFAULT 5,
    Activo BIT NOT NULL DEFAULT 1
);
GO

-- 2. Tabla de Servicios del Taller (Mano de obra, afinaciones, etc.)
IF OBJECT_ID('Servicios', 'U') IS NULL
CREATE TABLE Servicios (
    ServicioID INT IDENTITY PRIMARY KEY,
    Codigo VARCHAR(20) NOT NULL UNIQUE,
    Nombre VARCHAR(100) NOT NULL,
    Precio DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    Activo BIT NOT NULL DEFAULT 1
);
GO

-- 3. Tabla de Facturas (Cabecera)
IF OBJECT_ID('Facturas', 'U') IS NULL
CREATE TABLE Facturas (
    FacturaID INT IDENTITY PRIMARY KEY,
    NumeroFactura VARCHAR(30) NOT NULL UNIQUE,
    id_cliente INT NOT NULL REFERENCES Clientes(id_cliente),
    UsuarioID INT NULL,
    Fecha DATETIME NOT NULL DEFAULT GETDATE(),
    Subtotal DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    PorcentajeDescuento DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    MontoDescuento DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    MontoIVA DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    Total DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    Estado VARCHAR(20) NOT NULL DEFAULT 'Completada'
);
GO

-- 4. Tabla de Detalle de Factura (Líneas de la venta)
IF OBJECT_ID('DetalleFactura', 'U') IS NULL
CREATE TABLE DetalleFactura (
    DetalleID INT IDENTITY PRIMARY KEY,
    FacturaID INT NOT NULL REFERENCES Facturas(FacturaID) ON DELETE CASCADE,
    TipoItem VARCHAR(10) NOT NULL, -- 'Insumo' o 'Servicio'
    InsumoID INT NULL REFERENCES Insumos(InsumoID),
    ServicioID INT NULL REFERENCES Servicios(ServicioID),
    Cantidad INT NOT NULL DEFAULT 1,
    PrecioUnitario DECIMAL(10,2) NOT NULL DEFAULT 0.00
);
GO

-- Tabla Principal de Órdenes de Servicio
IF OBJECT_ID('Ordenes', 'U') IS NULL
CREATE TABLE Ordenes (
    id_orden           INT IDENTITY PRIMARY KEY,
    codigo_orden       AS ('ORD-' + RIGHT('00000' + CAST(id_orden AS VARCHAR(10)), 5)) PERSISTED,
    id_cliente         INT NOT NULL REFERENCES Clientes(id_cliente),
    id_vehiculo        INT NOT NULL REFERENCES Vehiculos(id_vehiculo),
    estado             VARCHAR(20) NOT NULL DEFAULT 'Registrado',
    fecha_registro     DATETIME NOT NULL DEFAULT GETDATE(),
    fecha_estimada     DATE NOT NULL,
    descuento_aplicado DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    observaciones      VARCHAR(250) NULL,
    CONSTRAINT CK_Ordenes_estado CHECK (estado IN ('Registrado', 'En proceso', 'Finalizado', 'Entregado'))
);
GO

-- Detalle de Servicios/Insumos asignados a la Orden
IF OBJECT_ID('DetalleOrden', 'U') IS NULL
CREATE TABLE DetalleOrden (
    id_detalle INT IDENTITY PRIMARY KEY,
    id_orden   INT NOT NULL REFERENCES Ordenes(id_orden) ON DELETE CASCADE,
    tipo_item  VARCHAR(10) NOT NULL CHECK (tipo_item IN ('Servicio', 'Insumo')),
    id_item    INT NOT NULL, -- ServicioID o InsumoID
    nombre     VARCHAR(100) NOT NULL,
    precio     DECIMAL(10,2) NOT NULL DEFAULT 0.00
);
GO