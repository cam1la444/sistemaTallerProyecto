-- ============================================================================
-- sql/03_servicios.sql
-- Catálogo de servicios (mano de obra) del taller: autos y motos.
-- Es lo que aparece en "Nueva Orden de Servicio" (Órdenes) y en la pestaña de servicios de Ventas.
--
--   Precio = lo que cobra el taller por la mano de obra (sin IVA, sin repuestos).
--   Los repuestos se cobran aparte desde Inventario/Ventas.
--
-- Ejecute antes sql/01_schema.sql. Se puede repetir sin problema: solo inserta los
-- servicios cuyo código o nombre todavía no existan. Los precios son de ejemplo:
-- ajústelos a los suyos con un UPDATE (ver el ejemplo al final).
-- ============================================================================
USE Taller;
GO

;WITH Datos (Codigo, Nombre, Precio) AS (
    SELECT * FROM (VALUES
        -- Mantenimiento
        ('SRV-001', N'Cambio de aceite y filtro de aceite',                 8.00),
        ('SRV-002', N'Cambio de filtro de aire',                            4.00),
        ('SRV-003', N'Cambio de filtro de combustible',                    10.00),
        ('SRV-004', N'Cambio de filtro de cabina (A/C)',                    4.00),
        ('SRV-005', N'Afinación menor (bujías y revisión)',                25.00),
        ('SRV-006', N'Afinación mayor (bujías, filtros y puesta a punto)', 45.00),
        ('SRV-007', N'Cambio de líquido de frenos (purga)',                15.00),
        ('SRV-008', N'Cambio de refrigerante y lavado de radiador',        20.00),
        ('SRV-009', N'Cambio de aceite de transmisión',                    18.00),
        ('SRV-010', N'Revisión general multipunto',                        10.00),
        -- Frenos
        ('SRV-011', N'Cambio de pastillas de freno delanteras',            20.00),
        ('SRV-012', N'Cambio de pastillas de freno traseras',              20.00),
        ('SRV-013', N'Rectificado de discos de freno (par)',               25.00),
        ('SRV-014', N'Cambio de zapatas de freno traseras (tambor)',       22.00),
        -- Llantas y dirección
        ('SRV-015', N'Cambio de llantas (montaje y balanceo, por llanta)',  6.00),
        ('SRV-016', N'Alineación',                                         25.00),
        ('SRV-017', N'Balanceo de llantas (4 llantas)',                    12.00),
        ('SRV-018', N'Rotación de llantas',                                 8.00),
        ('SRV-019', N'Reparación de ponchadura',                            5.00),
        -- Suspensión
        ('SRV-020', N'Cambio de amortiguadores (par)',                     35.00),
        ('SRV-021', N'Cambio de rótulas o terminales (unidad)',            15.00),
        ('SRV-022', N'Cambio de bujes de barra estabilizadora',            18.00),
        ('SRV-023', N'Cambio de rodamiento de rueda',                      25.00),
        -- Motor y transmisión
        ('SRV-024', N'Cambio de banda de distribución (kit)',              90.00),
        ('SRV-025', N'Cambio de banda serpentina',                         15.00),
        ('SRV-026', N'Cambio de bomba de agua',                            45.00),
        ('SRV-027', N'Cambio de embrague (mano de obra)',                 150.00),
        -- Eléctrico y aire acondicionado
        ('SRV-028', N'Diagnóstico con escáner',                            20.00),
        ('SRV-029', N'Revisión eléctrica y de luces',                      12.00),
        ('SRV-030', N'Cambio de batería (instalación)',                     5.00),
        ('SRV-031', N'Cambio de alternador o motor de arranque',           40.00),
        ('SRV-032', N'Carga de gas del aire acondicionado',                35.00),
        -- Motos
        ('SRV-040', N'Cambio de aceite de motor (moto)',                    5.00),
        ('SRV-041', N'Afinación completa (moto)',                          20.00),
        ('SRV-042', N'Cambio de kit de arrastre: cadena y piñones (moto)', 20.00),
        ('SRV-043', N'Ajuste y lubricación de cadena (moto)',               4.00),
        ('SRV-044', N'Cambio de pastillas o bandas de freno (moto)',        8.00),
        ('SRV-045', N'Cambio de llanta (moto, por llanta)',                 6.00),
        ('SRV-046', N'Cambio de bujía (moto)',                              3.00)
    ) AS v (Codigo, Nombre, Precio)
)
INSERT INTO Servicios (Codigo, Nombre, Precio)
SELECT d.Codigo, d.Nombre, d.Precio
FROM Datos d
WHERE NOT EXISTS (SELECT 1 FROM Servicios s WHERE s.Codigo = d.Codigo OR s.Nombre = d.Nombre);

-- Comprobación: cuántos servicios activos hay
SELECT COUNT(*) AS servicios_activos FROM Servicios WHERE Activo = 1;
GO

-- Para cambiar un precio (ejemplo):
--   UPDATE Servicios SET Precio = 10.00 WHERE Codigo = 'SRV-001';
-- Para ocultar un servicio sin borrarlo (sigue en facturas viejas):
--   UPDATE Servicios SET Activo = 0 WHERE Codigo = 'SRV-001';