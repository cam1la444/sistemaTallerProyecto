"""Ventanas emergentes de cuentas: crear cuenta (registro), nuevo usuario (administrador) y
cambiar contraseña. Responsable: .

Los tres formularios usan las funciones de core/auth.py; aquí solo está lo visual."""
from tkinter import messagebox

import ttkbootstrap as ttk

from core import auth, session


def _mensaje(etiqueta, texto):
    """Pone un mensaje de error en su etiqueta; si el texto está vacío, la oculta para no dejar huecos."""
    etiqueta.config(text=texto or "")
    if texto:
        etiqueta.grid()
    else:
        etiqueta.grid_remove()


class _VentanaModal(ttk.Toplevel):
    """Ventana emergente centrada sobre la principal que bloquea la de atrás hasta cerrarse.
    Los widgets se van colocando uno debajo de otro con un contador de filas (self._fila)."""

    def __init__(self, master, titulo):
        super().__init__(master=master, title=titulo)
        self.resizable(False, False)
        self.transient(master)
        self.cuerpo = ttk.Frame(self, padding=24)
        self.cuerpo.pack(fill="both", expand=True)
        self.cuerpo.columnconfigure(0, weight=1)
        self._fila = 0
        self.bind("<Escape>", lambda e: self.destroy())

    def _colocar(self, widget, **opciones):
        """Pone el widget en la siguiente fila libre del formulario."""
        widget.grid(row=self._fila, column=0, sticky=opciones.pop("sticky", "w"), **opciones)
        self._fila += 1

    def campo(self, texto, var, validador=None, **opciones):
        """Crea 'etiqueta + entrada + mensaje de error' y devuelve (entrada, etiqueta_de_error).
        Si hay validador, el campo se revisa solo al perder el foco."""
        self._colocar(ttk.Label(self.cuerpo, text=texto))
        entrada = ttk.Entry(self.cuerpo, textvariable=var, width=34, **opciones)
        self._colocar(entrada, sticky="ew", pady=(0, 8))
        error = ttk.Label(self.cuerpo, text="", bootstyle="danger", wraplength=330)
        self._colocar(error, pady=(0, 6))
        error.grid_remove()
        if validador:
            entrada.bind("<FocusOut>", lambda e: self._revisar(var, validador, error), add="+")
        return entrada, error

    def botones(self, texto_guardar, comando):
        """Fila final con 'Cancelar' y el botón principal. Devuelve el botón principal."""
        self.err_general = ttk.Label(self.cuerpo, text="", bootstyle="danger", wraplength=330)
        self._colocar(self.err_general, pady=(0, 6))
        self.err_general.grid_remove()
        fila = ttk.Frame(self.cuerpo)
        self._colocar(fila, sticky="e")
        ttk.Button(fila, text="Cancelar", bootstyle="secondary", command=self.destroy).pack(side="left", padx=6)
        boton = ttk.Button(fila, text=texto_guardar, bootstyle="primary", command=comando)
        boton.pack(side="left")
        self.bind("<Return>", lambda e: comando())
        return boton

    def mostrar(self):
        """Centra la ventana sobre su padre y la hace modal. Llamar al terminar de crear los campos."""
        self.update_idletasks()
        padre = self.master.winfo_toplevel()
        x = padre.winfo_rootx() + (padre.winfo_width() - self.winfo_reqwidth()) // 2
        y = padre.winfo_rooty() + (padre.winfo_height() - self.winfo_reqheight()) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.wait_visibility()      # en Linux, grab_set falla si la ventana aún no es visible
        self.grab_set()
        self.focus_set()

    @staticmethod
    def _revisar(var, validador, etiqueta_error):
        """Muestra u oculta el mensaje de error de un campo. Devuelve True si el dato es válido."""
        error = validador(var.get())[1]
        _mensaje(etiqueta_error, error)
        return error is None


class FormularioUsuario(_VentanaModal):
    """modo='registro': la persona se registra sola desde el login (queda pendiente de aprobación).
    modo='admin': el administrador crea una cuenta ya activa, con cualquier rol."""

    def __init__(self, master, modo="registro", al_guardar=None):
        assert modo in ("registro", "admin")
        titulo = "Crear cuenta" if modo == "registro" else "Nuevo usuario"
        super().__init__(master, titulo)
        self.modo = modo
        self.al_guardar = al_guardar

        self._colocar(ttk.Label(self.cuerpo, text=titulo, font=("", 16, "bold")))
        aviso = ("Un administrador debe aprobar su cuenta antes de que pueda ingresar."
                 if modo == "registro" else "La cuenta queda activa de inmediato.")
        self._colocar(ttk.Label(self.cuerpo, text=aviso, wraplength=330), pady=(0, 12))

        self.var_nombre = ttk.StringVar()
        self.var_usuario = ttk.StringVar()
        self.var_rol = ttk.StringVar()
        self.var_clave = ttk.StringVar()
        self.var_confirmar = ttk.StringVar()

        self.ent_nombre, self.err_nombre = self.campo("Nombre completo", self.var_nombre,
                                                      auth.validar_nombre_completo)
        self.ent_nombre.bind("<FocusOut>", self._sugerir_usuario, add="+")     # menos digitación
        self.ent_usuario, self.err_usuario = self.campo("Usuario", self.var_usuario, auth.validar_usuario)

        # Rol: lista desplegable (no se escribe). En la BD se guarda "Mecanico"; en pantalla "Mecánico".
        roles = session.ROLES_REGISTRO if modo == "registro" else session.ROLES
        self._rol_por_texto = {session.etiqueta_rol(r): r for r in roles}
        self._colocar(ttk.Label(self.cuerpo, text="Rol"))
        self.cmb_rol = ttk.Combobox(self.cuerpo, textvariable=self.var_rol, state="readonly", width=32,
                                    values=list(self._rol_por_texto))
        self._colocar(self.cmb_rol, sticky="ew", pady=(0, 10))
        self.cmb_rol.current(0)

        if modo == "registro":
            self.ent_clave, self.err_clave = self.campo("Contraseña (mínimo 8, con letras y números)",
                                                        self.var_clave, auth.validar_clave, show="•")
            self.ent_confirmar, self.err_confirmar = self.campo("Repetir contraseña", self.var_confirmar,
                                                                self._validar_confirmacion, show="•")
        else:
            # El administrador no inventa la clave: se genera una temporal y se la entrega al empleado
            self.var_clave.set(auth.generar_clave_temporal())
            self.ent_clave, self.err_clave = self.campo("Contraseña temporal", self.var_clave, auth.validar_clave)
            self._colocar(ttk.Button(self.cuerpo, text="Generar otra", bootstyle="info-outline",
                                     command=self._otra_clave), pady=(0, 6))

        self.btn_guardar = self.botones("Crear cuenta" if modo == "registro" else "Crear usuario", self._guardar)
        self.ent_nombre.focus()
        self.mostrar()

    def _sugerir_usuario(self, _evento=None):
        """Si el usuario está vacío, propone uno a partir del nombre (inicial + apellido)."""
        if not self.var_usuario.get().strip():
            self.var_usuario.set(auth.sugerir_usuario(self.var_nombre.get()))

    def _otra_clave(self):
        self.var_clave.set(auth.generar_clave_temporal())
        _mensaje(self.err_clave, "")

    def _validar_confirmacion(self, texto):
        """Mismo formato (valor, error) que los demás validadores."""
        if texto != self.var_clave.get():
            return None, "Las contraseñas no coinciden"
        return texto, None

    def _validar_todo(self):
        """Revisa todos los campos a la vez para mostrar todos los errores juntos."""
        resultados = [
            self._revisar(self.var_nombre, auth.validar_nombre_completo, self.err_nombre),
            self._revisar(self.var_usuario, auth.validar_usuario, self.err_usuario),
            self._revisar(self.var_clave, auth.validar_clave, self.err_clave),
        ]
        if self.modo == "registro":
            resultados.append(self._revisar(self.var_confirmar, self._validar_confirmacion, self.err_confirmar))
        return all(resultados)

    def _guardar(self):
        _mensaje(self.err_general, "")
        if not self._validar_todo():
            return
        rol = self._rol_por_texto[self.var_rol.get()]
        self.btn_guardar.config(state="disabled")          # evita doble clic
        try:
            if self.modo == "registro":
                auth.registrar_cuenta(self.var_nombre.get(), self.var_usuario.get(), self.var_clave.get(), rol)
            else:
                auth.crear_usuario(self.var_nombre.get(), self.var_usuario.get(), self.var_clave.get(), rol)
        except auth.ErrorUsuario as e:                     # regla de negocio: se muestra en el formulario
            _mensaje(self.err_general, str(e))
            self.btn_guardar.config(state="normal")
            return
        except Exception as e:                             # error de base de datos u otro inesperado
            print("Error al guardar usuario:", repr(e))
            _mensaje(self.err_general, "No se pudo guardar en la base de datos. Intente de nuevo.")
            self.btn_guardar.config(state="normal")
            return

        if self.modo == "registro":
            messagebox.showinfo("Cuenta creada",
                                "Su cuenta quedó pendiente de aprobación.\n"
                                "Cuando un administrador la active podrá iniciar sesión.", parent=self)
        else:
            messagebox.showinfo("Usuario creado",
                                f"Usuario: {self.var_usuario.get().strip().lower()}\n"
                                f"Contraseña temporal: {self.var_clave.get()}\n\n"
                                "Entregue estos datos al empleado y pídale que cambie su contraseña.",
                                parent=self)
        callback = self.al_guardar
        self.destroy()
        if callback:
            callback()


class CambiarClave(_VentanaModal):
    """El usuario con la sesión abierta cambia su propia contraseña."""

    def __init__(self, master):
        super().__init__(master, "Cambiar contraseña")
        self._colocar(ttk.Label(self.cuerpo, text="Cambiar contraseña", font=("", 16, "bold")), pady=(0, 12))

        self.var_actual = ttk.StringVar()
        self.var_nueva = ttk.StringVar()
        self.var_confirmar = ttk.StringVar()
        self.ent_actual, self.err_actual = self.campo("Contraseña actual", self.var_actual, show="•")
        self.ent_nueva, self.err_nueva = self.campo("Contraseña nueva (mínimo 8, con letras y números)",
                                                    self.var_nueva, auth.validar_clave, show="•")
        self.ent_confirmar, self.err_confirmar = self.campo("Repetir contraseña nueva", self.var_confirmar,
                                                            self._validar_confirmacion, show="•")
        self.btn = self.botones("Guardar", self._guardar)
        self.ent_actual.focus()
        self.mostrar()

    def _validar_confirmacion(self, texto):
        if texto != self.var_nueva.get():
            return None, "Las contraseñas no coinciden"
        return texto, None

    def _guardar(self):
        _mensaje(self.err_general, "")
        if not self.var_actual.get():
            _mensaje(self.err_actual, "Escriba su contraseña actual")
            return
        _mensaje(self.err_actual, "")
        nueva_ok = self._revisar(self.var_nueva, auth.validar_clave, self.err_nueva)
        confirmar_ok = self._revisar(self.var_confirmar, self._validar_confirmacion, self.err_confirmar)
        if not (nueva_ok and confirmar_ok):
            return
        self.btn.config(state="disabled")
        try:
            auth.cambiar_clave_propia(self.var_actual.get(), self.var_nueva.get())
        except auth.ErrorUsuario as e:
            _mensaje(self.err_general, str(e))
            self.btn.config(state="normal")
            return
        except Exception as e:
            print("Error al cambiar contraseña:", repr(e))
            _mensaje(self.err_general, "No se pudo guardar en la base de datos. Intente de nuevo.")
            self.btn.config(state="normal")
            return
        messagebox.showinfo("Listo", "Su contraseña fue actualizada.", parent=self)
        self.destroy()
