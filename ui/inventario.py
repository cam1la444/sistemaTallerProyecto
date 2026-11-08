"""Módulo Inventario: repuestos del taller (tabla Insumos).

Cada repuesto tiene dos precios:
- Costo        -> precio de COMPRA mayorista (lo que paga el taller al proveedor)
- PrecioVenta  -> precio FINAL al cliente (sin IVA; el IVA lo suma Ventas)

El stock se descuenta solo cuando Ventas cobra una factura (ver procesar_cobro en ui/ventas.py).
Solo edite SU archivo. main_window.py ya importa esta clase.
"""
import re
import tkinter as tk
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from tkinter import messagebox

import ttkbootstrap as ttk

from core.database import consultar, ejecutar, get_connection

COLOR_BAJO = "#f0ad4e"       # stock igual o menor al mínimo
COLOR_AGOTADO = "#e74c3c"    # stock en cero
MAX_DINERO = Decimal("99999999.99")      # límite de DECIMAL(10,2)
MAX_ENTERO = 1_000_000


# ---------------------------------------------------------------------- utilidades
def dinero(valor):
    """Formato $1,234.50"""
    return f"${float(valor):,.2f}"


def _escapar_like(texto):
    """Para que %, _ y [ escritos por el usuario se busquen tal cual (se usa con ESCAPE '\\')."""
    return re.sub(r"([\\%_\[])", r"\\\1", texto)


def leer_dinero(texto, campo):
    """Texto -> Decimal con 2 decimales (acepta '12.5', '12,50', '$1,234.50')."""
    t = (texto or "").strip().replace("$", "").replace(" ", "")
    if not t:
        raise ValueError(f"{campo} es obligatorio.")
    t = t.replace(",", "") if ("," in t and "." in t) else t.replace(",", ".")
    try:
        valor = Decimal(t)
    except InvalidOperation:
        raise ValueError(f"{campo} no es un número válido (ejemplo: 12.50).")
    if not valor.is_finite() or valor < 0:
        raise ValueError(f"{campo} no puede ser negativo.")
    if valor > MAX_DINERO:
        raise ValueError(f"{campo} es demasiado grande.")
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def leer_entero(texto, campo):
    t = (texto or "").strip()
    if not t:
        raise ValueError(f"{campo} es obligatorio.")
    if not (t.isascii() and t.isdigit()):
        raise ValueError(f"{campo} debe ser un número entero (0 o más).")
    n = int(t)
    if n > MAX_ENTERO:
        raise ValueError(f"{campo} es demasiado grande.")
    return n


# ---------------------------------------------------------------------- formulario
class FormularioProducto(ttk.Toplevel):
    """Ventana para agregar o editar un repuesto. 'producto' = None para agregar.
    al_guardar(datos, ventana) debe devolver True si se guardó (entonces la ventana se cierra)."""

    def __init__(self, master, producto, al_guardar):
        super().__init__(master)
        self.editando = producto is not None
        self.al_guardar = al_guardar
        self.title("Editar repuesto" if self.editando else "Agregar repuesto")
        self.resizable(False, False)
        self.transient(master)

        p = producto or {}
        self.v = {
            "codigo": tk.StringVar(value=p.get("Codigo", "")),
            "nombre": tk.StringVar(value=p.get("Nombre", "")),
            "marca": tk.StringVar(value=p.get("Marca") or ""),
            "costo": tk.StringVar(value=f"{p['Costo']:.2f}" if p else ""),
            "venta": tk.StringVar(value=f"{p['PrecioVenta']:.2f}" if p else ""),
            "stock": tk.StringVar(value=str(p["Stock"]) if p else "0"),
            "minimo": tk.StringVar(value=str(p["StockMinimo"]) if p else "5"),
        }

        cont = ttk.Frame(self, padding=18)
        cont.pack(fill="both", expand=True)
        ttk.Label(cont, text="Editar repuesto" if self.editando else "Nuevo repuesto",
                font=("", 14, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        filas = [
            ("Código *", "codigo"),
            ("Nombre *", "nombre"),
            ("Marca", "marca"),
            ("Precio de compra (mayorista) $ *", "costo"),
            ("Precio de venta (cliente) $ *", "venta"),
            ("Stock actual *", "stock"),
            ("Stock mínimo (alerta) *", "minimo"),
        ]
        self.entradas = {}
        for i, (texto, clave) in enumerate(filas, start=1):
            ttk.Label(cont, text=texto).grid(row=i, column=0, sticky="w", pady=4, padx=(0, 12))
            e = ttk.Entry(cont, textvariable=self.v[clave], width=34)
            e.grid(row=i, column=1, sticky="ew", pady=4)
            self.entradas[clave] = e
        if self.editando:                       # el código identifica al repuesto: no se cambia
            self.entradas["codigo"].config(state="disabled")

        self.lbl_ganancia = ttk.Label(cont, text="", font=("", 10, "bold"))
        self.lbl_ganancia.grid(row=len(filas) + 1, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.v["costo"].trace_add("write", lambda *a: self._actualizar_ganancia())
        self.v["venta"].trace_add("write", lambda *a: self._actualizar_ganancia())
        self._actualizar_ganancia()

        botones = ttk.Frame(cont)
        botones.grid(row=len(filas) + 2, column=0, columnspan=2, pady=(16, 0), sticky="e")
        ttk.Button(botones, text="Guardar", bootstyle="success", command=self._guardar).pack(side="left", padx=4)
        ttk.Button(botones, text="Cancelar", bootstyle="secondary", command=self.destroy).pack(side="left")

        self.bind("<Return>", lambda e: self._guardar())
        self.bind("<Escape>", lambda e: self.destroy())
        self.update_idletasks()
        self.grab_set()
        (self.entradas["nombre"] if self.editando else self.entradas["codigo"]).focus_set()

    def _actualizar_ganancia(self):
        """Muestra la ganancia por unidad mientras se escriben los precios."""
        try:
            costo = leer_dinero(self.v["costo"].get(), "Costo")
            venta = leer_dinero(self.v["venta"].get(), "Venta")
        except ValueError:
            self.lbl_ganancia.config(text="Ganancia por unidad: —", bootstyle="secondary")
            return
        g = venta - costo
        pct = f" ({g / costo * 100:.0f}% sobre el costo)" if costo > 0 else ""
        self.lbl_ganancia.config(text=f"Ganancia por unidad: {dinero(g)}{pct}",
                                bootstyle="success" if g >= 0 else "danger")

    def _guardar(self):
        try:
            codigo = self.v["codigo"].get().strip().upper()
            nombre = self.v["nombre"].get().strip()
            marca = self.v["marca"].get().strip() or None
            if not codigo:
                raise ValueError("El código es obligatorio.")
            if len(codigo) > 20 or re.search(r"\s", codigo):
                raise ValueError("El código no puede tener espacios ni más de 20 caracteres.")
            if not nombre:
                raise ValueError("El nombre es obligatorio.")
            if len(nombre) > 100:
                raise ValueError("El nombre admite máximo 100 caracteres.")
            if marca and len(marca) > 50:
                raise ValueError("La marca admite máximo 50 caracteres.")
            costo = leer_dinero(self.v["costo"].get(), "El precio de compra")
            venta = leer_dinero(self.v["venta"].get(), "El precio de venta")
            if venta <= 0:
                raise ValueError("El precio de venta debe ser mayor que 0.")
            stock = leer_entero(self.v["stock"].get(), "El stock")
            minimo = leer_entero(self.v["minimo"].get(), "El stock mínimo")
        except ValueError as e:
            messagebox.showwarning("Revise los datos", str(e), parent=self)
            return

        if venta < costo and not messagebox.askyesno(
                "Precio por debajo del costo",
                f"El precio de venta ({dinero(venta)}) es MENOR que el de compra ({dinero(costo)}).\n"
                "El taller perdería dinero en cada venta.\n\n¿Guardar de todas formas?", parent=self):
            return

        datos = {"codigo": codigo, "nombre": nombre, "marca": marca, "costo": costo,
                "venta": venta, "stock": stock, "minimo": minimo}
        if self.al_guardar(datos, self):
            self.destroy()


# ---------------------------------------------------------------------- pantalla
class InventarioFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=20)
        self._filas = {}             # InsumoID -> fila mostrada (para editar/eliminar)
        self._pendiente = None       # temporizador de la búsqueda

        ttk.Label(self, text="Inventario de repuestos", font=("", 20, "bold")).pack(anchor="w")
        ttk.Label(self, text="Compra = lo que paga el taller al proveedor (mayorista).  "
                            "Venta = precio final al cliente (sin IVA).",
                font=("", 9, "italic"), bootstyle="secondary").pack(anchor="w", pady=(2, 8))

        # resumen
        resumen = ttk.Frame(self)
        resumen.pack(fill="x", pady=(0, 10))
        self.lbl_total = ttk.Label(resumen, text="", font=("", 11))
        self.lbl_bajo = ttk.Label(resumen, text="", font=("", 11), foreground=COLOR_BAJO)
        self.lbl_agotado = ttk.Label(resumen, text="", font=("", 11), foreground=COLOR_AGOTADO)
        self.lbl_valor = ttk.Label(resumen, text="", font=("", 11))
        for lbl in (self.lbl_total, self.lbl_bajo, self.lbl_agotado, self.lbl_valor):
            lbl.pack(side="left", padx=(0, 22))

        # barra de herramientas (los botones se empaquetan primero para que nunca se encojan)
        barra = ttk.Frame(self)
        barra.pack(fill="x", pady=(0, 8))
        ttk.Button(barra, text="Eliminar", bootstyle="danger-outline",
                command=self.eliminar).pack(side="right")
        ttk.Button(barra, text="Editar", bootstyle="info-outline",
                command=self.editar).pack(side="right", padx=6)
        ttk.Button(barra, text="+ Agregar repuesto", bootstyle="success",
                command=self.agregar).pack(side="right")
        ttk.Label(barra, text="Buscar:").pack(side="left", padx=(0, 5))
        self.var_buscar = tk.StringVar()
        ttk.Entry(barra, textvariable=self.var_buscar, width=22).pack(side="left", padx=(0, 12))
        self.var_buscar.trace_add("write", lambda *a: self._buscar_con_pausa())
        self.var_solo_bajo = tk.BooleanVar(value=False)
        ttk.Checkbutton(barra, text="Solo stock bajo", variable=self.var_solo_bajo,
                        bootstyle="round-toggle", command=self.cargar).pack(side="left")

        # tabla
        cols = ("codigo", "nombre", "marca", "costo", "venta", "stock", "minimo", "estado")
        zona = ttk.Frame(self)
        zona.pack(fill="both", expand=True)
        self.tabla = ttk.Treeview(zona, columns=cols, show="headings", selectmode="browse")
        encabezados = [("codigo", "Código", 75, "center"), ("nombre", "Repuesto", 100, "w"),
                    ("marca", "Marca", 75, "w"), ("costo", "Compra mayorista", 140, "e"),
                    ("venta", "Venta cliente", 105, "e"), ("stock", "Stock", 55, "center"),
                    ("minimo", "Mínimo", 70, "center"), ("estado", "Estado", 65, "center")]
        for clave, texto, ancho, ancla in encabezados:
            self.tabla.heading(clave, text=texto)
            self.tabla.column(clave, width=ancho, anchor=ancla, stretch=(clave == "nombre"),
                            minwidth=100 if clave == "nombre" else 45)
        sb = ttk.Scrollbar(zona, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tabla.pack(side="left", fill="both", expand=True)
        self.tabla.tag_configure("bajo", foreground=COLOR_BAJO)
        self.tabla.tag_configure("agotado", foreground=COLOR_AGOTADO)
        self.tabla.bind("<Double-1>", self._doble_clic)

        ttk.Label(self, text="Doble clic para editar.  Naranja = stock bajo (igual o menor al mínimo).  "
                            "Rojo = agotado.  El stock baja solo cuando Ventas cobra una factura.",
                font=("", 9, "italic"), bootstyle="secondary").pack(anchor="w", pady=(8, 0))

    def al_mostrar(self):
        """Se llama cada vez que se abre la pantalla (por ejemplo después de vender)."""
        self.cargar()

    # ------------------------------------------------------------------ datos
    def _buscar_con_pausa(self):
        """Espera 300 ms tras la última tecla para no consultar la BD en cada letra."""
        if self._pendiente:
            self.after_cancel(self._pendiente)
        self._pendiente = self.after(300, self.cargar)

    def cargar(self):
        self._pendiente = None
        sql = ("SELECT InsumoID, Codigo, Nombre, Marca, Costo, PrecioVenta, Stock, StockMinimo "
            "FROM Insumos WHERE Activo = 1")
        params = []
        texto = self.var_buscar.get().strip()
        if texto:
            patron = f"%{_escapar_like(texto)}%"
            sql += (" AND (Codigo LIKE ? ESCAPE '\\' OR Nombre LIKE ? ESCAPE '\\'"
                    " OR Marca LIKE ? ESCAPE '\\')")
            params += [patron, patron, patron]
        if self.var_solo_bajo.get():
            sql += " AND Stock <= StockMinimo"
        sql += " ORDER BY Nombre"

        try:
            filas = consultar(sql, tuple(params))
            resumen = consultar(
                "SELECT COUNT(*) AS total,"
                " COALESCE(SUM(CASE WHEN Stock <= StockMinimo THEN 1 ELSE 0 END), 0) AS bajos,"
                " COALESCE(SUM(CASE WHEN Stock = 0 THEN 1 ELSE 0 END), 0) AS agotados,"
                " COALESCE(SUM(Costo * Stock), 0) AS valor "
                "FROM Insumos WHERE Activo = 1")[0]
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el inventario:\n{e}")
            return

        self.tabla.delete(*self.tabla.get_children())
        self._filas = {}
        for f in filas:
            self._filas[f["InsumoID"]] = f
            if f["Stock"] == 0:
                estado, tag = "Agotado", "agotado"
            elif f["Stock"] <= f["StockMinimo"]:
                estado, tag = "Bajo", "bajo"
            else:
                estado, tag = "OK", ""
            self.tabla.insert("", tk.END, iid=str(f["InsumoID"]), tags=(tag,) if tag else (), values=(
                f["Codigo"], f["Nombre"], f["Marca"] or "", dinero(f["Costo"]), dinero(f["PrecioVenta"]),
                f["Stock"], f["StockMinimo"], estado))

        self.lbl_total.config(text=f"Repuestos: {resumen['total']}")
        self.lbl_bajo.config(text=f"Stock bajo: {resumen['bajos']}")
        self.lbl_agotado.config(text=f"Agotados: {resumen['agotados']}")
        self.lbl_valor.config(text=f"Valor en bodega (a costo): {dinero(resumen['valor'])}")

    def _seleccionado(self):
        sel = self.tabla.selection()
        if not sel:
            messagebox.showinfo("Inventario", "Seleccione un repuesto de la tabla.")
            return None
        return self._filas.get(int(sel[0]))

    # ------------------------------------------------------------------ acciones
    def agregar(self):
        FormularioProducto(self, None, self._guardar_producto)

    def editar(self):
        producto = self._seleccionado()
        if producto:
            FormularioProducto(self, producto, self._guardar_producto)

    def _doble_clic(self, event):
        if self.tabla.identify_row(event.y):      # solo si se hizo clic sobre una fila (no el encabezado)
            self.editar()

    def _guardar_producto(self, d, ventana):
        """INSERT o UPDATE según el caso. Devuelve True si se guardó."""
        try:
            existente = consultar("SELECT InsumoID, Nombre, Activo FROM Insumos WHERE Codigo = ?", (d["codigo"],))
            if ventana.editando:
                ejecutar("UPDATE Insumos SET Nombre=?, Marca=?, Costo=?, PrecioVenta=?, Stock=?, StockMinimo=? "
                        "WHERE Codigo=?",
                        (d["nombre"], d["marca"], d["costo"], d["venta"], d["stock"], d["minimo"], d["codigo"]))
            elif existente and existente[0]["Activo"]:
                messagebox.showwarning("Código repetido",
                                    f"Ya existe el código {d['codigo']}: «{existente[0]['Nombre']}».",
                                    parent=ventana)
                return False
            elif existente:
                # el código es de un repuesto eliminado antes (desactivado): se ofrece restaurarlo
                if not messagebox.askyesno(
                        "Repuesto eliminado antes",
                        f"El código {d['codigo']} perteneció a «{existente[0]['Nombre']}», que fue eliminado.\n\n"
                        "¿Restaurarlo con los datos que acaba de escribir?", parent=ventana):
                    return False
                ejecutar("UPDATE Insumos SET Nombre=?, Marca=?, Costo=?, PrecioVenta=?, Stock=?, StockMinimo=?, "
                        "Activo=1 WHERE InsumoID=?",
                        (d["nombre"], d["marca"], d["costo"], d["venta"], d["stock"], d["minimo"],
                        existente[0]["InsumoID"]))
            else:
                ejecutar("INSERT INTO Insumos (Codigo, Nombre, Marca, Costo, PrecioVenta, Stock, StockMinimo) "
                        "VALUES (?,?,?,?,?,?,?)",
                        (d["codigo"], d["nombre"], d["marca"], d["costo"], d["venta"], d["stock"], d["minimo"]))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el repuesto:\n{e}", parent=ventana)
            return False
        self.cargar()
        return True

    def eliminar(self):
        producto = self._seleccionado()
        if not producto:
            return
        nombre = f"{producto['Codigo']} - {producto['Nombre']}"
        if not messagebox.askyesno("Eliminar repuesto", f"¿Eliminar «{nombre}» del inventario?"):
            return
        try:
            with get_connection() as cn:
                cur = cn.cursor()
                cur.execute("SELECT COUNT(*) FROM DetalleFactura WHERE InsumoID = ?", (producto["InsumoID"],))
                vendido = cur.fetchone()[0] > 0
                if vendido:
                    # ya aparece en facturas: se desactiva para no romper el historial de ventas
                    cur.execute("UPDATE Insumos SET Activo = 0 WHERE InsumoID = ?", (producto["InsumoID"],))
                else:
                    cur.execute("DELETE FROM Insumos WHERE InsumoID = ?", (producto["InsumoID"],))
                cn.commit()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar el repuesto:\n{e}")
            return
        if vendido:
            messagebox.showinfo("Repuesto retirado",
                                "Este repuesto ya se vendió en facturas anteriores, así que se retiró del "
                                "inventario (ya no aparece en Ventas) pero se conserva en el historial.")
        self.cargar()