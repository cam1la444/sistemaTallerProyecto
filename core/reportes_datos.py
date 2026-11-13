"""Consultas para el módulo Reportes (sin interfaz: devuelven listas y diccionarios de Python).

Solo cuentan las facturas con Estado = 'Completada'. Para los costos se usa el Costo ACTUAL del
repuesto en Inventario, por eso las ganancias son ESTIMADAS.
"""
import re
from datetime import date, datetime, timedelta

from core.database import consultar, get_connection

PERIODOS = ["Hoy", "Últimos 7 días", "Últimos 30 días", "Este mes", "Este año", "Todo"]
ESTADOS_ORDEN = ["Registrado", "En proceso", "Finalizado", "Entregado"]


# ---------------------------------------------------------------------- utilidades
def dinero(valor):
    """Formato $1,234.50"""
    return f"${float(valor or 0):,.2f}"


def escapar_like(texto):
    """Para que %, _ y [ escritos por el usuario se busquen tal cual (se usa con ESCAPE '\\')."""
    return re.sub(r"([\\%_\[])", r"\\\1", texto)


def desde_periodo(periodo, ahora=None):
    """Nombre del período -> fecha de inicio (datetime a las 00:00) o None si es 'Todo'."""
    ahora = ahora or datetime.now()
    hoy = datetime(ahora.year, ahora.month, ahora.day)
    if periodo == "Hoy":
        return hoy
    if periodo == "Últimos 7 días":
        return hoy - timedelta(days=6)
    if periodo == "Últimos 30 días":
        return hoy - timedelta(days=29)
    if periodo == "Este mes":
        return hoy.replace(day=1)
    if periodo == "Este año":
        return hoy.replace(month=1, day=1)
    return None


def _desde(campo, desde):
    """Fragmento SQL y parámetros para filtrar por fecha."""
    return (f" AND {campo} >= ?", [desde]) if desde else ("", [])


def _a_fecha(valor):
    if isinstance(valor, datetime):
        return valor
    if isinstance(valor, date):
        return datetime(valor.year, valor.month, valor.day)
    for formato in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(valor), formato)
        except ValueError:
            pass
    return None


def _primeras(sql, params=(), limite=10):
    """Como consultar(), pero trae como máximo 'limite' filas (para listas ORDER BY ... DESC)."""
    with get_connection() as cn:
        cur = cn.cursor()
        cur.execute(sql, tuple(params))
        columnas = [c[0] for c in cur.description]
        return [dict(zip(columnas, f)) for f in cur.fetchmany(limite)]


# ---------------------------------------------------------------------- piezas y servicios
def piezas_mas_usadas(desde=None):
    """Repuestos vendidos, del más al menos usado. Incluye repuestos ya retirados del inventario."""
    filtro, params = _desde("f.Fecha", desde)
    filas = consultar(
        "SELECT i.Codigo, i.Nombre, SUM(d.Cantidad) AS cantidad,"
        " SUM(d.Cantidad * d.PrecioUnitario) AS ingresos, SUM(d.Cantidad * i.Costo) AS costo,"
        " COUNT(DISTINCT f.FacturaID) AS facturas "
        "FROM DetalleFactura d "
        "JOIN Facturas f ON f.FacturaID = d.FacturaID "
        "JOIN Insumos i ON i.InsumoID = d.InsumoID "
        "WHERE d.TipoItem = 'Insumo' AND f.Estado = 'Completada'" + filtro +
        " GROUP BY i.InsumoID, i.Codigo, i.Nombre", tuple(params))
    datos = []
    for f in filas:
        ingresos, costo = float(f["ingresos"] or 0), float(f["costo"] or 0)
        datos.append({"codigo": f["Codigo"], "nombre": f["Nombre"], "cantidad": int(f["cantidad"]),
                      "ingresos": ingresos, "ganancia": ingresos - costo, "facturas": int(f["facturas"])})
    datos.sort(key=lambda d: (-d["cantidad"], -d["ingresos"], d["nombre"]))
    return datos


def servicios_resumen(desde=None):
    """Servicios pedidos en órdenes y facturados en ventas, unidos por servicio."""
    filtro_f, params_f = _desde("f.Fecha", desde)
    facturados = consultar(
        "SELECT s.ServicioID, s.Nombre, SUM(d.Cantidad) AS veces,"
        " SUM(d.Cantidad * d.PrecioUnitario) AS ingresos "
        "FROM DetalleFactura d "
        "JOIN Facturas f ON f.FacturaID = d.FacturaID "
        "JOIN Servicios s ON s.ServicioID = d.ServicioID "
        "WHERE d.TipoItem = 'Servicio' AND f.Estado = 'Completada'" + filtro_f +
        " GROUP BY s.ServicioID, s.Nombre", tuple(params_f))
    filtro_o, params_o = _desde("o.fecha_registro", desde)
    en_ordenes = consultar(
        "SELECT d.id_item AS ServicioID, MAX(d.nombre) AS Nombre, COUNT(*) AS veces "
        "FROM DetalleOrden d JOIN Ordenes o ON o.id_orden = d.id_orden "
        "WHERE d.tipo_item = 'Servicio'" + filtro_o + " GROUP BY d.id_item", tuple(params_o))

    por_id = {}
    for r in en_ordenes:
        por_id[r["ServicioID"]] = {"nombre": r["Nombre"], "ordenes": int(r["veces"]), "facturado": 0, "ingresos": 0.0}
    for r in facturados:
        d = por_id.setdefault(r["ServicioID"], {"nombre": r["Nombre"], "ordenes": 0, "facturado": 0, "ingresos": 0.0})
        d["facturado"] = int(r["veces"])
        d["ingresos"] = float(r["ingresos"] or 0)
    datos = list(por_id.values())
    datos.sort(key=lambda d: (-(d["ordenes"] + d["facturado"]), -d["ingresos"], d["nombre"]))
    return datos


def ordenes_por_estado(desde=None):
    filtro, params = _desde("fecha_registro", desde)
    cuenta = {e: 0 for e in ESTADOS_ORDEN}
    for r in consultar("SELECT estado, COUNT(*) AS n FROM Ordenes WHERE 1 = 1" + filtro + " GROUP BY estado",
                       tuple(params)):
        cuenta[r["estado"]] = int(r["n"])
    return cuenta


def vehiculos_por_tipo():
    cuenta = {"Auto": 0, "Moto": 0}
    for r in consultar("SELECT tipo, COUNT(*) AS n FROM Vehiculos GROUP BY tipo"):
        cuenta[r["tipo"]] = int(r["n"])
    return cuenta


# ---------------------------------------------------------------------- ventas
def ventas_resumen(desde=None, ahora=None):
    """Ventas agrupadas por día (períodos cortos) o por mes (períodos largos), sin huecos."""
    ahora = ahora or datetime.now()
    filtro, params = _desde("Fecha", desde)
    filas = consultar("SELECT Fecha, Subtotal, MontoDescuento, MontoIVA, Total FROM Facturas "
                      "WHERE Estado = 'Completada'" + filtro + " ORDER BY Fecha", tuple(params))
    por = "dia" if (desde is not None and (ahora - desde).days <= 31) else "mes"

    acumulado = {}
    tot = {"facturas": 0, "total": 0.0, "subtotal": 0.0, "descuento": 0.0, "iva": 0.0}
    primera = None
    for f in filas:
        fecha = _a_fecha(f["Fecha"])
        if fecha is None:
            continue
        primera = primera or fecha
        clave = fecha.date() if por == "dia" else date(fecha.year, fecha.month, 1)
        item = acumulado.setdefault(clave, {"total": 0.0, "facturas": 0})
        item["total"] += float(f["Total"] or 0)
        item["facturas"] += 1
        tot["facturas"] += 1
        tot["total"] += float(f["Total"] or 0)
        tot["subtotal"] += float(f["Subtotal"] or 0)
        tot["descuento"] += float(f["MontoDescuento"] or 0)
        tot["iva"] += float(f["MontoIVA"] or 0)
    tot["ticket"] = tot["total"] / tot["facturas"] if tot["facturas"] else 0.0

    serie = []
    inicio = (desde or primera)
    if inicio is not None:
        if por == "dia":
            dia, fin = inicio.date(), ahora.date()
            while dia <= fin:
                serie.append((dia, dia.strftime("%d/%m"), acumulado.get(dia, {"total": 0.0, "facturas": 0})))
                dia += timedelta(days=1)
        else:
            mes, fin = date(inicio.year, inicio.month, 1), date(ahora.year, ahora.month, 1)
            while mes <= fin:
                serie.append((mes, mes.strftime("%m/%Y"), acumulado.get(mes, {"total": 0.0, "facturas": 0})))
                mes = date(mes.year + (mes.month == 12), mes.month % 12 + 1, 1)
    return {"por": por,
            "serie": [{"etiqueta": e, "total": v["total"], "facturas": v["facturas"]} for _, e, v in serie],
            "totales": tot}


def kpis(ahora=None):
    """Indicadores de la pestaña Resumen."""
    ahora = ahora or datetime.now()
    hoy = datetime(ahora.year, ahora.month, ahora.day)
    mes = hoy.replace(day=1)

    def ventas(desde):
        r = consultar("SELECT COUNT(*) AS n, COALESCE(SUM(Total), 0) AS total FROM Facturas "
                      "WHERE Estado = 'Completada' AND Fecha >= ?", (desde,))[0]
        return int(r["n"]), float(r["total"])

    n_hoy, total_hoy = ventas(hoy)
    n_mes, total_mes = ventas(mes)
    ganancia = consultar(
        "SELECT COALESCE(SUM(d.Cantidad * (d.PrecioUnitario - i.Costo)), 0) AS g "
        "FROM DetalleFactura d JOIN Facturas f ON f.FacturaID = d.FacturaID "
        "JOIN Insumos i ON i.InsumoID = d.InsumoID "
        "WHERE d.TipoItem = 'Insumo' AND f.Estado = 'Completada' AND f.Fecha >= ?", (mes,))[0]["g"]
    return {
        "ventas_hoy": total_hoy, "facturas_hoy": n_hoy,
        "ventas_mes": total_mes, "facturas_mes": n_mes,
        "ticket_mes": total_mes / n_mes if n_mes else 0.0,
        "ganancia_repuestos_mes": float(ganancia),
        "ordenes_activas": int(consultar("SELECT COUNT(*) AS n FROM Ordenes "
                                         "WHERE estado IN ('Registrado', 'En proceso')")[0]["n"]),
        "clientes": int(consultar("SELECT COUNT(*) AS n FROM Clientes")[0]["n"]),
        "stock_bajo": int(consultar("SELECT COUNT(*) AS n FROM Insumos "
                                    "WHERE Activo = 1 AND Stock <= StockMinimo")[0]["n"]),
    }


def ultimas_facturas(n=8):
    return _primeras(
        "SELECT f.FacturaID, f.NumeroFactura, f.Fecha, f.Total, f.Estado, c.nombre AS cliente "
        "FROM Facturas f JOIN Clientes c ON c.id_cliente = f.id_cliente "
        "ORDER BY f.Fecha DESC, f.FacturaID DESC", (), n)


# ---------------------------------------------------------------------- clientes y facturas
def clientes_resumen(texto=""):
    """Clientes con cuántas facturas y cuánto han gastado (de mayor a menor)."""
    sql = ("SELECT c.id_cliente, c.codigo, c.nombre, c.visitas, COUNT(f.FacturaID) AS facturas,"
           " COALESCE(SUM(f.Total), 0) AS total "
           "FROM Clientes c LEFT JOIN Facturas f ON f.id_cliente = c.id_cliente AND f.Estado = 'Completada' ")
    params = []
    texto = (texto or "").strip()
    if texto:
        patron = f"%{escapar_like(texto)}%"
        sql += ("WHERE (c.nombre LIKE ? ESCAPE '\\' OR c.codigo LIKE ? ESCAPE '\\'"
                " OR c.dui LIKE ? ESCAPE '\\' OR c.telefono LIKE ? ESCAPE '\\') ")
        params = [patron] * 4
    sql += "GROUP BY c.id_cliente, c.codigo, c.nombre, c.visitas ORDER BY total DESC, c.nombre"
    return consultar(sql, tuple(params))


def cliente(id_cliente):
    filas = consultar("SELECT id_cliente, codigo, tipo_persona, nombre, dui, nit, telefono, correo, direccion, visitas "
                      "FROM Clientes WHERE id_cliente = ?", (id_cliente,))
    return filas[0] if filas else None


def vehiculos_de_cliente(id_cliente):
    return consultar("SELECT id_vehiculo, placa, tipo, marca, modelo, anio, color, kilometraje, puertas,"
                     " transmision, cilindraje FROM Vehiculos WHERE id_cliente = ? ORDER BY tipo, placa",
                     (id_cliente,))


def vehiculo(id_vehiculo):
    filas = consultar("SELECT id_vehiculo, placa, tipo, marca, modelo, anio, color, kilometraje, puertas,"
                      " transmision, cilindraje FROM Vehiculos WHERE id_vehiculo = ?", (id_vehiculo,))
    return filas[0] if filas else None


def vehiculo_sugerido(id_cliente):
    """Vehículo de la última orden del cliente (las facturas no guardan el vehículo); si no hay, el primero."""
    ult = _primeras("SELECT id_vehiculo FROM Ordenes WHERE id_cliente = ? ORDER BY fecha_registro DESC, id_orden DESC",
                    (id_cliente,), 1)
    if ult:
        return ult[0]["id_vehiculo"]
    todos = vehiculos_de_cliente(id_cliente)
    return todos[0]["id_vehiculo"] if todos else None


def facturas_de_cliente(id_cliente):
    return consultar("SELECT FacturaID, NumeroFactura, Fecha, Subtotal, PorcentajeDescuento, MontoDescuento,"
                     " MontoIVA, Total, Estado FROM Facturas WHERE id_cliente = ? "
                     "ORDER BY Fecha DESC, FacturaID DESC", (id_cliente,))


def lineas_de_factura(factura_id):
    """Servicios primero y luego repuestos, en el orden en que se cobraron."""
    return consultar(
        "SELECT d.TipoItem, d.Cantidad, d.PrecioUnitario, COALESCE(i.Codigo, s.Codigo) AS Codigo,"
        " COALESCE(i.Nombre, s.Nombre) AS Nombre, i.Marca "
        "FROM DetalleFactura d "
        "LEFT JOIN Insumos i ON i.InsumoID = d.InsumoID "
        "LEFT JOIN Servicios s ON s.ServicioID = d.ServicioID "
        "WHERE d.FacturaID = ? "
        "ORDER BY CASE WHEN d.TipoItem = 'Servicio' THEN 0 ELSE 1 END, d.DetalleID", (factura_id,))


def datos_factura(factura_id):
    """(factura, cliente, líneas) de una factura, o None si no existe."""
    filas = consultar("SELECT FacturaID, NumeroFactura, id_cliente, Fecha, Subtotal, PorcentajeDescuento,"
                      " MontoDescuento, MontoIVA, Total, Estado FROM Facturas WHERE FacturaID = ?", (factura_id,))
    if not filas:
        return None
    f = filas[0]
    return f, cliente(f["id_cliente"]), lineas_de_factura(factura_id)


def historial_cliente(id_cliente):
    """Todo lo necesario para el PDF de historial: cliente, vehículos, facturas (con líneas) y órdenes."""
    facturas = facturas_de_cliente(id_cliente)
    for f in facturas:
        f["lineas"] = lineas_de_factura(f["FacturaID"])
    ordenes = consultar(
        "SELECT o.id_orden, o.codigo_orden, o.estado, o.fecha_registro, o.fecha_estimada, o.observaciones,"
        " v.tipo, v.marca, v.modelo, v.placa "
        "FROM Ordenes o JOIN Vehiculos v ON v.id_vehiculo = o.id_vehiculo "
        "WHERE o.id_cliente = ? ORDER BY o.fecha_registro DESC, o.id_orden DESC", (id_cliente,))
    servicios = {}
    for d in consultar("SELECT d.id_orden, d.nombre, d.precio FROM DetalleOrden d "
                       "JOIN Ordenes o ON o.id_orden = d.id_orden WHERE o.id_cliente = ? ORDER BY d.id_detalle",
                       (id_cliente,)):
        servicios.setdefault(d["id_orden"], []).append(d)
    for o in ordenes:
        o["servicios"] = servicios.get(o["id_orden"], [])
    return {"cliente": cliente(id_cliente), "vehiculos": vehiculos_de_cliente(id_cliente),
            "facturas": facturas, "ordenes": ordenes}