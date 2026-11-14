"""Módulo Reportes: indicadores, gráficas y PDF de facturación.

Pestañas: Resumen | Piezas más usadas | Ventas | Servicios y taller | Clientes y facturas (PDF).
Las consultas están en core/reportes_datos.py y los PDF en core/pdf_facturas.py.
Solo cuentan las facturas 'Completada'. Las ganancias son ESTIMADAS (usan el costo actual del repuesto).
"""
import os
import re
import subprocess
import sys
import traceback
import unicodedata
import tkinter as tk
from tkinter import filedialog, messagebox

import ttkbootstrap as ttk

from core import reportes_datos as rd
from core.reportes_datos import dinero

try:                                    # si falta matplotlib, el resto de Reportes sigue funcionando
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    from matplotlib.ticker import FuncFormatter, MaxNLocator
    HAY_GRAFICAS = True
except Exception:                       # pragma: no cover
    HAY_GRAFICAS = False

SIN_VEHICULO = "(No especificar vehículo)"


# ---------------------------------------------------------------------- utilidades
def _paleta():
    """Colores del tema de la app, para que las gráficas combinen con la interfaz."""
    try:
        c = ttk.Style().colors
        return {"bg": c.bg, "fg": c.fg, "primary": c.primary, "success": c.success, "info": c.info,
                "warning": c.warning, "danger": c.danger, "borde": c.border, "suave": c.secondary}
    except Exception:
        return {"bg": "#222222", "fg": "#ffffff", "primary": "#375a7f", "success": "#00bc8c", "info": "#3498db",
                "warning": "#f39c12", "danger": "#e74c3c", "borde": "#444444", "suave": "#888888"}


def _mt(texto):
    """matplotlib interpreta $...$ como fórmula: se escapa para que los precios se vean normales."""
    return str(texto).replace("$", r"\$")


def _cortar(texto, n=28):
    texto = str(texto)
    return texto if len(texto) <= n else texto[:n - 1] + "…"


def _fecha_corta(valor, con_hora=False):
    try:
        return valor.strftime("%d/%m/%Y %H:%M" if con_hora else "%d/%m/%Y")
    except Exception:
        return str(valor or "")


def _carpeta_inicial():
    for c in ("~/Documents", "~/Documentos", "~"):
        ruta = os.path.expanduser(c)
        if os.path.isdir(ruta):
            return ruta
    return os.getcwd()


def _nombre_archivo(*partes):
    texto = " ".join(str(p) for p in partes if p)
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "_", texto).strip("_") + ".pdf"


def _abrir(ruta):
    try:
        if sys.platform.startswith("win"):
            os.startfile(ruta)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", ruta])
        else:
            subprocess.Popen(["xdg-open", ruta])
    except Exception:
        messagebox.showinfo("PDF", f"No se pudo abrir automáticamente. Búsquelo en:\n{ruta}")


def _guardar_pdf(parent, sugerido, generar):
    """Pide dónde guardar, genera el PDF con generar(ruta) y ofrece abrirlo."""
    ruta = filedialog.asksaveasfilename(parent=parent, title="Guardar PDF", defaultextension=".pdf",
                                        filetypes=[("Archivo PDF", "*.pdf")], initialfile=sugerido,
                                        initialdir=_carpeta_inicial())
    if not ruta:
        return
    try:
        generar(ruta)
    except PermissionError:
        messagebox.showerror("No se pudo guardar", "No se puede escribir ese archivo. Si ya lo tiene abierto en "
                             "otro programa, ciérrelo e intente de nuevo.", parent=parent)
        return
    except ImportError:
        messagebox.showerror("Falta una librería", "Instale reportlab con:  pip install reportlab", parent=parent)
        return
    except Exception as e:
        traceback.print_exc()
        messagebox.showerror("Error", f"No se pudo generar el PDF:\n{e}", parent=parent)
        return
    if messagebox.askyesno("PDF generado", f"Se guardó en:\n{ruta}\n\n¿Abrirlo ahora?", parent=parent):
        _abrir(ruta)


def exportar_factura(parent, factura_id, vehiculo_id="auto"):
    """PDF de una factura. vehiculo_id: 'auto' = el de la última orden del cliente, None = sin vehículo."""
    try:
        datos = rd.datos_factura(factura_id)
        if not datos:
            messagebox.showwarning("Factura", "No se encontró la factura.", parent=parent)
            return
        factura, cli, lineas = datos
        if vehiculo_id == "auto":
            vehiculo_id = rd.vehiculo_sugerido(factura["id_cliente"])
        veh = rd.vehiculo(vehiculo_id) if vehiculo_id else None
    except Exception as e:
        traceback.print_exc()
        messagebox.showerror("Error", f"No se pudo leer la factura:\n{e}", parent=parent)
        return

    def generar(ruta):
        from core import pdf_facturas
        pdf_facturas.generar_factura_pdf(ruta, factura, cli, veh, lineas)

    _guardar_pdf(parent, _nombre_archivo(factura["NumeroFactura"], cli["nombre"] if cli else ""), generar)


def exportar_historial(parent, id_cliente):
    """PDF con todas las facturas, vehículos y órdenes de un cliente."""
    try:
        historial = rd.historial_cliente(id_cliente)
        if not historial["cliente"]:
            messagebox.showwarning("Cliente", "No se encontró el cliente.", parent=parent)
            return
    except Exception as e:
        traceback.print_exc()
        messagebox.showerror("Error", f"No se pudo leer el historial:\n{e}", parent=parent)
        return

    def generar(ruta):
        from core import pdf_facturas
        pdf_facturas.generar_historial_pdf(ruta, historial)

    _guardar_pdf(parent, _nombre_archivo("Historial", historial["cliente"]["nombre"]), generar)


# ---------------------------------------------------------------------- gráfica
class Grafica(ttk.Frame):
    """Figura de matplotlib con los colores del tema."""

    def __init__(self, master):
        super().__init__(master)
        self.p = _paleta()
        self.fig = None
        if HAY_GRAFICAS:
            self.fig = Figure(figsize=(3.6, 3.6), facecolor=self.p["bg"], layout="constrained")
            self.canvas = FigureCanvasTkAgg(self.fig, master=self)
            self.canvas.get_tk_widget().configure(highlightthickness=0, background=self.p["bg"])
            self.canvas.get_tk_widget().pack(fill="both", expand=True)
        else:
            ttk.Label(self, text="Para ver las gráficas instale matplotlib:\npip install matplotlib",
                      justify="center").pack(expand=True)

    @property
    def disponible(self):
        return self.fig is not None

    def nueva(self, filas=1, alturas=None):
        """Limpia la figura y devuelve una lista con los ejes (uno por fila)."""
        self.fig.clear()
        grilla = self.fig.add_gridspec(filas, 1, height_ratios=alturas)
        ejes = [self.fig.add_subplot(grilla[i]) for i in range(filas)]
        for ax in ejes:
            ax.set_facecolor(self.p["bg"])
            for lado, borde in ax.spines.items():
                borde.set_color(self.p["borde"])
                borde.set_visible(lado in ("left", "bottom"))
            ax.tick_params(colors=self.p["fg"], labelsize=8.5)
        return ejes

    def terminar(self):
        self.canvas.draw_idle()

    def sin_datos(self, ax, texto="Sin datos en este período"):
        ax.set_axis_off()
        ax.text(0.5, 0.5, texto, ha="center", va="center", color=self.p["suave"], fontsize=11,
                transform=ax.transAxes)

    def _titulo(self, ax, titulo):
        ax.set_title(_mt(titulo), fontsize=10.5, loc="left", color=self.p["fg"], pad=8)

    def _rejilla(self, ax, eje):
        ax.grid(axis=eje, color=self.p["borde"], alpha=0.45, linewidth=0.6)
        ax.set_axisbelow(True)

    def barras_h(self, ax, etiquetas, valores, color, titulo, fmt=str):
        """Barras horizontales; la primera etiqueta queda arriba."""
        pos = list(range(len(valores)))
        barras = ax.barh(pos, valores, color=color, height=0.65)
        ax.set_yticks(pos)
        ax.set_yticklabels([_mt(_cortar(e)) for e in etiquetas])
        ax.invert_yaxis()
        ax.bar_label(barras, labels=[_mt(fmt(v)) for v in valores], padding=3, color=self.p["fg"], fontsize=8.5)
        ax.set_xlim(0, max(valores) * 1.2 if max(valores) > 0 else 1)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        self._rejilla(ax, "x")
        self._titulo(ax, titulo)

    def barras_v(self, ax, etiquetas, valores, color, titulo):
        """Barras verticales con valores en dólares (ventas por día o mes)."""
        n = len(valores)
        pos = list(range(n))
        barras = ax.bar(pos, valores, color=color, width=0.7)
        paso = max(1, -(-n // 12))
        ax.set_xticks(pos[::paso])
        ax.set_xticklabels([etiquetas[i] for i in pos[::paso]], rotation=45 if n > 8 else 0,
                           ha="right" if n > 8 else "center")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: _mt(f"${v:,.0f}")))
        if n <= 12:
            ax.bar_label(barras, labels=[_mt(dinero(v)) if v > 0 else "" for v in valores], padding=3,
                         color=self.p["fg"], fontsize=8)
            ax.set_ylim(0, max(valores) * 1.18 if max(valores) > 0 else 1)
        self._rejilla(ax, "y")
        self._titulo(ax, titulo)


# ---------------------------------------------------------------------- base: filtros + gráfica + tabla
class PestanaGrafica(ttk.Frame):
    COLUMNAS = ()       # (clave, título, ancho, ancla)

    def __init__(self, master, periodo_inicial="Últimos 30 días", con_top=False):
        super().__init__(master, padding=(0, 10, 0, 0))
        barra = ttk.Frame(self)
        barra.pack(fill="x")
        ttk.Label(barra, text="Período:").pack(side="left", padx=(0, 5))
        self.combo_periodo = ttk.Combobox(barra, values=rd.PERIODOS, state="readonly", width=16)
        self.combo_periodo.set(periodo_inicial)
        self.combo_periodo.pack(side="left", padx=(0, 15))
        self.combo_periodo.bind("<<ComboboxSelected>>", lambda e: self.refrescar())
        self.combo_top = None
        if con_top:
            ttk.Label(barra, text="Mostrar los:").pack(side="left", padx=(0, 5))
            self.combo_top = ttk.Combobox(barra, values=[5, 10, 15, 20], state="readonly", width=4)
            self.combo_top.set(10)
            self.combo_top.pack(side="left")
            self.combo_top.bind("<<ComboboxSelected>>", lambda e: self.refrescar())

        self.lbl_info = ttk.Label(self, text="", font=("", 10, "bold"))
        self.lbl_info.pack(anchor="w", pady=(10, 6))

        cuerpo = ttk.Frame(self)
        cuerpo.pack(fill="both", expand=True)
        cuerpo.rowconfigure(0, weight=1)
        cuerpo.columnconfigure(0, weight=3)
        cuerpo.columnconfigure(1, weight=2, minsize=340)
        self.grafica = Grafica(cuerpo)
        self.grafica.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        zona = ttk.Frame(cuerpo)
        zona.grid(row=0, column=1, sticky="nsew")
        self.tabla = ttk.Treeview(zona, columns=[c[0] for c in self.COLUMNAS], show="headings", selectmode="browse")
        for clave, titulo, ancho, ancla in self.COLUMNAS:
            self.tabla.heading(clave, text=titulo)
            self.tabla.column(clave, width=ancho, anchor=ancla, stretch=(ancla == "w"), minwidth=40)
        sb = ttk.Scrollbar(zona, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tabla.pack(side="left", fill="both", expand=True)

    def desde(self):
        return rd.desde_periodo(self.combo_periodo.get())

    def top(self):
        return int(self.combo_top.get()) if self.combo_top else None

    def llenar_tabla(self, filas):
        self.tabla.delete(*self.tabla.get_children())
        for f in filas:
            self.tabla.insert("", tk.END, values=f)


class PestanaPiezas(PestanaGrafica):
    COLUMNAS = (("n", "#", 28, "center"), ("nombre", "Repuesto", 130, "w"), ("cant", "Cant.", 46, "center"),
                ("ingresos", "Ingresos", 74, "e"), ("ganancia", "Ganancia", 74, "e"))

    def __init__(self, master):
        super().__init__(master, con_top=True)

    def refrescar(self):
        datos = rd.piezas_mas_usadas(self.desde())
        top = datos[:self.top()]
        self.lbl_info.config(text=(
            f"Repuestos distintos: {len(datos)}   |   Unidades vendidas: {sum(d['cantidad'] for d in datos)}   |   "
            f"Ingresos: {dinero(sum(d['ingresos'] for d in datos))}   |   "
            f"Ganancia estimada: {dinero(sum(d['ganancia'] for d in datos))}"))
        self.llenar_tabla([(i, d["nombre"], d["cantidad"], dinero(d["ingresos"]), dinero(d["ganancia"]))
                           for i, d in enumerate(top, start=1)])
        if not self.grafica.disponible:
            return
        (ax,) = self.grafica.nueva()
        if top:
            self.grafica.barras_h(ax, [d["nombre"] for d in top], [d["cantidad"] for d in top],
                                  self.grafica.p["info"], "Piezas más utilizadas (unidades)")
        else:
            self.grafica.sin_datos(ax, "Todavía no hay repuestos vendidos en este período")
        self.grafica.terminar()


class PestanaVentas(PestanaGrafica):
    COLUMNAS = (("periodo", "Período", 90, "w"), ("facturas", "Facturas", 72, "center"), ("total", "Total", 95, "e"))

    def refrescar(self):
        r = rd.ventas_resumen(self.desde())
        t = r["totales"]
        self.lbl_info.config(text=(f"Facturas: {t['facturas']}   |   Total vendido: {dinero(t['total'])}   |   "
                                   f"Ticket promedio: {dinero(t['ticket'])}   |   Descuentos: {dinero(t['descuento'])}   |   "
                                   f"IVA cobrado: {dinero(t['iva'])}"))
        serie = r["serie"]
        self.llenar_tabla([(s["etiqueta"], s["facturas"], dinero(s["total"])) for s in reversed(serie) if s["facturas"]])
        if not self.grafica.disponible:
            return
        (ax,) = self.grafica.nueva()
        if t["facturas"]:
            titulo = "Ventas por " + ("día" if r["por"] == "dia" else "mes") + " (con IVA)"
            self.grafica.barras_v(ax, [s["etiqueta"] for s in serie], [s["total"] for s in serie],
                                  self.grafica.p["success"], titulo)
        else:
            self.grafica.sin_datos(ax, "No hay ventas en este período")
        self.grafica.terminar()


class PestanaTaller(PestanaGrafica):
    COLUMNAS = (("servicio", "Servicio", 130, "w"), ("ordenes", "Órdenes", 72, "center"),
                ("facturado", "Facturado", 84, "center"), ("ingresos", "Ingresos", 78, "e"))

    def refrescar(self):
        desde = self.desde()
        datos = rd.servicios_resumen(desde)
        estados = rd.ordenes_por_estado(desde)
        veh = rd.vehiculos_por_tipo()
        self.lbl_info.config(text=("Órdenes: " + "  ·  ".join(f"{e} {n}" for e, n in estados.items())
                                   + f"   |   Vehículos registrados: {veh['Auto']} autos  ·  {veh['Moto']} motos"))
        self.llenar_tabla([(d["nombre"], d["ordenes"], d["facturado"], dinero(d["ingresos"])) for d in datos])
        if not self.grafica.disponible:
            return
        p = self.grafica.p
        arriba, abajo = self.grafica.nueva(2, [3, 2])
        if datos:
            top = datos[:8]
            pos, h = list(range(len(top))), 0.38
            arriba.barh([i - h / 2 for i in pos], [d["ordenes"] for d in top], height=h, color=p["info"],
                        label="En órdenes")
            arriba.barh([i + h / 2 for i in pos], [d["facturado"] for d in top], height=h, color=p["success"],
                        label="Facturados")
            arriba.set_yticks(pos)
            arriba.set_yticklabels([_mt(_cortar(d["nombre"], 30)) for d in top])
            arriba.invert_yaxis()
            arriba.xaxis.set_major_locator(MaxNLocator(integer=True))
            arriba.legend(facecolor=p["bg"], edgecolor=p["borde"], labelcolor=p["fg"], fontsize=8, loc="lower right")
            self.grafica._rejilla(arriba, "x")
            self.grafica._titulo(arriba, "Servicios más solicitados")
        else:
            self.grafica.sin_datos(arriba, "Sin servicios en este período")
        colores = [p["info"], p["warning"], p["suave"], p["success"]]
        etiquetas, valores = list(estados.keys()), list(estados.values())
        if sum(valores):
            barras = abajo.barh(list(range(4)), valores, color=colores, height=0.6)
            abajo.set_yticks(list(range(4)))
            abajo.set_yticklabels(etiquetas)
            abajo.invert_yaxis()
            abajo.bar_label(barras, padding=3, color=p["fg"], fontsize=8.5)
            abajo.set_xlim(0, max(valores) * 1.25)
            abajo.xaxis.set_major_locator(MaxNLocator(integer=True))
            self.grafica._rejilla(abajo, "x")
            self.grafica._titulo(abajo, "Órdenes por estado")
        else:
            self.grafica.sin_datos(abajo, "Sin órdenes en este período")
        self.grafica.terminar()


# ---------------------------------------------------------------------- resumen
class PestanaResumen(ttk.Frame):
    def __init__(self, master, abrir_factura):
        super().__init__(master, padding=(0, 12, 0, 0))
        self.abrir_factura = abrir_factura
        p = _paleta()
        definiciones = [("ventas_hoy", "Ventas de hoy", p["success"]), ("ventas_mes", "Ventas del mes", p["success"]),
                        ("ticket_mes", "Ticket promedio (mes)", p["info"]),
                        ("ganancia", "Ganancia en repuestos (mes)", p["success"]),
                        ("ordenes_activas", "Órdenes activas", p["warning"]),
                        ("clientes", "Clientes registrados", p["info"]),
                        ("stock_bajo", "Repuestos con stock bajo", p["danger"]),
                        ("facturas_mes", "Facturas del mes", p["fg"])]
        rejilla = ttk.Frame(self)
        rejilla.pack(fill="x")
        self.valores, self.notas = {}, {}
        for i, (clave, titulo, color) in enumerate(definiciones):
            rejilla.columnconfigure(i % 4, weight=1, uniform="tarjeta")
            tarjeta = ttk.Frame(rejilla, padding=12, bootstyle="secondary")
            tarjeta.grid(row=i // 4, column=i % 4, sticky="nsew", padx=4, pady=4)
            ttk.Label(tarjeta, text=titulo, font=("", 9), bootstyle="inverse-secondary").pack(anchor="w")
            self.valores[clave] = ttk.Label(tarjeta, text="-", font=("", 18, "bold"), bootstyle="inverse-secondary")
            self.valores[clave].configure(foreground=color)
            self.valores[clave].pack(anchor="w", pady=(2, 0))
            self.notas[clave] = ttk.Label(tarjeta, text=" ", font=("", 8), bootstyle="inverse-secondary")
            self.notas[clave].pack(anchor="w")

        ttk.Label(self, text="Últimas facturas", font=("", 12, "bold")).pack(anchor="w", pady=(14, 4))
        cols = (("numero", "Factura", 280, "w"), ("fecha", "Fecha", 380, "w"), ("cliente", "Cliente", 210, "w"),
                ("total", "Total", 290, "w"), ("estado", "Estado", 290, "w"))
        zona = ttk.Frame(self)
        zona.pack(fill="both", expand=True)
        self.tabla = ttk.Treeview(zona, columns=[c[0] for c in cols], show="headings", selectmode="browse", height=7)
        for clave, titulo, ancho, ancla in cols:
            self.tabla.heading(clave, text=titulo, anchor="w")
            self.tabla.column(clave, width=ancho, anchor=ancla, stretch=(clave == "cliente"), minwidth=50)
        sb = ttk.Scrollbar(zona, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tabla.pack(side="left", fill="both", expand=True)
        self.tabla.bind("<Double-1>", self._doble_clic)
        ttk.Label(self, text="Doble clic en una factura para generar su PDF.", font=("", 9, "italic"),
                  bootstyle="secondary").pack(anchor="w", pady=(6, 0))

    def refrescar(self):
        k = rd.kpis()
        self.valores["ventas_hoy"].config(text=dinero(k["ventas_hoy"]))
        self.notas["ventas_hoy"].config(text=f"{k['facturas_hoy']} factura(s)")
        self.valores["ventas_mes"].config(text=dinero(k["ventas_mes"]))
        self.notas["ventas_mes"].config(text=f"{k['facturas_mes']} factura(s)")
        self.valores["ticket_mes"].config(text=dinero(k["ticket_mes"]))
        self.notas["ticket_mes"].config(text="promedio por factura")
        self.valores["ganancia"].config(text=dinero(k["ganancia_repuestos_mes"]))
        self.notas["ganancia"].config(text="venta menos costo (estimada)")
        self.valores["ordenes_activas"].config(text=str(k["ordenes_activas"]))
        self.notas["ordenes_activas"].config(text="registradas o en proceso")
        self.valores["clientes"].config(text=str(k["clientes"]))
        self.valores["stock_bajo"].config(text=str(k["stock_bajo"]))
        self.notas["stock_bajo"].config(text="ver pantalla Inventario")
        self.valores["facturas_mes"].config(text=str(k["facturas_mes"]))
        self.notas["facturas_mes"].config(text="completadas")
        self.notas["clientes"].config(text="en el sistema")

        self.tabla.delete(*self.tabla.get_children())
        for f in rd.ultimas_facturas(8):
            self.tabla.insert("", tk.END, iid=str(f["FacturaID"]), values=(
                f["NumeroFactura"], _fecha_corta(f["Fecha"], True), f["cliente"], dinero(f["Total"]), f["Estado"]))

    def _doble_clic(self, event):
        fila = self.tabla.identify_row(event.y)
        if fila:
            self.abrir_factura(int(fila))


# ---------------------------------------------------------------------- clientes y PDF
class PestanaClientes(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=(0, 10, 0, 0))
        self._pendiente = None
        self.id_cliente = None
        self._vehiculos = {}          # texto del desplegable -> id_vehiculo (None = sin vehículo)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # ---- izquierda: lista de clientes
        izq = ttk.Frame(self)
        izq.grid(row=0, column=0, sticky="ns", padx=(0, 14))
        ttk.Label(izq, text="Buscar (nombre, código, DUI, tel.):", font=("", 9)).pack(anchor="w")
        self.var_buscar = tk.StringVar()
        ttk.Entry(izq, textvariable=self.var_buscar).pack(fill="x", pady=(3, 6))
        self.var_buscar.trace_add("write", lambda *a: self._buscar_con_pausa())
        cols = (("nombre", "Cliente", 150, "w"), ("facturas", "Fact.", 42, "center"), ("total", "Total", 82, "e"))
        zona = ttk.Frame(izq)
        zona.pack(fill="both", expand=True)
        self.tabla_clientes = ttk.Treeview(zona, columns=[c[0] for c in cols], show="headings", selectmode="browse")
        for clave, titulo, ancho, ancla in cols:
            self.tabla_clientes.heading(clave, text=titulo)
            self.tabla_clientes.column(clave, width=ancho, anchor=ancla, stretch=False)
        sb = ttk.Scrollbar(zona, orient="vertical", command=self.tabla_clientes.yview)
        self.tabla_clientes.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tabla_clientes.pack(side="left", fill="both", expand=True)
        self.tabla_clientes.bind("<<TreeviewSelect>>", self._al_elegir_cliente)
        ttk.Label(izq, text="Ordenados por lo que más han gastado.", font=("", 8, "italic"),
                  bootstyle="secondary").pack(anchor="w", pady=(4, 0))

        # ---- derecha: datos del cliente, facturas y botones de PDF
        der = ttk.Frame(self)
        der.grid(row=0, column=1, sticky="nsew")
        self.lbl_cliente = ttk.Label(der, text="Seleccione un cliente de la lista", font=("", 13, "bold"))
        self.lbl_cliente.pack(anchor="w")
        self.lbl_detalle = ttk.Label(der, text="", justify="left", wraplength=500)
        self.lbl_detalle.pack(anchor="w", pady=(2, 8))

        ttk.Label(der, text="Facturas del cliente", font=("", 11, "bold")).pack(anchor="w")
        cols_f = (("numero", "Factura", 10, "w"), ("fecha", "Fecha", 230, "w"), ("subtotal", "Subtotal", 200, "w"),
                  ("total", "Total", 200, "w"), ("estado", "Estado", 230, "w"))
        zona_f = ttk.Frame(der)
        zona_f.pack(fill="both", expand=True, pady=(3, 8))
        self.tabla_facturas = ttk.Treeview(zona_f, columns=[c[0] for c in cols_f], show="headings",
                                           selectmode="browse", height=7)
        for clave, titulo, ancho, ancla in cols_f:
            self.tabla_facturas.heading(clave, text=titulo, anchor="w")
            self.tabla_facturas.column(clave, width=ancho, anchor=ancla, stretch=(clave == "numero"))
        sb2 = ttk.Scrollbar(zona_f, orient="vertical", command=self.tabla_facturas.yview)
        self.tabla_facturas.configure(yscrollcommand=sb2.set)
        sb2.pack(side="right", fill="y")
        self.tabla_facturas.pack(side="left", fill="both", expand=True)
        self.tabla_facturas.bind("<Double-1>", lambda e: self.pdf_factura() if self.tabla_facturas.identify_row(e.y) else None)

        fila_v = ttk.Frame(der)
        fila_v.pack(fill="x", pady=(0, 8))
        ttk.Label(fila_v, text="Vehículo en la factura:").pack(side="left", padx=(0, 6))
        self.combo_vehiculo = ttk.Combobox(fila_v, state="readonly", width=36)
        self.combo_vehiculo.pack(side="left")

        botones = ttk.Frame(der)
        botones.pack(fill="x")
        ttk.Button(botones, text="PDF de la factura", bootstyle="success",
                   command=self.pdf_factura).pack(side="left", padx=(0, 8))
        ttk.Button(botones, text="PDF historial del cliente", bootstyle="info",
                   command=self.pdf_historial).pack(side="left")
        ttk.Label(der, text="Sirve para autos y motos. La factura trae todos sus servicios y repuestos; el historial "
                            "trae todas las facturas, los vehículos y las órdenes de servicio.",
                  font=("", 8, "italic"), bootstyle="secondary", wraplength=500, justify="left").pack(anchor="w", pady=(8, 0))

    def refrescar(self):
        self._cargar_lista()
        if self.id_cliente is not None:
            iid = str(self.id_cliente)
            if self.tabla_clientes.exists(iid):
                self.tabla_clientes.selection_set(iid)
                self._mostrar_cliente(self.id_cliente)

    def _buscar_con_pausa(self):
        if self._pendiente:
            self.after_cancel(self._pendiente)
        self._pendiente = self.after(300, self._cargar_lista)

    def _cargar_lista(self):
        self._pendiente = None
        self.tabla_clientes.delete(*self.tabla_clientes.get_children())
        for c in rd.clientes_resumen(self.var_buscar.get()):
            self.tabla_clientes.insert("", tk.END, iid=str(c["id_cliente"]),
                                       values=(c["nombre"], c["facturas"], dinero(c["total"])))

    def _al_elegir_cliente(self, _evento=None):
        sel = self.tabla_clientes.selection()
        if sel:
            self._mostrar_cliente(int(sel[0]))

    def _mostrar_cliente(self, id_cliente):
        self.id_cliente = id_cliente
        c = rd.cliente(id_cliente)
        vehiculos = rd.vehiculos_de_cliente(id_cliente)
        facturas = rd.facturas_de_cliente(id_cliente)
        if not c:
            return
        self.lbl_cliente.config(text=f"{c['nombre']}  ({c['codigo']})")
        contacto = [f"Tel. {c['telefono']}"] + [x for x in (c.get("correo"), c.get("direccion")) if x]
        docs = " · ".join(x for x in (f"DUI {c['dui']}" if c.get("dui") else "", f"NIT {c['nit']}" if c.get("nit") else "") if x)
        autos = ", ".join(f"{v['tipo']} {v['marca']} {v['modelo']} ({v['placa']})" for v in vehiculos) or "ninguno"
        self.lbl_detalle.config(text=" · ".join(contacto) + (f"\n{docs}" if docs else "")
                                + f"\nVisitas: {c['visitas']}   |   Vehículos: {autos}")

        self.tabla_facturas.delete(*self.tabla_facturas.get_children())
        for f in facturas:
            self.tabla_facturas.insert("", tk.END, iid=str(f["FacturaID"]), values=(
                f["NumeroFactura"], _fecha_corta(f["Fecha"]), dinero(f["Subtotal"]), dinero(f["Total"]), f["Estado"]))
        if facturas:
            primera = str(facturas[0]["FacturaID"])
            self.tabla_facturas.selection_set(primera)

        self._vehiculos = {SIN_VEHICULO: None}
        for v in vehiculos:
            self._vehiculos[f"{v['tipo']} {v['marca']} {v['modelo']} {v['anio']} · {v['placa']}"] = v["id_vehiculo"]
        self.combo_vehiculo.config(values=list(self._vehiculos))
        sugerido = rd.vehiculo_sugerido(id_cliente)
        elegido = next((t for t, i in self._vehiculos.items() if i == sugerido and i is not None), SIN_VEHICULO)
        self.combo_vehiculo.set(elegido)

    def pdf_factura(self):
        if self.id_cliente is None:
            messagebox.showinfo("Reportes", "Primero elija un cliente de la lista.", parent=self.winfo_toplevel())
            return
        sel = self.tabla_facturas.selection()
        if not sel:
            messagebox.showinfo("Reportes", "Este cliente no tiene facturas. Seleccione otro cliente.",
                                parent=self.winfo_toplevel())
            return
        exportar_factura(self.winfo_toplevel(), int(sel[0]), self._vehiculos.get(self.combo_vehiculo.get()))

    def pdf_historial(self):
        if self.id_cliente is None:
            messagebox.showinfo("Reportes", "Primero elija un cliente de la lista.", parent=self.winfo_toplevel())
            return
        exportar_historial(self.winfo_toplevel(), self.id_cliente)


# ---------------------------------------------------------------------- pantalla
class ReportesFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=20)
        self._activo = False
        cabecera = ttk.Frame(self)
        cabecera.pack(fill="x")
        ttk.Label(cabecera, text="Reportes", font=("", 20, "bold")).pack(side="left")
        ttk.Button(cabecera, text="Actualizar", bootstyle="secondary-outline",
                   command=self._refrescar_actual).pack(side="right")

        self.libro = ttk.Notebook(self)
        self.libro.pack(fill="both", expand=True, pady=(10, 0))
        self.resumen = PestanaResumen(self.libro, lambda fid: exportar_factura(self.winfo_toplevel(), fid))
        self.piezas = PestanaPiezas(self.libro)
        self.ventas = PestanaVentas(self.libro)
        self.taller = PestanaTaller(self.libro)
        self.clientes = PestanaClientes(self.libro)
        for titulo, pestana in (("Resumen", self.resumen), ("Piezas más usadas", self.piezas), ("Ventas", self.ventas),
                                ("Servicios y taller", self.taller), ("Clientes y facturas (PDF)", self.clientes)):
            self.libro.add(pestana, text=titulo, padding=(12, 0, 12, 8))
        self.libro.bind("<<NotebookTabChanged>>", lambda e: self._refrescar_actual() if self._activo else None)

    def al_mostrar(self):
        """Se llama cada vez que se abre la pantalla: se recarga la pestaña visible."""
        self._activo = True
        self._refrescar_actual()

    def _refrescar_actual(self):
        pestana = self.nametowidget(self.libro.select())
        try:
            pestana.refrescar()
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Reportes", f"No se pudo cargar este reporte:\n{e}", parent=self.winfo_toplevel())