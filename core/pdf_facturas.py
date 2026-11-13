"""PDF de facturación (reportlab): factura individual e historial completo de un cliente.

Sirve igual para autos y motos: el bloque del vehículo muestra puertas/transmisión si es Auto
y cilindraje si es Moto. Los datos llegan ya cargados (ver core/reportes_datos.py); este módulo
solo dibuja, no consulta la base de datos.
"""
from datetime import date, datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.platypus import CondPageBreak, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core.reportes_datos import dinero

# ---- Datos del taller que salen en el encabezado (edítelos a gusto) ----
EMPRESA_NOMBRE = "TALLER PRO"
EMPRESA_LEMA = "Taller mecánico de autos y motos"
EMPRESA_DATOS = []      # líneas opcionales, p. ej. ["Dirección del taller", "Tel. 2222-0000", "NIT 0000-000000-000-0"]

AZUL = colors.HexColor("#1F3A5F")
AZUL_CLARO = colors.HexColor("#E8EEF6")
GRIS = colors.HexColor("#F1F3F6")
BORDE = colors.HexColor("#CBD2DC")
SUAVE = colors.HexColor("#6B7280")
TEXTO = colors.HexColor("#1F2937")
VERDE = colors.HexColor("#067647")
ROJO = colors.HexColor("#B42318")

MARGEN = 1.8 * cm
ANCHO = letter[0] - 2 * MARGEN


# ---------------------------------------------------------------------- utilidades
def _fecha(valor, con_hora=False):
    if isinstance(valor, str):
        for formato in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                valor = datetime.strptime(valor, formato)
                break
            except ValueError:
                pass
    if isinstance(valor, (datetime, date)):
        return valor.strftime("%d/%m/%Y %H:%M" if con_hora and isinstance(valor, datetime) else "%d/%m/%Y")
    return str(valor or "")


def _estilos():
    base = dict(fontName="Helvetica", fontSize=9, leading=12, textColor=TEXTO)

    def est(nombre, **cambios):
        return ParagraphStyle(nombre, **{**base, **cambios})

    return {
        "n": est("n"),
        "der": est("der", alignment=TA_RIGHT),
        "der_b": est("der_b", alignment=TA_RIGHT, fontName="Helvetica-Bold"),
        "peq": est("peq", fontSize=7.5, leading=10, textColor=SUAVE),
        "peq_der": est("peq_der", fontSize=8, leading=10, textColor=SUAVE, alignment=TA_RIGHT),
        "caja_t": est("caja_t", fontName="Helvetica-Bold", fontSize=8, textColor=AZUL),
        "th": est("th", fontName="Helvetica-Bold", fontSize=8.5, textColor=colors.white),
        "th_der": est("th_der", fontName="Helvetica-Bold", fontSize=8.5, textColor=colors.white, alignment=TA_RIGHT),
        "seccion": est("seccion", fontName="Helvetica-Bold", fontSize=8.5, textColor=AZUL),
        "h2": est("h2", fontName="Helvetica-Bold", fontSize=11.5, leading=14, textColor=AZUL,
                  spaceBefore=12, spaceAfter=5, keepWithNext=1),
        "blanco": est("blanco", textColor=colors.white),
        "marca": est("marca", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=colors.white),
        "titulo_der": est("titulo_der", fontName="Helvetica-Bold", fontSize=15, leading=20, alignment=TA_RIGHT,
                          textColor=colors.white),
        "blanco_peq": est("blanco_peq", fontSize=8, leading=10.5, textColor=colors.HexColor("#D6E0EE")),
        "blanco_der": est("blanco_der", textColor=colors.white, alignment=TA_RIGHT),
        "blanco_peq_der": est("blanco_peq_der", fontSize=8.5, leading=11, alignment=TA_RIGHT,
                              textColor=colors.HexColor("#D6E0EE")),
        "gracias": est("gracias", alignment=TA_CENTER, textColor=SUAVE, fontSize=9),
        "alerta": est("alerta", fontName="Helvetica-Bold", textColor=ROJO, alignment=TA_CENTER),
    }


def _p(texto, estilo):
    return Paragraph(escape(str(texto)), estilo)


class _CanvasNumerado(canvas.Canvas):
    """Pone 'Página x de y' y una línea de pie en cada hoja."""

    def __init__(self, *args, pie="", **kwargs):
        super().__init__(*args, **kwargs)
        self._paginas = []
        self._pie = pie

    def showPage(self):
        self._paginas.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._paginas)
        for estado in self._paginas:
            self.__dict__.update(estado)
            ancho = self._pagesize[0]
            self.setStrokeColor(BORDE)
            self.line(MARGEN, 1.45 * cm, ancho - MARGEN, 1.45 * cm)
            self.setFont("Helvetica", 8)
            self.setFillColor(SUAVE)
            self.drawString(MARGEN, 1.0 * cm, self._pie)
            self.drawRightString(ancho - MARGEN, 1.0 * cm, f"Página {self._pageNumber} de {total}")
            super().showPage()
        super().save()


def _construir(ruta, story, titulo, pie):
    doc = SimpleDocTemplate(ruta, pagesize=letter, leftMargin=MARGEN, rightMargin=MARGEN,
                            topMargin=1.5 * cm, bottomMargin=2.0 * cm, title=titulo, author=EMPRESA_NOMBRE)
    doc.build(story, canvasmaker=lambda *a, **k: _CanvasNumerado(*a, pie=pie, **k))
    return ruta


def _pie():
    return f"{EMPRESA_NOMBRE} · Documento generado el {datetime.now():%d/%m/%Y %H:%M}"


# ---------------------------------------------------------------------- bloques
def _cabecera(st, titulo, lineas_der):
    izq = [Paragraph(escape(EMPRESA_NOMBRE), st["marca"]), Paragraph(escape(EMPRESA_LEMA), st["blanco_peq"])]
    izq += [Paragraph(escape(x), st["blanco_peq"]) for x in EMPRESA_DATOS]
    der = [Paragraph(escape(titulo), st["titulo_der"])]
    der += [Paragraph(x, st["blanco_peq_der"]) for x in lineas_der]
    t = Table([[izq, der]], colWidths=[ANCHO * 0.5, ANCHO * 0.5])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), AZUL), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 14), ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 12), ("BOTTOMPADDING", (0, 0), (-1, -1), 12)]))
    return t


def _caja(st, titulo, filas, ancho):
    datos = [[Paragraph(escape(titulo), st["caja_t"])]]
    for etiqueta, valor in filas:
        if valor not in (None, ""):
            datos.append([Paragraph(f"<b>{escape(etiqueta)}:</b> {escape(str(valor))}", st["n"])])
    if len(datos) == 1:
        datos.append([Paragraph("Sin información", st["peq"])])
    t = Table(datos, colWidths=[ancho])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), AZUL_CLARO), ("BOX", (0, 0), (-1, -1), 0.6, BORDE),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return t


def _dos_cajas(st, titulo1, filas1, titulo2, filas2):
    mitad = (ANCHO - 0.5 * cm) / 2
    t = Table([[_caja(st, titulo1, filas1, mitad), "", _caja(st, titulo2, filas2, mitad)]],
              colWidths=[mitad, 0.5 * cm, mitad])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return t


def _filas_cliente(c):
    if not c:
        return [("Cliente", "No disponible")]
    tipo = "Persona jurídica" if c.get("tipo_persona") == "Juridica" else "Persona natural"
    return [("Cliente", c["nombre"]), ("Código", c.get("codigo")), ("Tipo", tipo), ("DUI", c.get("dui")),
            ("NIT", c.get("nit")), ("Teléfono", c.get("telefono")), ("Correo", c.get("correo")),
            ("Dirección", c.get("direccion"))]


def _detalle_vehiculo(v):
    """Características según el tipo: Auto (puertas, transmisión) o Moto (cilindraje)."""
    if (v.get("tipo") or "").lower() == "moto":
        return f"{v['cilindraje']} cc" if v.get("cilindraje") else ""
    partes = []
    if v.get("puertas"):
        partes.append(f"{v['puertas']} puertas")
    if v.get("transmision"):
        partes.append(str(v["transmision"]))
    return " · ".join(partes)


def _filas_vehiculo(v):
    if not v:
        return [("Vehículo", "No especificado")]
    km = f"{int(v['kilometraje']):,} km" if v.get("kilometraje") is not None else None
    filas = [("Tipo", v["tipo"]), ("Vehículo", f"{v['marca']} {v['modelo']} {v['anio']}"),
             ("Placa", v["placa"]), ("Color", v.get("color")), ("Kilometraje", km)]
    detalle = _detalle_vehiculo(v)
    if detalle:
        filas.append(("Moto" if v["tipo"] == "Moto" else "Auto", detalle))
    return filas


def _tabla_lineas(st, lineas):
    """Servicios y repuestos en secciones separadas, cada una con su subtotal."""
    otros = [2.6 * cm, 1.5 * cm, 2.7 * cm, 2.9 * cm]
    anchos = [otros[0], ANCHO - sum(otros), otros[1], otros[2], otros[3]]
    filas = [[Paragraph(t, st["th_der" if i >= 2 else "th"])
              for i, t in enumerate(["Código", "Descripción", "Cant.", "Precio unit.", "Subtotal"])]]
    estilo = [("BACKGROUND", (0, 0), (-1, 0), AZUL), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
              ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
              ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]

    for titulo, tipo in (("SERVICIOS", "Servicio"), ("REPUESTOS E INSUMOS", "Insumo")):
        grupo = [x for x in lineas if x["TipoItem"] == tipo]
        if not grupo:
            continue
        fila = len(filas)
        filas.append([Paragraph(titulo, st["seccion"]), "", "", "", ""])
        estilo += [("SPAN", (0, fila), (-1, fila)), ("BACKGROUND", (0, fila), (-1, fila), GRIS)]
        subtotal = 0.0
        for x in grupo:
            cant, precio = int(x["Cantidad"]), float(x["PrecioUnitario"])
            subtotal += cant * precio
            desc = escape(x["Nombre"] or "(sin nombre)")
            if x.get("Marca"):
                desc += f"<br/><font size='7' color='#6B7280'>{escape(x['Marca'])}</font>"
            filas.append([_p(x["Codigo"] or "-", st["n"]), Paragraph(desc, st["n"]), _p(cant, st["der"]),
                          _p(dinero(precio), st["der"]), _p(dinero(cant * precio), st["der"])])
            estilo.append(("LINEBELOW", (0, len(filas) - 1), (-1, len(filas) - 1), 0.4, BORDE))
        fila = len(filas)
        filas.append([Paragraph(f"Subtotal {titulo.split(' ')[0].lower()}", st["peq_der"]), "", "", "",
                      _p(dinero(subtotal), st["der_b"])])
        estilo.append(("SPAN", (0, fila), (3, fila)))

    if len(filas) == 1:
        filas.append([Paragraph("Esta factura no tiene líneas de detalle.", st["peq"]), "", "", "", ""])
        estilo.append(("SPAN", (0, 1), (-1, 1)))
    t = Table(filas, colWidths=anchos, repeatRows=1)
    t.setStyle(TableStyle(estilo))
    return t


def _tabla_totales(st, f):
    sub, desc = float(f["Subtotal"]), float(f["MontoDescuento"])
    iva, total = float(f["MontoIVA"]), float(f["Total"])
    base = sub - desc
    pct_iva = round(iva / base * 100) if base > 0 else 0
    filas = [[_p("Subtotal", st["n"]), _p(dinero(sub), st["der"])]]
    estilo = [("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
              ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
              ("LINEBELOW", (0, 0), (-1, -2), 0.4, BORDE)]
    if desc > 0:
        pct = float(f.get("PorcentajeDescuento") or 0) or round(desc / sub * 100)
        filas.append([_p(f"Descuento cliente frecuente ({pct:g}%)", st["n"]), _p("-" + dinero(desc), st["der"])])
    filas.append([_p(f"IVA ({pct_iva}%)", st["n"]), _p(dinero(iva), st["der"])])
    fila_total = len(filas)
    blanco_b = ParagraphStyle("tt", parent=st["n"], fontName="Helvetica-Bold", fontSize=11, textColor=colors.white)
    blanco_der = ParagraphStyle("td", parent=blanco_b, alignment=TA_RIGHT)
    filas.append([Paragraph("TOTAL", blanco_b), Paragraph(escape(dinero(total)), blanco_der)])
    estilo += [("BACKGROUND", (0, fila_total), (-1, fila_total), AZUL),
               ("TOPPADDING", (0, fila_total), (-1, fila_total), 6), ("BOTTOMPADDING", (0, fila_total), (-1, fila_total), 6)]
    t = Table(filas, colWidths=[6.2 * cm, 3.0 * cm], hAlign="RIGHT")
    t.setStyle(TableStyle(estilo))
    return t


def _estilo_tabla_simple(extra=()):
    return TableStyle([("BACKGROUND", (0, 0), (-1, 0), AZUL), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                       ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                       ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                       ("LINEBELOW", (0, 1), (-1, -1), 0.4, BORDE), *extra])


# ---------------------------------------------------------------------- factura individual
def generar_factura_pdf(ruta, factura, cliente, vehiculo, lineas):
    """Factura de UNA venta: cliente, vehículo (auto o moto), servicios, repuestos y totales."""
    st = _estilos()
    numero = str(factura["NumeroFactura"])
    estado = factura.get("Estado") or "Completada"
    story = [_cabecera(st, numero, [f"Fecha: {_fecha(factura['Fecha'], True)}", f"Estado: {escape(estado)}"]),
             Spacer(1, 12),
             _dos_cajas(st, "DATOS DEL CLIENTE", _filas_cliente(cliente),
                        "VEHÍCULO ATENDIDO", _filas_vehiculo(vehiculo)),
             Spacer(1, 14)]
    if estado != "Completada":
        story += [Paragraph(f"FACTURA {escape(estado.upper())}", st["alerta"]), Spacer(1, 8)]
    story += [_tabla_lineas(st, lineas), Spacer(1, 10),
              KeepTogether([_tabla_totales(st, factura), Spacer(1, 26),
                            Paragraph("Gracias por su preferencia.", st["gracias"])])]
    nombre = cliente["nombre"] if cliente else ""
    return _construir(ruta, story, f"{numero} - {nombre}", _pie())


# ---------------------------------------------------------------------- historial del cliente
def generar_historial_pdf(ruta, historial):
    """Historial completo: vehículos, resumen de facturas, detalle de cada factura y órdenes de servicio.
    'historial' es el diccionario que devuelve core.reportes_datos.historial_cliente()."""
    st = _estilos()
    c, vehiculos = historial["cliente"], historial["vehiculos"]
    facturas, ordenes = historial["facturas"], historial["ordenes"]
    validas = [f for f in facturas if f["Estado"] == "Completada"]

    total_fact = sum(float(f["Total"]) for f in validas)
    total_desc = sum(float(f["MontoDescuento"]) for f in validas)
    resumen = [("Facturas emitidas", len(validas)), ("Total facturado", dinero(total_fact)),
               ("Descuentos otorgados", dinero(total_desc)), ("Visitas registradas", c.get("visitas")),
               ("Primera factura", _fecha(validas[-1]["Fecha"]) if validas else None),
               ("Última factura", _fecha(validas[0]["Fecha"]) if validas else None)]

    story = [_cabecera(st, "HISTORIAL DE FACTURACIÓN", [f"<b>{escape(c['nombre'])}</b>",
                                                        f"Generado: {datetime.now():%d/%m/%Y %H:%M}"]),
             Spacer(1, 12), _dos_cajas(st, "DATOS DEL CLIENTE", _filas_cliente(c), "RESUMEN", resumen)]

    # vehículos (autos y motos)
    story.append(Paragraph("Vehículos registrados", st["h2"]))
    if vehiculos:
        anchos = [1.6 * cm, 2.4 * cm, 5.0 * cm, 2.3 * cm, 2.3 * cm]
        anchos.append(ANCHO - sum(anchos))
        filas = [[Paragraph(t, st["th"]) for t in ["Tipo", "Placa", "Vehículo", "Color", "Km", "Características"]]]
        for v in vehiculos:
            km = f"{int(v['kilometraje']):,}" if v.get("kilometraje") is not None else ""
            filas.append([_p(v["tipo"], st["n"]), _p(v["placa"], st["n"]),
                          _p(f"{v['marca']} {v['modelo']} {v['anio']}", st["n"]), _p(v.get("color") or "", st["n"]),
                          _p(km, st["n"]), _p(_detalle_vehiculo(v), st["n"])])
        t = Table(filas, colWidths=anchos, repeatRows=1)
        t.setStyle(_estilo_tabla_simple())
        story.append(t)
    else:
        story.append(Paragraph("El cliente no tiene vehículos registrados.", st["peq"]))

    # resumen de facturas
    story.append(Paragraph("Resumen de facturas", st["h2"]))
    if facturas:
        anchos = [3.2 * cm, 2.4 * cm, 2.4 * cm, 2.4 * cm, 2.2 * cm, 2.4 * cm]
        anchos.append(ANCHO - sum(anchos))
        filas = [[Paragraph(t, st["th_der" if 2 <= i <= 5 else "th"])
                  for i, t in enumerate(["Factura", "Fecha", "Subtotal", "Descuento", "IVA", "Total", "Estado"])]]
        for f in facturas:
            filas.append([_p(f["NumeroFactura"], st["n"]), _p(_fecha(f["Fecha"]), st["n"]),
                          _p(dinero(f["Subtotal"]), st["der"]), _p(dinero(f["MontoDescuento"]), st["der"]),
                          _p(dinero(f["MontoIVA"]), st["der"]), _p(dinero(f["Total"]), st["der"]),
                          _p(f["Estado"], st["n"])])
        filas.append([_p("TOTAL (completadas)", st["n"]), "", "",
                      _p(dinero(total_desc), st["der_b"]),
                      _p(dinero(sum(float(f["MontoIVA"]) for f in validas)), st["der_b"]),
                      _p(dinero(total_fact), st["der_b"]), ""])
        ultima = len(filas) - 1
        t = Table(filas, colWidths=anchos, repeatRows=1)
        t.setStyle(_estilo_tabla_simple([("SPAN", (0, ultima), (2, ultima)), ("BACKGROUND", (0, ultima), (-1, ultima), AZUL_CLARO)]))
        story.append(t)

        # detalle de cada factura (todos los servicios y repuestos)
        for i, f in enumerate(facturas):
            encabezado = Paragraph(f"<b>{escape(f['NumeroFactura'])}</b> · {_fecha(f['Fecha'], True)}"
                                   + ("" if f["Estado"] == "Completada" else f" · <font color='#B42318'>{escape(f['Estado'])}</font>"),
                                   ParagraphStyle("fh", parent=st["n"], fontSize=9.5, textColor=AZUL, spaceBefore=8,
                                                  spaceAfter=3, keepWithNext=1))
            bloque = [encabezado, _tabla_lineas(st, f["lineas"]), Spacer(1, 4), _tabla_totales(st, f), Spacer(1, 6)]
            if i == 0:      # el título de la sección viaja junto a la primera factura (nunca queda solo)
                bloque.insert(0, Paragraph("Detalle de cada factura", st["h2"]))
            if len(f["lineas"]) <= 8:
                story.append(KeepTogether(bloque))
            else:           # factura larga: puede partirse entre páginas, pero su título no queda solo
                story += [CondPageBreak(5 * cm)] + bloque
    else:
        story.append(Paragraph("El cliente todavía no tiene facturas.", st["peq"]))

    # órdenes de servicio
    story.append(Paragraph("Órdenes de servicio", st["h2"]))
    if ordenes:
        anchos = [2.2 * cm, 2.2 * cm, 4.2 * cm, 2.3 * cm]
        anchos.append(ANCHO - sum(anchos))
        filas = [[Paragraph(t, st["th"]) for t in ["Orden", "Fecha", "Vehículo", "Estado", "Servicios asignados"]]]
        for o in ordenes:
            servicios = "<br/>".join(f"• {escape(s['nombre'])} ({dinero(s['precio'])})" for s in o["servicios"]) \
                or "<font color='#6B7280'>Sin servicios asignados</font>"
            filas.append([_p(o["codigo_orden"], st["n"]), _p(_fecha(o["fecha_registro"]), st["n"]),
                          _p(f"{o['tipo']} {o['marca']} {o['modelo']} ({o['placa']})", st["n"]),
                          _p(o["estado"], st["n"]), Paragraph(servicios, st["n"])])
        t = Table(filas, colWidths=anchos, repeatRows=1)
        t.setStyle(_estilo_tabla_simple([("VALIGN", (0, 1), (-1, -1), "TOP")]))
        story.append(t)
    else:
        story.append(Paragraph("El cliente no tiene órdenes de servicio.", st["peq"]))

    story += [Spacer(1, 20), Paragraph("Las facturas anuladas se listan pero no suman en los totales.", st["gracias"])]
    return _construir(ruta, story, f"Historial - {c['nombre']}", _pie())