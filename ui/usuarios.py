"""Módulo Usuarios (solo Administrador)"""
from tkinter import messagebox

import ttkbootstrap as ttk

from core import auth, session
from ui.registro import FormularioUsuario

FILTROS = ["Todos", "Pendientes", "Activos", "Inactivos"]
ESTADO_POR_FILTRO = {"Pendientes": "Pendiente", "Activos": "Activo", "Inactivos": "Inactivo"}


class UsuariosFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=20)
        self.todos = []          # todos los usuarios leídos de la BD
        self.filas = {}          # iid de la tabla (texto) -> diccionario del usuario (los que pasan el filtro)

        # ---- encabezado ----
        cabecera = ttk.Frame(self)
        cabecera.pack(fill="x")
        ttk.Label(cabecera, text="Usuarios", font=("", 20, "bold")).pack(side="left")
        ttk.Button(cabecera, text="+ Nuevo usuario", bootstyle="primary", command=self.nuevo).pack(side="right")

        filtros = ttk.Frame(self)
        filtros.pack(fill="x", pady=(12, 8))
        ttk.Label(filtros, text="Mostrar:").pack(side="left")
        self.var_filtro = ttk.StringVar(value=FILTROS[0])
        cmb = ttk.Combobox(filtros, textvariable=self.var_filtro, values=FILTROS, state="readonly", width=12)
        cmb.pack(side="left", padx=8)
        cmb.bind("<<ComboboxSelected>>", lambda e: self.pintar())
        self.lbl_total = ttk.Label(filtros, text="")
        self.lbl_total.pack(side="right")

        # ---- tabla ----
        marco = ttk.Frame(self)
        marco.pack(fill="both", expand=True)
        columnas = ("usuario", "nombre", "rol", "estado", "creado")
        self.tabla = ttk.Treeview(marco, columns=columnas, show="headings", selectmode="browse")
        for col, texto, ancho in (("usuario", "Usuario", 130), ("nombre", "Nombre completo", 240),
                                  ("rol", "Rol", 120), ("estado", "Estado", 100), ("creado", "Creado", 120)):
            self.tabla.heading(col, text=texto)
            self.tabla.column(col, width=ancho, anchor="w")
        barra = ttk.Scrollbar(marco, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=barra.set)
        self.tabla.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        colores = ttk.Style().colors
        self.tabla.tag_configure("Pendiente", foreground=colores.warning)
        self.tabla.tag_configure("Inactivo", foreground=colores.secondary)
        self.tabla.bind("<<TreeviewSelect>>", lambda e: self.actualizar_botones())

        # ---- acciones sobre la fila seleccionada ----
        acciones = ttk.Frame(self)
        acciones.pack(fill="x", pady=(12, 0))
        self.btn_aprobar = ttk.Button(acciones, text="Aprobar cuenta", bootstyle="success", command=self.aprobar)
        self.btn_aprobar.pack(side="left", padx=(0, 8))
        self.btn_estado = ttk.Button(acciones, text="Desactivar", bootstyle="warning-outline", command=self.alternar_activo)
        self.btn_estado.pack(side="left", padx=(0, 8))
        self.btn_clave = ttk.Button(acciones, text="Restablecer contraseña", bootstyle="info-outline",
                                    command=self.restablecer_clave)
        self.btn_clave.pack(side="left", padx=(0, 24))

        ttk.Label(acciones, text="Rol:").pack(side="left")
        self.var_rol = ttk.StringVar()
        self._rol_por_texto = {session.etiqueta_rol(r): r for r in session.ROLES}
        self.cmb_rol = ttk.Combobox(acciones, textvariable=self.var_rol, values=list(self._rol_por_texto),
                                    state="readonly", width=14)
        self.cmb_rol.pack(side="left", padx=8)
        self.btn_rol = ttk.Button(acciones, text="Cambiar rol", bootstyle="info-outline", command=self.cambiar_rol)
        self.btn_rol.pack(side="left")

        self.lbl_ayuda = ttk.Label(self, text="")
        self.lbl_ayuda.pack(anchor="w", pady=(8, 0))
        self.actualizar_botones()

    # ------------------------------------------------------------------ datos
    def al_mostrar(self):
        """Se llama cada vez que el usuario abre esta pantalla: recarga la tabla desde la BD."""
        self.recargar()

    def recargar(self):
        try:
            self.todos = auth.listar_usuarios()
        except auth.ErrorUsuario as e:
            messagebox.showwarning("Acceso denegado", str(e), parent=self)
            self.todos = []
        except Exception as e:
            print("Error al listar usuarios:", repr(e))
            messagebox.showerror("Error", "No se pudo leer la lista de usuarios de la base de datos.", parent=self)
            self.todos = []
        self.pintar()

    def pintar(self):
        """Llena la tabla aplicando el filtro elegido y conserva la selección si sigue visible."""
        seleccionado = self.id_seleccionado()
        self.tabla.delete(*self.tabla.get_children())
        self.filas = {}
        estado = ESTADO_POR_FILTRO.get(self.var_filtro.get())
        for f in self.todos:
            if estado and f["Estado"] != estado:
                continue
            iid = str(f["UsuarioID"])
            self.filas[iid] = f
            creado = str(f["FechaCreacion"] or "")[:10]
            self.tabla.insert("", "end", iid=iid, tags=(f["Estado"],),
                              values=(f["NombreUsuario"], f["NombreCompleto"], session.etiqueta_rol(f["Rol"]),
                                      f["Estado"], creado))
        if seleccionado is not None and str(seleccionado) in self.filas:
            self.tabla.selection_set(str(seleccionado))
        pendientes = sum(1 for f in self.todos if f["Estado"] == "Pendiente")
        texto = f"{len(self.filas)} de {len(self.todos)} usuarios"
        self.lbl_total.config(text=texto + (f"   |   {pendientes} por aprobar" if pendientes else ""))
        self.actualizar_botones()

    def seleccionada(self):
        """Diccionario del usuario seleccionado, o None."""
        sel = self.tabla.selection()
        return self.filas.get(sel[0]) if sel else None

    def id_seleccionado(self):
        f = self.seleccionada()
        return f["UsuarioID"] if f else None

    # ------------------------------------------------------------------ botones
    def actualizar_botones(self):
        """Activa solo las acciones que tienen sentido para la fila elegida."""
        f = self.seleccionada()
        propio = bool(f) and f["UsuarioID"] == session.usuario_actual["UsuarioID"]
        pendiente = bool(f) and f["Estado"] == "Pendiente"
        self._estado(self.btn_aprobar, pendiente)
        self._estado(self.btn_estado, bool(f) and not propio)
        self._estado(self.btn_clave, bool(f))
        self._estado(self.btn_rol, bool(f) and not propio)
        self.cmb_rol.config(state="readonly" if f and not propio else "disabled")
        if f:
            self.var_rol.set(session.etiqueta_rol(f["Rol"]))
            if pendiente:
                self.btn_estado.config(text="Rechazar")          # rechazar = dejar la cuenta desactivada
            else:
                self.btn_estado.config(text="Desactivar" if f["Activo"] else "Activar")
            self.lbl_ayuda.config(text="Su propia cuenta no se puede desactivar ni cambiar de rol." if propio else "")
        else:
            self.var_rol.set("")
            self.lbl_ayuda.config(text="Seleccione un usuario de la lista.")

    @staticmethod
    def _estado(boton, activo):
        boton.config(state="normal" if activo else "disabled")

    def _ejecutar(self, accion, *args):
        """Ejecuta una acción de auth mostrando los errores sin cerrar la aplicación.
        Devuelve (True, resultado) si salió bien."""
        try:
            resultado = accion(*args)
        except auth.ErrorUsuario as e:
            messagebox.showwarning("No se pudo completar", str(e), parent=self)
            return False, None
        except Exception as e:
            print("Error en acción de usuarios:", repr(e))
            messagebox.showerror("Error", "Ocurrió un problema con la base de datos. Intente de nuevo.", parent=self)
            return False, None
        return True, resultado

    def nuevo(self):
        FormularioUsuario(self.winfo_toplevel(), modo="admin", al_guardar=self.recargar)

    def aprobar(self):
        f = self.seleccionada()
        if f and self._ejecutar(auth.aprobar, f["UsuarioID"])[0]:
            self.recargar()

    def alternar_activo(self):
        f = self.seleccionada()
        if not f:
            return
        # Una cuenta pendiente se rechaza (queda desactivada); una inactiva se activa; una activa se desactiva
        activar = (not f["Activo"]) and f["Estado"] != "Pendiente"
        if not activar:
            verbo = "Rechazar" if f["Estado"] == "Pendiente" else "Desactivar"
            if not messagebox.askyesno(f"{verbo} cuenta", f"¿{verbo} la cuenta de {f['NombreCompleto']}?\n"
                                       "No podrá iniciar sesión.", parent=self):
                return
        if self._ejecutar(auth.cambiar_activo, f["UsuarioID"], activar)[0]:
            self.recargar()

    def cambiar_rol(self):
        f = self.seleccionada()
        if not f:
            return
        rol = self._rol_por_texto.get(self.var_rol.get())
        if rol == f["Rol"]:
            return
        if self._ejecutar(auth.cambiar_rol, f["UsuarioID"], rol)[0]:
            self.recargar()

    def restablecer_clave(self):
        f = self.seleccionada()
        if not f or not messagebox.askyesno(
                "Restablecer contraseña", f"¿Generar una contraseña temporal para {f['NombreCompleto']}?\n"
                                          "La contraseña actual dejará de funcionar.", parent=self):
            return
        ok, temporal = self._ejecutar(auth.restablecer_clave, f["UsuarioID"])
        if ok:
            messagebox.showinfo("Contraseña temporal",
                                f"Usuario: {f['NombreUsuario']}\nContraseña temporal: {temporal}\n\n"
                                "Anótela ahora: no se vuelve a mostrar.", parent=self)
