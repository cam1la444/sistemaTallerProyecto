"""Módulo Ventas.
Punto de Venta, cobro de servicios, adición de insumos, cálculo de IVA y generación de factura."""
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkinter as tk
from tkinter import messagebox
from core.database import consultar, get_connection

class VentasFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=20)
        
        #titulo principal
        ttk.Label(self, text="Punto de Venta y Facturación", font=("", 20, "bold")).pack(anchor="w", pady=(0, 10))
        
        # Contenedor principal de dos paneles
        panel_principal = ttk.Frame(self)
        panel_principal.pack(fill="both", expand=True, pady=5)
        
        panel_principal.columnconfigure(0, weight=3)
        panel_principal.columnconfigure(1, weight=2)
        panel_principal.rowconfigure(0, weight=1)
        
        # -------------------------------------------------------------
        # PANEL IZQUIERDO: Selección de Cliente, Servicios e Insumos
        # -------------------------------------------------------------
        izq_frame = ttk.Frame(panel_principal, padding=5)
        izq_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        #Selección de Cliente
        ttk.Label(izq_frame, text="1. Seleccionar Cliente:", font=("", 11, "bold")).pack(anchor="w", pady=(0, 5))
        
        f_cli = ttk.Frame(izq_frame)
        f_cli.pack(fill="x", pady=5)
        ttk.Label(f_cli, text="Cliente:").pack(side="left", padx=(0, 5))
        
        self.combo_clientes = ttk.Combobox(f_cli, state="readonly", width=42)
        self.combo_clientes.pack(side="left", padx=5)
        self.combo_clientes.bind("<<ComboboxSelected>>", self.cargar_datos_cliente)
        
        #servicios realizados / del taller
        ttk.Label(izq_frame, text="2. Servicios a Facturar:", font=("", 11, "bold")).pack(anchor="w", pady=(10, 5))
        
        cols_serv = ("id", "servicio", "precio")
        self.tabla_servicios = ttk.Treeview(izq_frame, columns=cols_serv, show="headings", height=5)
        self.tabla_servicios.heading("id", text="ID")
        self.tabla_servicios.heading("servicio", text="Servicio / Descripción")
        self.tabla_servicios.heading("precio", text="Precio ($)")
        self.tabla_servicios.column("id", width=40, anchor="center")
        self.tabla_servicios.column("servicio", width=220)
        self.tabla_servicios.column("precio", width=80, anchor="e")
        self.tabla_servicios.pack(fill="x", pady=5)
        self.tabla_servicios.bind("<Double-1>", lambda e: self.agregar_servicio_factura())
        
        ttk.Button(izq_frame, text="Agregar Servicio al Cobro", bootstyle="info-outline", command=self.agregar_servicio_factura).pack(anchor="w", pady=2)
        
        #insumos adicionales (Repuestos solicitados en el momento)
        ttk.Label(izq_frame, text="3. Agregar Insumos Adicionales (Repuestos):", font=("", 11, "bold")).pack(anchor="w", pady=(15, 5))
        
        f_ins = ttk.Frame(izq_frame)
        f_ins.pack(fill="x", pady=5)
        
        self.combo_insumos = ttk.Combobox(f_ins, state="readonly", width=28)
        self.combo_insumos.pack(side="left", padx=(0, 5))
        
        ttk.Label(f_ins, text="Cant:").pack(side="left", padx=5)
        self.spin_cantidad = ttk.Spinbox(f_ins, from_=1, to=100, width=5)
        self.spin_cantidad.set(1)
        self.spin_cantidad.pack(side="left", padx=5)
        
        ttk.Button(f_ins, text="Agregar Insumo", bootstyle="success-outline", command=self.agregar_insumo_factura).pack(side="left", padx=5)
        
        # -------------------------------------------------------------
        # PANEL DERECHO: Detalle de Factura / Carrito y Totales
        # -------------------------------------------------------------
        der_frame = ttk.Labelframe(panel_principal, text=" Detalle de Factura / Cobro Unificado ", padding=10)
        der_frame.grid(row=0, column=1, sticky="nsew")
        
        cols_fac = ("tipo", "item", "cant", "sub")
        self.tabla_carrito = ttk.Treeview(der_frame, columns=cols_fac, show="headings", height=12)
        self.tabla_carrito.heading("tipo", text="Tipo")
        self.tabla_carrito.heading("item", text="Descripción")
        self.tabla_carrito.heading("cant", text="Cant")
        self.tabla_carrito.heading("sub", text="Subtotal")
        self.tabla_carrito.column("tipo", width=60, anchor="center")
        self.tabla_carrito.column("item", width=130)
        self.tabla_carrito.column("cant", width=40, anchor="center")
        self.tabla_carrito.column("sub", width=70, anchor="e")
        self.tabla_carrito.pack(fill="both", expand=True, pady=5)
        
        ttk.Button(der_frame, text="Quitar Ítem Seleccionado", bootstyle="danger-outline", command=self.quitar_item_carrito).pack(anchor="e", pady=5)
        
        #Totales
        frame_totales = ttk.Frame(der_frame, padding=5)
        frame_totales.pack(fill="x", pady=10)
        
        self.lbl_subtotal = ttk.Label(frame_totales, text="Subtotal: $0.00", font=("", 11))
        self.lbl_subtotal.pack(anchor="e", pady=2)
        
        self.lbl_descuento = ttk.Label(frame_totales, text="Descuento Frecuente: -$0.00", font=("", 11), bootstyle="success")
        self.lbl_descuento.pack(anchor="e", pady=2)
        
        self.lbl_iva = ttk.Label(frame_totales, text="IVA (13%): $0.00", font=("", 11))
        self.lbl_iva.pack(anchor="e", pady=2)
        
        self.lbl_total = ttk.Label(frame_totales, text="TOTAL: $0.00", font=("", 14, "bold"), bootstyle="primary")
        self.lbl_total.pack(anchor="e", pady=5)
        
        #Boton para cobrar y generar la factura
        ttk.Button(der_frame, text="Cobrar y Generar Factura", bootstyle="success", command=self.procesar_cobro).pack(fill="x", pady=5)

        #Variables internas
        self.carrito = []
        self.clientes_dict = {}
        self.insumos_dict = {}
        self.servicios_dict = {}
        self.cliente_actual_id = None
        self.visitas_cliente = 0
        self.totales_calculados = {"subtotal": 0, "porcentaje_desc": 0, "monto_desc": 0, "monto_iva": 0, "total": 0}

    def al_mostrar(self):
        """Se llama cada vez que el usuario abre esta pantalla: refresca los datos."""
        self.cargar_combos()
        self.limpiar_carrito()

    def cargar_combos(self):
        """Carga clientes, servicios e insumos desde la base de datos usando diccionarios."""
        try:
            # Clientes
            self.combo_clientes.set('')
            self.clientes_dict.clear()
            res_cli = consultar("SELECT id_cliente, nombre, dui, visitas FROM Clientes")
            cli_lista = []
            for c in res_cli:
                texto = f"{c['id_cliente']} - {c['nombre']} (DUI: {c['dui'] or 'N/A'})"
                cli_lista.append(texto)
                self.clientes_dict[texto] = {"id": c['id_cliente'], "visitas": c['visitas']}
            self.combo_clientes['values'] = cli_lista

            # Insumos (Repuestos) con stock disponible
            self.combo_insumos.set('')
            self.insumos_dict.clear()
            res_ins = consultar("SELECT InsumoID, Codigo, Nombre, PrecioVenta, Stock FROM Insumos WHERE Activo = 1 AND Stock > 0")
            ins_lista = []
            for i in res_ins:
                texto = f"{i['Codigo']} - {i['Nombre']} (${i['PrecioVenta']:.2f} | Stock: {i['Stock']})"
                ins_lista.append(texto)
                self.insumos_dict[texto] = {"id": i['InsumoID'], "nombre": i['Nombre'], "precio": i['PrecioVenta'], "stock": i['Stock']}
            self.combo_insumos['values'] = ins_lista

            # Servicios del taller
            self.servicios_dict.clear()
            res_serv = consultar("SELECT ServicioID, Codigo, Nombre, Precio FROM Servicios WHERE Activo = 1")
            self.tabla_servicios.delete(*self.tabla_servicios.get_children())
            for s in res_serv:
                self.tabla_servicios.insert("", tk.END, values=(s['ServicioID'], s['Nombre'], f"{s['Precio']:.2f}"))
                self.servicios_dict[s['ServicioID']] = {"id": s['ServicioID'], "nombre": s['Nombre'], "precio": s['Precio']}

        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar los datos de ventas:\n{e}")

    def cargar_datos_cliente(self, event):
        """Identifica al cliente seleccionado y sus visitas para el descuento de fidelidad."""
        seleccion = self.combo_clientes.get()
        if not seleccion:
            return
        datos = self.clientes_dict.get(seleccion)
        if datos:
            self.cliente_actual_id = datos["id"]
            self.visitas_cliente = datos["visitas"]
            self.recalcular_totales()

    def agregar_servicio_factura(self):
        """Agrega un servicio seleccionado al carrito de cobro."""
        seleccion = self.tabla_servicios.selection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Seleccione un servicio de la tabla.")
            return
        item = self.tabla_servicios.item(seleccion[0])
        vals = item['values']
        serv_id = vals[0]
        nombre = vals[1]
        precio = float(vals[2])

        self.carrito.append({
            "tipo": "Servicio",
            "id": serv_id,
            "nombre": nombre,
            "cantidad": 1,
            "precio": precio,
            "subtotal": precio
        })
        self.actualizar_tabla_carrito()

    def agregar_insumo_factura(self):
        """Agrega un insumo/repuesto adicional validando el stock."""
        seleccion = self.combo_insumos.get()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Seleccione un insumo del desplegable.")
            return
        datos_ins = self.insumos_dict.get(seleccion)
        try:
            cant = int(self.spin_cantidad.get())
            if cant <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showwarning("Advertencia", "La cantidad debe ser un entero válido.")
            return

        if cant > datos_ins["stock"]:
            messagebox.showwarning("Stock Insuficiente", f"Solo hay {datos_ins['stock']} unidades disponibles de {datos_ins['nombre']}.")
            return

        subtotal = cant * datos_ins["precio"]
        self.carrito.append({
            "tipo": "Insumo",
            "id": datos_ins["id"],
            "nombre": datos_ins["nombre"],
            "cantidad": cant,
            "precio": datos_ins["precio"],
            "subtotal": subtotal
        })
        self.actualizar_tabla_carrito()

    def quitar_item_carrito(self):
        """Elimina un ítem del carrito actual."""
        seleccion = self.tabla_carrito.selection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Seleccione el ítem del carrito que desea quitar.")
            return
        index = self.tabla_carrito.index(seleccion[0])
        del self.carrito[index]
        self.actualizar_tabla_carrito()

    def actualizar_tabla_carrito(self):
        """Refresca la tabla del carrito y actualiza los cálculos."""
        self.tabla_carrito.delete(*self.tabla_carrito.get_children())
        for item in self.carrito:
            self.tabla_carrito.insert("", tk.END, values=(item["tipo"], item["nombre"], item["cantidad"], f"${item['subtotal']:.2f}"))
        self.recalcular_totales()

    def recalcular_totales(self):
        """Calcula subtotal, descuento (25% cada 5 visitas), IVA y total."""
        subtotal = sum(item["subtotal"] for item in self.carrito)

        #Regla de descuento del 25% en las visitas
        porcentaje_desc = 0.0
        if self.visitas_cliente > 0 and (self.visitas_cliente + 1) % 5 == 0:
            porcentaje_desc = 25.0

        monto_desc = subtotal * (porcentaje_desc / 100.0)

        # Obtener IVA desde la tabla Configuración
        iva_porcentaje = 0.13
        try:
            res_iva = consultar("SELECT valor FROM Configuracion WHERE clave = 'IVA'")
            if res_iva:
                iva_porcentaje = float(res_iva[0]['valor'])
        except Exception:
            pass

        base_imponible = subtotal - monto_desc
        monto_iva = base_imponible * iva_porcentaje
        total = base_imponible + monto_iva

        # Mostrar en interfaz
        self.lbl_subtotal.config(text=f"Subtotal: ${subtotal:.2f}")
        self.lbl_descuento.config(text=f"Descuento Frecuente ({porcentaje_desc}%): -${monto_desc:.2f}")
        self.lbl_iva.config(text=f"IVA ({int(iva_porcentaje*100)}%): ${monto_iva:.2f}")
        self.lbl_total.config(text=f"TOTAL: ${total:.2f}")

        self.totales_calculados = {
            "subtotal": subtotal,
            "porcentaje_desc": porcentaje_desc,
            "monto_desc": monto_desc,
            "monto_iva": monto_iva,
            "total": total
        }

    def limpiar_carrito(self):
        self.carrito.clear()
        self.cliente_actual_id = None
        self.visitas_cliente = 0
        if self.combo_clientes['values']:
            self.combo_clientes.set('')
        self.actualizar_tabla_carrito()

    def procesar_cobro(self):
        """Registra la factura usando diccionarios y suma una visita al cliente."""
        if not self.cliente_actual_id:
            messagebox.showwarning("Advertencia", "Debe seleccionar un cliente antes de procesar el cobro.")
            return
        if not self.carrito:
            messagebox.showwarning("Advertencia", "El carrito de cobro está vacío.")
            return

        totales = self.totales_calculados

        try:
            with get_connection() as cn:
                cur = cn.cursor()
                
                #numero de factura consecutivo basado en la tabla Facturas
                cur.execute("SELECT ISNULL(MAX(FacturaID), 0) + 1 FROM Facturas")
                next_id = cur.fetchone()[0]
                num_factura = f"FACTURA #{next_id:04d}"

                # Insertar Cabecera
                sql_fac = """
                    INSERT INTO Facturas (NumeroFactura, id_cliente, UsuarioID, Subtotal, PorcentajeDescuento, MontoDescuento, MontoIVA, Total, Estado)
                    OUTPUT INSERTED.FacturaID
                    VALUES (?, ?, 1, ?, ?, ?, ?, ?, 'Completada')
                """
                cur.execute(sql_fac, (
                    num_factura,
                    self.cliente_actual_id,
                    totales["subtotal"],
                    totales["porcentaje_desc"],
                    totales["monto_desc"],
                    totales["monto_iva"],
                    totales["total"]
                ))
                factura_id = cur.fetchone()[0]

                # Insertar Detalles
                sql_det = """
                    INSERT INTO DetalleFactura (FacturaID, TipoItem, InsumoID, ServicioID, Cantidad, PrecioUnitario)
                    VALUES (?, ?, ?, ?, ?, ?)
                """
                for item in self.carrito:
                    ins_id = item["id"] if item["tipo"] == "Insumo" else None
                    serv_id = item["id"] if item["tipo"] == "Servicio" else None
                    cur.execute(sql_det, (
                        factura_id,
                        item["tipo"],
                        ins_id,
                        serv_id,
                        item["cantidad"],
                        item["precio"]
                    ))

                # Incrementar las visitas del cliente
                cur.execute("UPDATE Clientes SET visitas = visitas + 1 WHERE id_cliente = ?", (self.cliente_actual_id,))
                
                cn.commit()

            messagebox.showinfo("Venta Exitosa", f"Se ha generado la {num_factura} por un total de ${totales['total']:.2f}.")
            self.limpiar_carrito()
            self.cargar_combos()

        except Exception as ex:
            messagebox.showerror("Error de Base de Datos", f"No se pudo completar el cobro:\n{ex}")