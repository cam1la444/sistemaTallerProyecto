"""Módulo Órdenes de Servicio.
Gestión de citas, seguimiento de estados, control de fechas y asignación de servicios."""
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkinter as tk
from tkinter import messagebox
from datetime import date, timedelta
from core.database import consultar, get_connection

ESTADOS_ORDEN = ["Registrado", "En proceso", "Finalizado", "Entregado"]

class OrdenesFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=20)
        
        #titulo principal
        ttk.Label(self, text="Órdenes de Servicio", font=("", 20, "bold")).pack(anchor="w", pady=(0, 10))
        
        #barra de control (filtro por estado y botón Nueva Orden)
        barra_top = ttk.Frame(self)
        barra_top.pack(fill="x", pady=(0, 10))
        
        ttk.Label(barra_top, text="Filtrar por Estado:").pack(side="left", padx=(0, 5))
        self.combo_filtro_estado = ttk.Combobox(barra_top, values=["Todos"] + ESTADOS_ORDEN, state="readonly", width=15)
        self.combo_filtro_estado.set("Todos")
        self.combo_filtro_estado.pack(side="left", padx=5)
        self.combo_filtro_estado.bind("<<ComboboxSelected>>", lambda e: self.cargar_ordenes())
        
        ttk.Button(barra_top, text="Actualizar Lista", bootstyle="secondary", command=self.cargar_ordenes).pack(side="left", padx=5)
        ttk.Button(barra_top, text="+ Nueva Orden de Servicio", bootstyle="success", command=self.abrir_modal_nueva_orden).pack(side="right")

        ttk.Label(
            self, 
            text="Doble clic sobre la orden para cambiar su estado.", 
            font=("", 9, "italic"), 
            bootstyle="secondary"
        ).pack(anchor="w", pady=(0, 8))
        # Tabla de Órdenes
        cols = ("codigo", "cliente", "vehiculo", "fecha_reg", "fecha_est", "estado", "descuento")
        self.tabla = ttk.Treeview(self, columns=cols, show="headings", height=15)
        self.tabla.heading("codigo", text="Código Orden", anchor="w")
        self.tabla.heading("cliente", text="Cliente", anchor="w")
        self.tabla.heading("vehiculo", text="Vehículo (Placa)", anchor="w")
        self.tabla.heading("fecha_reg", text="Fecha Registro", anchor="w")
        self.tabla.heading("fecha_est", text="Entrega Estimada", anchor="w")
        self.tabla.heading("estado", text="Estado Actual", anchor="w")
        self.tabla.heading("descuento", text="Descuento", anchor="w")
        
        self.tabla.column("codigo", width=100, anchor="w")
        self.tabla.column("cliente", width=180, anchor="w")
        self.tabla.column("vehiculo", width=150, anchor="w")
        self.tabla.column("fecha_reg", width=110, anchor="w")
        self.tabla.column("fecha_est", width=110, anchor="w")
        self.tabla.column("estado", width=110, anchor="w")
        self.tabla.column("descuento", width=100, anchor="w")
        
        sb = ttk.Scrollbar(self, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=sb.set)
        
        self.tabla.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        
        # Eventos para cambiar estado manual
        self.tabla.bind("<Double-1>", self.cambiar_estado_manual)
        
        self.cargar_ordenes()

    def al_mostrar(self):
        """Refresca la lista cada vez que se abre la pantalla."""
        self.cargar_ordenes()

    def cargar_ordenes(self):
        """Carga las órdenes de servicio desde la base de datos."""
        self.tabla.delete(*self.tabla.get_children())
        filtro = self.combo_filtro_estado.get()
        
        query = """
            SELECT o.id_orden, o.codigo_orden, c.nombre AS cliente, 
                   (v.tipo + ' ' + v.marca + ' (' + v.placa + ')') AS vehiculo,
                   CONVERT(VARCHAR, o.fecha_registro, 103) AS fecha_reg,
                   CONVERT(VARCHAR, o.fecha_estimada, 103) AS fecha_est,
                   o.estado, o.descuento_aplicado
            FROM Ordenes o
            JOIN Clientes c ON c.id_cliente = o.id_cliente
            JOIN Vehiculos v ON v.id_vehiculo = o.id_vehiculo
        """
        params = []
        if filtro != "Todos":
            query += " WHERE o.estado = ?"
            params.append(filtro)
            
        query += " ORDER BY o.id_orden DESC"
        
        try:
            ordenes = consultar(query, tuple(params))
            for o in ordenes:
                desc_txt = f"{int(o['descuento_aplicado'])}%" if o['descuento_aplicado'] > 0 else "0%"
                self.tabla.insert("", tk.END, iid=o['id_orden'], values=(
                    o['codigo_orden'], o['cliente'], o['vehiculo'], o['fecha_reg'], o['fecha_est'], o['estado'], desc_txt
                ))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar las órdenes:\n{e}")

    def cambiar_estado_manual(self, event):
        """Permite cambiar manualmente el estado de la orden seleccionada."""
        sel = self.tabla.selection()
        if not sel:
            return
        id_orden = int(sel[0])
        estado_actual = self.tabla.item(id_orden, "values")[5]
        
        win = ttk.Toplevel(self)
        win.title("Cambiar Estado de la Orden")
        win.geometry("320x200")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        
        ttk.Label(win, text="Seleccionar Nuevo Estado:", font=("", 11, "bold")).pack(pady=15)
        combo = ttk.Combobox(win, values=ESTADOS_ORDEN, state="readonly", width=20)
        combo.set(estado_actual)
        combo.pack(pady=10)
        
        def guardar():
            nuevo = combo.get()
            try:
                with get_connection() as cn:
                    cn.cursor().execute("UPDATE Ordenes SET estado = ? WHERE id_orden = ?", (nuevo, id_orden))
                    cn.commit()
                messagebox.showinfo("Éxito", f"Estado actualizado a: {nuevo}", parent=win)
                win.destroy()
                self.cargar_ordenes()
            except Exception as ex:
                messagebox.showerror("Error", str(ex), parent=win)
                
        ttk.Button(win, text="Guardar Estado", bootstyle="success", command=guardar).pack(pady=15)

    def abrir_modal_nueva_orden(self):
        """Modal para agendar una cita/orden asociando cliente, vehículo y servicios."""
        modal = ttk.Toplevel(self)
        modal.title("Registrar Orden de Servicio")
        modal.geometry(f"580x{min(730, modal.winfo_screenheight() - 90)}")
        modal.resizable(False, False)
        modal.transient(self)
        modal.grab_set()
        
        cont = ttk.Frame(modal, padding=15)
        cont.pack(fill="both", expand=True)
        
        ttk.Label(cont, text="Nueva Orden de Servicio", font=("", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        #Buscar y seleccionar cliente
        ttk.Label(cont, text="1. Seleccionar Cliente:").grid(row=1, column=0, sticky="w", pady=5)
        
        clientes_dict = {}
        res_cli = consultar("SELECT id_cliente, codigo, nombre, dui, visitas FROM Clientes ORDER BY nombre")
        cli_opciones = []
        for c in res_cli:
            txt = f"{c['codigo']} - {c['nombre']} (DUI: {c['dui'] or 'N/A'})"
            cli_opciones.append(txt)
            clientes_dict[txt] = {"id": c['id_cliente'], "visitas": c['visitas'], "nombre": c['nombre']}
            
        combo_cli = ttk.Combobox(cont, values=cli_opciones, state="readonly", width=38)
        combo_cli.grid(row=1, column=1, pady=5)
        
        # Etiqueta de aviso de descuento por cliente frecuente
        lbl_fidelidad = ttk.Label(cont, text="", font=("", 10, "bold"), foreground="green")
        lbl_fidelidad.grid(row=2, column=0, columnspan=2, pady=2)
        
        #Vehículos del cliente seleccionado
        ttk.Label(cont, text="2. Vehículo a Ingresar:").grid(row=3, column=0, sticky="w", pady=5)
        combo_veh = ttk.Combobox(cont, state="readonly", width=38)
        combo_veh.grid(row=3, column=1, pady=5)
        vehiculos_dict = {}
        
        def al_seleccionar_cliente(event):
            combo_veh.set('')
            vehiculos_dict.clear()
            cli_str = combo_cli.get()
            if not cli_str:
                return
            cli_info = clientes_dict[cli_str]
            
            # Comprobar si la PRÓXIMA visita (visitas + 1) califica para el 25% de descuento
            visita_nueva = cli_info["visitas"] + 1
            if visita_nueva % 5 == 0:
                lbl_fidelidad.config(text=f"¡Atención: Visita #{visita_nueva}! Aplica 25% de Descuento.")
            else:
                lbl_fidelidad.config(text=f"Visita #{visita_nueva} del cliente.")
                
            res_v = consultar("SELECT id_vehiculo, placa, tipo, marca, modelo FROM Vehiculos WHERE id_cliente = ?", (cli_info["id"],))
            v_opciones = []
            for v in res_v:
                txt_v = f"{v['placa']} - {v['tipo']} {v['marca']} {v['modelo']}"
                v_opciones.append(txt_v)
                vehiculos_dict[txt_v] = v['id_vehiculo']
            combo_veh['values'] = v_opciones
            if v_opciones:
                combo_veh.current(0)
                
        combo_cli.bind("<<ComboboxSelected>>", al_seleccionar_cliente)
        
        # Control de Fechas
        ttk.Label(cont, text="3. Días estimados de entrega:").grid(row=4, column=0, sticky="w", pady=5)
        spin_dias = ttk.Spinbox(cont, from_=1, to=30, width=10)
        spin_dias.set(2) # Por defecto 2 días
        spin_dias.grid(row=4, column=1, sticky="w", pady=5)
        
        # Servicios a realizar: salen de la tabla Servicios y se marcan con un clic (☐ -> ☑)
        ttk.Label(cont, text="4. Servicios a realizar (clic para marcar):").grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(8, 2))
        fila_busq = ttk.Frame(cont)
        fila_busq.grid(row=6, column=0, columnspan=2, sticky="ew")
        ttk.Label(fila_busq, text="Buscar servicio:").pack(side="left")
        var_busq = tk.StringVar()
        ttk.Entry(fila_busq, textvariable=var_busq).pack(side="left", fill="x", expand=True, padx=(6, 0))

        zona_serv = ttk.Frame(cont)
        zona_serv.grid(row=7, column=0, columnspan=2, sticky="nsew", pady=5)
        tabla_serv = ttk.Treeview(zona_serv, columns=("ok", "nombre", "precio"), show="headings",
                                  height=9, selectmode="none")
        tabla_serv.heading("ok", text="")
        tabla_serv.heading("nombre", text="Servicio")
        tabla_serv.heading("precio", text="Precio ($)")
        tabla_serv.column("ok", width=34, anchor="center", stretch=False)
        tabla_serv.column("nombre", width=330)
        tabla_serv.column("precio", width=80, anchor="e", stretch=False)
        tabla_serv.tag_configure("marcado", foreground="#00bc8c")
        sb_serv = ttk.Scrollbar(zona_serv, orient="vertical", command=tabla_serv.yview)
        tabla_serv.configure(yscrollcommand=sb_serv.set)
        sb_serv.pack(side="right", fill="y")
        tabla_serv.pack(side="left", fill="both", expand=True)
        cont.columnconfigure(1, weight=1)
        cont.rowconfigure(7, weight=1)

        servicios_disponibles = []
        try:
            servicios_disponibles = consultar(
                "SELECT ServicioID AS id, Codigo AS codigo, Nombre AS nombre, Precio AS precio "
                "FROM Servicios WHERE Activo = 1 ORDER BY Codigo")
        except Exception as ex:
            messagebox.showerror("Error", f"No se pudieron cargar los servicios:\n{ex}", parent=modal)
        marcados = set()           # ids de los servicios marcados

        lbl_total = ttk.Label(cont, text="", font=("", 10, "bold"))
        lbl_total.grid(row=8, column=0, columnspan=2, sticky="w")

        def actualizar_total():
            if not servicios_disponibles:
                lbl_total.config(text="No hay servicios registrados (cárguelos con sql/03_servicios.sql).",
                                 foreground="#e74c3c")
                return
            elegidos = [x for x in servicios_disponibles if x["id"] in marcados]
            total = sum(float(x["precio"]) for x in elegidos)
            lbl_total.config(foreground="",
                             text=f"Servicios marcados: {len(elegidos)}   |   Total estimado (sin IVA): ${total:,.2f}")

        def datos_fila(x):
            marcado = x["id"] in marcados
            return ("\u2611" if marcado else "\u2610", x["nombre"], f"${float(x['precio']):.2f}"), \
                   (("marcado",) if marcado else ())

        def dibujar_servicios(*_):
            filtro = var_busq.get().strip().lower()
            tabla_serv.delete(*tabla_serv.get_children())
            for x in servicios_disponibles:
                if filtro and filtro not in x["nombre"].lower() and filtro not in x["codigo"].lower():
                    continue
                valores, tags = datos_fila(x)
                tabla_serv.insert("", tk.END, iid=f"s_{x['id']}", values=valores, tags=tags)

        def alternar_servicio(event):
            fila = tabla_serv.identify_row(event.y)
            if not fila:
                return "break"
            s_id = int(fila[2:])
            marcados.symmetric_difference_update({s_id})
            x = next(item for item in servicios_disponibles if item["id"] == s_id)
            valores, tags = datos_fila(x)
            tabla_serv.item(fila, values=valores, tags=tags)
            actualizar_total()
            return "break"

        tabla_serv.bind("<Button-1>", alternar_servicio)
        var_busq.trace_add("write", dibujar_servicios)
        dibujar_servicios()
        actualizar_total()

        ttk.Label(cont, text="Observaciones / Motivo:").grid(row=9, column=0, sticky="w", pady=5)
        ent_obs = ttk.Entry(cont, width=38)
        ent_obs.grid(row=9, column=1, sticky="ew", pady=5)
        
        def guardar_orden():
            cli_str = combo_cli.get()
            veh_str = combo_veh.get()
            if not cli_str or not veh_str:
                messagebox.showwarning("Advertencia", "Debe seleccionar un cliente y un vehículo.", parent=modal)
                return
                
            cli_data = clientes_dict[cli_str]
            id_cliente = cli_data["id"]
            id_vehiculo = vehiculos_dict[veh_str]
            
            dias = int(spin_dias.get())
            fecha_est = date.today() + timedelta(days=dias)
            
            #calcular descuento aplicable
            visitas_nuevas = cli_data["visitas"] + 1
            desc = 25.0 if (visitas_nuevas % 5 == 0) else 0.0
            
            obs = ent_obs.get().strip()
            serv_seleccionados = [x for x in servicios_disponibles if x["id"] in marcados]
            if not serv_seleccionados and not messagebox.askyesno(
                    "Sin servicios", "No marcó ningún servicio.\n¿Guardar la orden sin servicios?", parent=modal):
                return
            
            try:
                with get_connection() as cn:
                    cur = cn.cursor()
                    
                    #Guardar la Orden
                    sql_ord = """
                        INSERT INTO Ordenes (id_cliente, id_vehiculo, estado, fecha_registro, fecha_estimada, descuento_aplicado, observaciones)
                        OUTPUT INSERTED.id_orden
                        VALUES (?, ?, 'Registrado', GETDATE(), ?, ?, ?)
                    """
                    cur.execute(sql_ord, (id_cliente, id_vehiculo, fecha_est, desc, obs))
                    id_orden = cur.fetchone()[0]
                    
                    #Guardar los Servicios Seleccionados en el Detalle
                    for serv_obj in serv_seleccionados:
                        cur.execute("INSERT INTO DetalleOrden (id_orden, tipo_item, id_item, nombre, precio) VALUES (?, 'Servicio', ?, ?, ?)",
                                    (id_orden, serv_obj['id'], serv_obj['nombre'], serv_obj['precio']))
                                    
                    #Incrementar las Visitas del Cliente en la BD
                    cur.execute("UPDATE Clientes SET visitas = visitas + 1 WHERE id_cliente = ?", (id_cliente,))
                    
                    cn.commit()
                    
                messagebox.showinfo("Éxito", "Orden de Servicio registrada correctamente.\nSe ha actualizado el conteo de visitas del cliente.", parent=modal)
                modal.destroy()
                self.cargar_ordenes()
            except Exception as ex:
                messagebox.showerror("Error", f"No se pudo guardar la orden:\n{ex}", parent=modal)

        frame_btns = ttk.Frame(cont)
        frame_btns.grid(row=10, column=0, columnspan=2, pady=15)
        ttk.Button(frame_btns, text="Guardar Orden", bootstyle="success", command=guardar_orden).pack(side="left", padx=5)
        ttk.Button(frame_btns, text="Cancelar", bootstyle="secondary", command=modal.destroy).pack(side="left", padx=5)