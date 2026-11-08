-- ============================================================================
-- sql/02_inventario.sql
-- Repuestos de carros de ejemplo para el módulo Inventario.
--
--   Costo       = precio de COMPRA mayorista (lo que paga el taller al proveedor)
--   PrecioVenta = precio FINAL al cliente (sin IVA: el IVA se suma en Ventas)
--
-- Ejecute antes sql/01_schema.sql. Este script se puede repetir sin problema:
-- solo inserta los códigos que todavía no existen y NO toca los que ya están.
-- Los precios son de ejemplo: ajústelos desde la pantalla Inventario (Editar).
-- ============================================================================
USE Taller;
GO

;WITH Datos (Codigo, Nombre, Marca, Costo, PrecioVenta, Stock, StockMinimo) AS (
    SELECT * FROM (VALUES
        -- Filtros
        ('FIL-001', N'Filtro de aceite (auto compacto)',          N'Bosch',        2.80,   4.50, 40, 10),
        ('FIL-002', N'Filtro de aceite (pick-up / SUV)',          N'Fram',         3.60,   5.75, 30, 10),
        ('FIL-003', N'Filtro de aire de motor',                   N'Mann-Filter',  6.50,  10.50, 25,  8),
        ('FIL-004', N'Filtro de combustible',                     N'Bosch',        7.00,  11.50, 18,  6),
        ('FIL-005', N'Filtro de cabina (A/C)',                    N'Mann-Filter',  5.50,   9.00, 20,  6),
        -- Lubricantes y fluidos
        ('LUB-001', N'Aceite de motor 10W-30 (galón)',            N'Valvoline',   14.50,  21.00, 30,  8),
        ('LUB-002', N'Aceite de motor 5W-30 sintético (galón)',   N'Mobil 1',     27.00,  38.50, 24,  6),
        ('LUB-003', N'Aceite de motor 20W-50 (galón)',            N'Castrol',     15.50,  22.50, 20,  6),
        ('LUB-004', N'Líquido de frenos DOT 4 (500 ml)',          N'Prestone',     3.80,   6.50, 25,  8),
        ('LUB-005', N'Refrigerante concentrado (galón)',          N'Prestone',     8.50,  13.50, 20,  6),
        ('LUB-006', N'Aceite de transmisión automática ATF (cuarto)', N'Valvoline', 6.50, 10.25, 15,  5),
        ('LUB-007', N'Aceite de caja manual 75W-90 (cuarto)',     N'Castrol',      9.00,  14.00, 12,  4),
        -- Motor
        ('MOT-001', N'Bujía estándar',                            N'NGK',          2.20,   4.00, 80, 20),
        ('MOT-002', N'Bujía de iridio',                           N'Denso',        8.50,  13.50, 40, 12),
        ('MOT-003', N'Bobina de ignición',                        N'Bosch',       21.00,  34.00, 12,  4),
        ('MOT-004', N'Banda serpentina',                          N'Gates',       14.00,  22.50, 15,  5),
        ('MOT-005', N'Kit de banda de distribución',              N'Gates',       52.00,  82.00,  3,  3),
        ('MOT-006', N'Bomba de agua',                             N'Aisin',       28.00,  45.00,  8,  3),
        ('MOT-007', N'Termostato con empaque',                    N'Motorad',      7.50,  13.00, 14,  4),
        ('MOT-008', N'Sensor de oxígeno (O2)',                    N'Denso',       38.00,  62.00,  8,  3),
        ('MOT-009', N'Empaque de tapa de válvulas',               N'Victor Reinz',12.50,  21.00, 10,  3),
        ('MOT-010', N'Radiador de aluminio',                      N'Denso',       95.00, 150.00,  4,  2),
        -- Frenos
        ('FRE-001', N'Pastillas de freno delanteras',             N'Akebono',     22.00,  38.00, 20,  6),
        ('FRE-002', N'Pastillas de freno traseras',               N'Akebono',     18.00,  31.00, 15,  5),
        ('FRE-003', N'Disco de freno delantero (unidad)',         N'Brembo',      28.00,  46.00, 12,  4),
        ('FRE-004', N'Zapatas de freno traseras (tambor)',        N'Bendix',      16.00,  27.00, 10,  4),
        ('FRE-005', N'Cilindro maestro de freno',                 N'ACDelco',     42.00,  68.00,  5,  2),
        -- Suspensión y dirección
        ('SUS-001', N'Amortiguador delantero (unidad)',           N'Monroe',      38.00,  62.00, 10,  4),
        ('SUS-002', N'Amortiguador trasero (unidad)',             N'Monroe',      32.00,  53.00, 10,  4),
        ('SUS-003', N'Rótula inferior',                           N'Moog',        14.50,  25.00, 12,  4),
        ('SUS-004', N'Terminal de dirección',                     N'Moog',        12.00,  21.00, 14,  4),
        ('SUS-005', N'Buje de barra estabilizadora',              N'Moog',         3.50,   7.00, 30, 10),
        ('SUS-006', N'Rodamiento de rueda delantero',             N'SKF',         24.00,  40.00, 10,  4),
        ('SUS-007', N'Bieleta de barra estabilizadora',           N'Moog',        10.00,  18.00, 16,  5),
        -- Sistema eléctrico
        ('ELE-001', N'Batería 12V 45Ah',                          N'LTH',         62.00,  95.00,  8,  3),
        ('ELE-002', N'Batería 12V 65Ah',                          N'LTH',         78.00, 118.00,  6,  3),
        ('ELE-003', N'Alternador remanufacturado',                N'Bosch',      110.00, 170.00,  2,  2),
        ('ELE-004', N'Motor de arranque remanufacturado',         N'Bosch',       95.00, 150.00,  3,  2),
        ('ELE-005', N'Bombilla H4 (par)',                         N'Philips',      6.50,  12.00, 30, 10),
        ('ELE-006', N'Bombilla H7 (unidad)',                      N'Philips',      5.00,   9.50, 25,  8),
        ('ELE-007', N'Kit de fusibles surtidos',                  N'Bussmann',     2.50,   5.00, 20,  6),
        -- Embrague y accesorios
        ('CLU-001', N'Kit de embrague (disco, plato y collarín)', N'Exedy',       98.00, 155.00,  4,  2),
        ('ACC-001', N'Plumilla limpiaparabrisas 20"',             N'Bosch',        3.80,   7.50, 30, 10),
        ('ACC-002', N'Plumilla limpiaparabrisas 22"',             N'Bosch',        4.20,   8.00, 30, 10)
    ) AS v (Codigo, Nombre, Marca, Costo, PrecioVenta, Stock, StockMinimo)
)
INSERT INTO Insumos (Codigo, Nombre, Marca, Costo, PrecioVenta, Stock, StockMinimo)
SELECT d.Codigo, d.Nombre, d.Marca, d.Costo, d.PrecioVenta, d.Stock, d.StockMinimo
FROM Datos d
WHERE NOT EXISTS (SELECT 1 FROM Insumos i WHERE i.Codigo = d.Codigo);

-- Comprobación: cuántos repuestos quedaron activos en el inventario
SELECT COUNT(*) AS repuestos_activos FROM Insumos WHERE Activo = 1;
GO