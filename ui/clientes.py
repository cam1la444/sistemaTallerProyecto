"""Módulo Clientes"""
import re
import tkinter as tk
from tkinter import messagebox
from datetime import date

import pyodbc
import ttkbootstrap as ttk

from core.database import get_connection as conectar, consultar


#descuento para los visitantes frecuentes
VISITAS_PARA_DESCUENTO = 5
PORCENTAJE_DESCUENTO = 25


def descuento_proxima_visita(visitas):
    """25% si la próxima visita es la 5, 10, 15..."""
    return PORCENTAJE_DESCUENTO if (visitas + 1) % VISITAS_PARA_DESCUENTO == 0 else 0


def texto_descuento(visitas):
    if descuento_proxima_visita(visitas):
        return f"¡{PORCENTAJE_DESCUENTO}% en la próxima visita!"
    siguiente = visitas + (VISITAS_PARA_DESCUENTO - visitas % VISITAS_PARA_DESCUENTO)
    return f"{PORCENTAJE_DESCUENTO}% en la visita #{siguiente}"


# validaciones
def nul(texto):
    texto = (texto or "").strip()
    return texto or None


def _entero(texto, campo, minimo, maximo=None, requerido=True):
    texto = (texto or "").strip()
    if not texto:
        if requerido:
            raise ValueError(f"{campo} es obligatorio.")
        return None
    if not texto.isdigit():
        raise ValueError(f"{campo} debe ser un número entero.")
    n = int(texto)
    if n < minimo or (maximo is not None and n > maximo):
        raise ValueError(f"{campo} fuera de rango.")
    return n


#formulario para el carro
class VehiculoForm(ttk.LabelFrame):
    def __init__(self, parent, datos=None):
        super().__init__(parent, text="Vehículo", padding=8)
        d = datos or {}
        campos = ["tipo", "placa", "marca", "modelo", "anio", "color",
                  "kilometraje", "puertas", "transmision", "cilindraje"]
        self.v = {k: tk.StringVar(value="" if d.get(k) is None else str(d.get(k)))
                  for k in campos}
        if not self.v["tipo"].get():
            self.v["tipo"].set("Auto")

        filas = [("Tipo", "tipo"), ("Placa", "placa"), ("Marca", "marca"),
                 ("Modelo", "modelo"), ("Año", "anio"), ("Color", "color"),
                 ("Kilometraje", "kilometraje")]
        for i, (txt, k) in enumerate(filas):
            ttk.Label(self, text=txt).grid(row=i, column=0, sticky="w", pady=3, padx=(0, 8))
            if k == "tipo":
                w = ttk.Combobox(self, textvariable=self.v[k], values=["Auto", "Moto"],
                                 state="readonly", width=28)
                w.bind("<<ComboboxSelected>>", lambda e: self._mostrar_extra())
            else:
                w = ttk.Entry(self, textvariable=self.v[k], width=30)
            w.grid(row=i, column=1, sticky="ew", pady=3)

        # campos dependiendo si es auto o moto
        self.f_auto = ttk.Frame(self)
        ttk.Label(self.f_auto, text="Puertas").grid(row=0, column=0, sticky="w", pady=3, padx=(0, 8))
        ttk.Entry(self.f_auto, textvariable=self.v["puertas"], width=30).grid(row=0, column=1, pady=3)
        ttk.Label(self.f_auto, text="Transmisión").grid(row=1, column=0, sticky="w", pady=3, padx=(0, 8))
        ttk.Combobox(self.f_auto, textvariable=self.v["transmision"],
                     values=["Manual", "Automática"], state="readonly", width=28
                     ).grid(row=1, column=1, pady=3)
        self.f_moto = ttk.Frame(self)
        ttk.Label(self.f_moto, text="Cilindraje (cc)").grid(row=0, column=0, sticky="w", pady=3, padx=(0, 8))
        ttk.Entry(self.f_moto, textvariable=self.v["cilindraje"], width=30).grid(row=0, column=1, pady=3)
        self._mostrar_extra()

    def _mostrar_extra(self):
        self.f_auto.grid_forget()
        self.f_moto.grid_forget()
        destino = self.f_auto if self.v["tipo"].get() == "Auto" else self.f_moto
        destino.grid(row=10, column=0, columnspan=2, sticky="ew")

    def valores(self):
        v = {k: var.get().strip() for k, var in self.v.items()}
        placa = v["placa"].upper().replace(" ", "")
        if not placa:
            raise ValueError("La placa es obligatoria.")
        if not v["marca"] or not v["modelo"]:
            raise ValueError("Marca y modelo son obligatorios.")
        es_auto = v["tipo"] == "Auto"
        return {
            "tipo": v["tipo"], "placa": placa, "marca": v["marca"], "modelo": v["modelo"],
            "anio": _entero(v["anio"], "El año", 1950, date.today().year + 1),
            "color": nul(v["color"]),
            "kilometraje": _entero(v["kilometraje"], "El kilometraje", 0, requerido=False) or 0,
            "puertas": _entero(v["puertas"], "Las puertas", 1, 6, requerido=False) if es_auto else None,
            "transmision": nul(v["transmision"]) if es_auto else None,
            "cilindraje": _entero(v["cilindraje"], "El cilindraje", 1, 3000, requerido=False) if not es_auto else None,
        }


SQL_INS_VEH = ("INSERT INTO Vehiculos(id_cliente, placa, tipo, marca, modelo, anio, color, kilometraje,"
               " puertas, transmision, cilindraje) VALUES (?,?,?,?,?,?,?,?,?,?,?)")


def _args_vehiculo(idc, d):
    return (idc, d["placa"], d["tipo"], d["marca"], d["modelo"], d["anio"], d["color"],
            d["kilometraje"], d["puertas"], d["transmision"], d["cilindraje"])


def _placa_existe(placa, excluir_id=None):
    r = consultar("SELECT v.id_vehiculo, c.nombre FROM Vehiculos v JOIN Clientes c "
                  "ON c.id_cliente = v.id_cliente WHERE v.placa = ? AND v.id_vehiculo <> ?",
                  (placa, excluir_id or 0))
    return r[0] if r else None


# mensajes de dialogos
class _Modal(tk.Toplevel):
    def __init__(self, parent, titulo):
        super().__init__(parent)
        self.title(titulo)
        self.transient(parent.winfo_toplevel())
        self.resizable(False, False)
        self.ok = False
        self.bind("<Escape>", lambda e: self.destroy())

    def mostrar(self):
        self.update_idletasks()
        top = self.master.winfo_toplevel()
        x = top.winfo_rootx() + (top.winfo_width() - self.winfo_width()) // 2
        y = top.winfo_rooty() + (top.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.grab_set()
        self.wait_window()
        return self.ok

    def botones(self, parent, texto_ok="Guardar"):
        f = ttk.Frame(parent)
        ttk.Button(f, text="Cancelar", command=self.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(f, text=texto_ok, command=self.guardar).pack(side="right")
        return f


class ClienteDialog(_Modal):
    """Cliente nuevo (con su primer vehículo) o edición de datos del cliente."""

    def __init__(self, parent, id_cliente=None):
        super().__init__(parent, "Editar cliente" if id_cliente else "Registrar cliente y vehículo")
        self.id_cliente = id_cliente
        d = consultar("SELECT * FROM Clientes WHERE id_cliente = ?", (id_cliente,))[0] if id_cliente else {}

        cont = ttk.Frame(self, padding=12)
        cont.pack(fill="both", expand=True)
        box = ttk.LabelFrame(cont, text="Cliente", padding=8)
        box.grid(row=0, column=0, sticky="n", padx=(0, 10))

        self.v = {k: tk.StringVar(value=d.get(k) or "") for k in
                  ["tipo_persona", "nombre", "dui", "nit", "telefono", "correo", "direccion"]}
        if not self.v["tipo_persona"].get():
            self.v["tipo_persona"].set("Natural")
        etiquetas = [("Tipo de persona", "tipo_persona"), ("Nombre *", "nombre"),
                     ("DUI (00000000-0)", "dui"), ("NIT", "nit"), ("Teléfono *", "telefono"),
                     ("Correo", "correo"), ("Dirección", "direccion")]
        for i, (txt, k) in enumerate(etiquetas):
            ttk.Label(box, text=txt).grid(row=i, column=0, sticky="w", pady=3, padx=(0, 8))
            if k == "tipo_persona":
                w = ttk.Combobox(box, textvariable=self.v[k], values=["Natural", "Juridica"],
                                 state="readonly", width=28)
            else:
                w = ttk.Entry(box, textvariable=self.v[k], width=30)
            w.grid(row=i, column=1, pady=3)

        self.form_veh = None
        if not id_cliente:
            self.form_veh = VehiculoForm(cont)
            self.form_veh.grid(row=0, column=1, sticky="n")
        self.botones(cont).grid(row=1, column=0, columnspan=2, sticky="e", pady=(10, 0))
        self.bind("<Return>", lambda e: self.guardar())
        self.mostrar()

    def guardar(self):
        try:
            c = {k: var.get().strip() for k, var in self.v.items()}
            if not c["nombre"]:
                raise ValueError("El nombre es obligatorio.")
            if not c["telefono"]:
                raise ValueError("El teléfono es obligatorio.")
            if c["dui"] and not re.fullmatch(r"\d{8}-\d", c["dui"]):
                raise ValueError("El DUI debe tener el formato 00000000-0.")
            veh = self.form_veh.valores() if self.form_veh else None
        except ValueError as e:
            messagebox.showwarning("Datos incompletos", str(e), parent=self)
            return

        # Evitar registrar dos veces al mismo cliente / la misma placa
        if c["dui"]:
            dup = consultar("SELECT nombre FROM Clientes WHERE dui = ? AND id_cliente <> ?",
                            (c["dui"], self.id_cliente or 0))
            if dup:
                messagebox.showinfo("Cliente ya registrado",
                                    f"Ese DUI ya pertenece a {dup[0]['nombre']}.\n"
                                    "No hace falta registrarlo de nuevo: búscalo y crea su orden.",
                                    parent=self)
                return
        if veh:
            dup = _placa_existe(veh["placa"])
            if dup:
                messagebox.showinfo("Vehículo ya registrado",
                                    f"La placa {veh['placa']} ya está registrada a nombre de {dup['nombre']}.",
                                    parent=self)
                return
        try:
            with conectar() as cn:
                cur = cn.cursor()
                datos = (c["tipo_persona"], c["nombre"], nul(c["dui"]), nul(c["nit"]),
                         c["telefono"], nul(c["correo"]), nul(c["direccion"]))
                if self.id_cliente:
                    cur.execute("UPDATE Clientes SET tipo_persona=?, nombre=?, dui=?, nit=?, telefono=?,"
                                " correo=?, direccion=? WHERE id_cliente=?", datos + (self.id_cliente,))
                else:
                    cur.execute("INSERT INTO Clientes(tipo_persona, nombre, dui, nit, telefono, correo,"
                                " direccion) OUTPUT INSERTED.id_cliente VALUES (?,?,?,?,?,?,?)", datos)
                    idc = cur.fetchone()[0]
                    cur.execute(SQL_INS_VEH, _args_vehiculo(idc, veh))
        except pyodbc.Error as e:
            messagebox.showerror("Error de base de datos", str(e), parent=self)
            return
        self.ok = True
        self.destroy()


class VehiculoDialog(_Modal):
    def __init__(self, parent, id_cliente, nombre_cliente, id_vehiculo=None):
        super().__init__(parent, "Editar vehículo" if id_vehiculo else "Agregar vehículo")
        self.id_cliente, self.id_vehiculo = id_cliente, id_vehiculo
        d = consultar("SELECT * FROM Vehiculos WHERE id_vehiculo = ?", (id_vehiculo,))[0] if id_vehiculo else None
        cont = ttk.Frame(self, padding=12)
        cont.pack()
        ttk.Label(cont, text=f"Cliente: {nombre_cliente}", font=("", 10, "bold")).pack(anchor="w", pady=(0, 6))
        self.form = VehiculoForm(cont, d)
        self.form.pack()
        self.botones(cont).pack(anchor="e", pady=(10, 0))
        self.bind("<Return>", lambda e: self.guardar())
        self.mostrar()

    def guardar(self):
        try:
            d = self.form.valores()
        except ValueError as e:
            messagebox.showwarning("Datos incompletos", str(e), parent=self)
            return
        dup = _placa_existe(d["placa"], self.id_vehiculo)
        if dup:
            messagebox.showinfo("Placa ya registrada",
                                f"La placa {d['placa']} ya está registrada a nombre de {dup['nombre']}.",
                                parent=self)
            return
        try:
            with conectar() as cn:
                cur = cn.cursor()
                if self.id_vehiculo:
                    cur.execute("UPDATE Vehiculos SET placa=?, tipo=?, marca=?, modelo=?, anio=?, color=?,"
                                " kilometraje=?, puertas=?, transmision=?, cilindraje=? WHERE id_vehiculo=?",
                                _args_vehiculo(0, d)[1:] + (self.id_vehiculo,))
                else:
                    cur.execute(SQL_INS_VEH, _args_vehiculo(self.id_cliente, d))
        except pyodbc.Error as e:
            messagebox.showerror("Error de base de datos", str(e), parent=self)
            return
        self.ok = True
        self.destroy()


# ventana del treeview
FILTRO = ("(? = '' OR c.nombre LIKE ? OR c.dui LIKE ? OR c.codigo LIKE ? OR EXISTS "
          "(SELECT 1 FROM Vehiculos x WHERE x.id_cliente = c.id_cliente AND x.placa LIKE ?))")


class ClientesFrame(ttk.Frame):
    def __init__(self, master, on_crear_orden=None):
        super().__init__(master, padding=20)
        self.on_crear_orden = on_crear_orden
        self.q = tk.StringVar()

        ttk.Label(self, text="Clientes", font=("", 20, "bold")).pack(anchor="w", pady=(0, 10))

        barra = ttk.Frame(self)
        barra.pack(fill="x", pady=(0, 8))
        ttk.Label(barra, text="Buscar (DUI, placa o nombre):").pack(side="left")
        e = ttk.Entry(barra, textvariable=self.q, width=30)
        e.pack(side="left", padx=6)
        e.bind("<Return>", lambda ev: self.cargar())
        ttk.Button(barra, text="Buscar", command=self.cargar).pack(side="left")
        ttk.Button(barra, text="Limpiar", command=self.limpiar, bootstyle="secondary").pack(side="left", padx=4)
        ttk.Button(barra, text="+ Nuevo cliente", command=self.nuevo_cliente,
                   bootstyle="success").pack(side="right")

        cols = ("nombre", "dui", "telefono", "vehiculos", "visitas", "descuento")
        self.tree = ttk.Treeview(self, columns=cols, selectmode="browse")
        self.tree.heading("#0", text="Código / Placa")
        self.tree.column("#0", width=150)
        for c, t, w in [("nombre", "Nombre / Vehículo", 280), ("dui", "DUI", 110),
                        ("telefono", "Teléfono", 110), ("vehiculos", "Vehíc.", 60),
                        ("visitas", "Visitas", 60), ("descuento", "Descuento", 190)]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="w")
        sb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.tag_configure("premio", foreground="#4caf50")

        self.tree.bind("<Button-3>", self.menu_contextual)
        self.tree.bind("<Double-1>", self.menu_contextual)

    def al_mostrar(self):
        """Se llama cada vez que el usuario abre esta pantalla: refresca los datos."""
        self.cargar()

    # datos para el buscador
    def limpiar(self):
        self.q.set("")
        self.cargar()

    def cargar(self):
        q = self.q.get().strip()
        like = f"%{q}%"
        params = (q, like, like, like, like)
        try:
            clientes = consultar(
                "SELECT c.id_cliente, c.codigo, c.nombre, c.dui, c.telefono, c.visitas,"
                " (SELECT COUNT(*) FROM Vehiculos v WHERE v.id_cliente = c.id_cliente) AS n_veh"
                f" FROM Clientes c WHERE {FILTRO} ORDER BY c.nombre", params)
            vehiculos = consultar(
                "SELECT v.* FROM Vehiculos v JOIN Clientes c ON c.id_cliente = v.id_cliente"
                f" WHERE {FILTRO} ORDER BY v.placa", params)
        except pyodbc.Error as e:
            messagebox.showerror("Error de base de datos", str(e), parent=self)
            return

        self.tree.delete(*self.tree.get_children())
        por_cliente = {}
        for v in vehiculos:
            por_cliente.setdefault(v["id_cliente"], []).append(v)
        for c in clientes:
            tag = ("premio",) if descuento_proxima_visita(c["visitas"]) else ()
            iid = f"c{c['id_cliente']}"
            self.tree.insert("", "end", iid=iid, text=c["codigo"], open=bool(q), tags=tag,
                             values=(c["nombre"], c["dui"] or "", c["telefono"], c["n_veh"],
                                     c["visitas"], texto_descuento(c["visitas"])))
            for v in por_cliente.get(c["id_cliente"], []):
                detalle = f"{v['tipo']} {v['marca']} {v['modelo']} {v['anio']}"
                self.tree.insert(iid, "end", iid=f"v{v['id_vehiculo']}", text=v["placa"],
                                 values=(detalle, "", "", "", "", ""))
        if q and len(clientes) == 0:
            if messagebox.askyesno("Sin resultados",
                                   "No existe ningún cliente con esos datos.\n¿Registrar un cliente nuevo?",
                                   parent=self):
                self.nuevo_cliente()

    # CRUD con los datos del treeview
    def _nombre_de(self, iid):
        cid = iid if iid.startswith("c") else self.tree.parent(iid)
        return self.tree.set(cid, "nombre")

    def nuevo_cliente(self):
        if ClienteDialog(self).ok:
            self.cargar()

    def editar_cliente(self, idc):
        if ClienteDialog(self, idc).ok:
            self.cargar()

    def eliminar_cliente(self, idc, nombre):
        if not messagebox.askyesno("Eliminar cliente",
                                   f"¿Eliminar a {nombre} y todos sus vehículos?\n"
                                   "Esta acción no se puede deshacer.", parent=self):
            return
        try:
            with conectar() as cn:
                cur = cn.cursor()
                cur.execute("DELETE FROM Vehiculos WHERE id_cliente = ?", (idc,))
                cur.execute("DELETE FROM Clientes WHERE id_cliente = ?", (idc,))
        except pyodbc.Error:
            messagebox.showerror("No se puede eliminar",
                                 "El cliente tiene órdenes o historial asociado.", parent=self)
            return
        self.cargar()

    def agregar_vehiculo(self, idc, nombre):
        if VehiculoDialog(self, idc, nombre).ok:
            self.cargar()
            self.tree.item(f"c{idc}", open=True)

    def editar_vehiculo(self, idv, idc, nombre):
        if VehiculoDialog(self, idc, nombre, idv).ok:
            self.cargar()

    def eliminar_vehiculo(self, idv, placa):
        if not messagebox.askyesno("Eliminar vehículo", f"¿Eliminar el vehículo {placa}?", parent=self):
            return
        try:
            with conectar() as cn:
                cn.cursor().execute("DELETE FROM Vehiculos WHERE id_vehiculo = ?", (idv,))
        except pyodbc.Error:
            messagebox.showerror("No se puede eliminar",
                                 "El vehículo tiene órdenes asociadas.", parent=self)
            return
        self.cargar()

    def _orden(self, idc, idv=None):
        if self.on_crear_orden:
            self.on_crear_orden(idc, idv)
        else:
            messagebox.showinfo("Órdenes", "El módulo de órdenes aún está en construcción.", parent=self)

    # ---------------------------------------------- menú doble clic / clic derecho
    def menu_contextual(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        self.tree.selection_set(iid)
        nombre = self._nombre_de(iid)
        m = tk.Menu(self, tearoff=0)
        if iid.startswith("c"):
            idc = int(iid[1:])
            m.add_command(label="Crear orden de reparación", command=lambda: self._orden(idc))
            m.add_separator()
            m.add_command(label="Agregar vehículo", command=lambda: self.agregar_vehiculo(idc, nombre))
            m.add_command(label="Editar cliente", command=lambda: self.editar_cliente(idc))
            m.add_command(label="Eliminar cliente", command=lambda: self.eliminar_cliente(idc, nombre))
        else:
            idv = int(iid[1:])
            idc = int(self.tree.parent(iid)[1:])
            placa = self.tree.item(iid, "text")
            m.add_command(label="Crear orden para este vehículo", command=lambda: self._orden(idc, idv))
            m.add_separator()
            m.add_command(label="Editar vehículo", command=lambda: self.editar_vehiculo(idv, idc, nombre))
            m.add_command(label="Eliminar vehículo", command=lambda: self.eliminar_vehiculo(idv, placa))
        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()
        return "break"  # evita que el doble clic también expanda/colapse la fila


if __name__ == "__main__":   
    root = ttk.Window(title="Clientes", themename="darkly", size=(1100, 650))
    frame = ClientesFrame(root)
    frame.pack(fill="both", expand=True)
    frame.al_mostrar()
    root.mainloop()