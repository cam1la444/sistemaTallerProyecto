"""Pantalla de inicio de sesión."""
import ttkbootstrap as ttk

from core import session
from core.auth import MENSAJES_LOGIN, verificar_login
from ui.registro import FormularioUsuario

MAX_INTENTOS = 3
SEGUNDOS_BLOQUEO = 30


class LoginFrame(ttk.Frame):
    def __init__(self, master, al_ingresar):
        super().__init__(master)
        self.al_ingresar = al_ingresar
        self.intentos = 0

        caja = ttk.Frame(self, padding=30)
        caja.place(relx=0.5, rely=0.5, anchor="center")
        ttk.Label(caja, text="Taller Pro", font=("", 24, "bold")).pack()
        ttk.Label(caja, text="Inicie sesión para continuar").pack(pady=(0, 20))

        self.var_usuario = ttk.StringVar()
        self.var_clave = ttk.StringVar()
        ttk.Label(caja, text="Usuario").pack(anchor="w")
        self.ent_usuario = ttk.Entry(caja, textvariable=self.var_usuario, width=30)
        self.ent_usuario.pack(pady=(0, 10))
        ttk.Label(caja, text="Contraseña").pack(anchor="w")
        self.ent_clave = ttk.Entry(caja, textvariable=self.var_clave, show="•", width=30)
        self.ent_clave.pack(pady=(0, 4))

        self.var_mostrar = ttk.BooleanVar(value=False)
        ttk.Checkbutton(caja, text="Mostrar contraseña", variable=self.var_mostrar,
                        command=self._alternar_clave, bootstyle="round-toggle").pack(anchor="w", pady=(0, 10))

        self.lbl_error = ttk.Label(caja, text="", bootstyle="danger", wraplength=260)
        self.lbl_error.pack(pady=(0, 10))
        self.btn = ttk.Button(caja, text="Ingresar", bootstyle="primary", command=self.ingresar, width=28)
        self.btn.pack()

        ttk.Separator(caja).pack(fill="x", pady=16)
        ttk.Label(caja, text="¿Es nuevo en el taller?").pack()
        ttk.Button(caja, text="Crear cuenta", bootstyle="link", command=self.abrir_registro).pack()

        self.ent_usuario.focus()
        self.ent_usuario.bind("<Return>", lambda e: self.ent_clave.focus())
        self.ent_clave.bind("<Return>", lambda e: self.ingresar())

    def _alternar_clave(self):
        """Muestra u oculta la contraseña (evita errores al escribirla)."""
        self.ent_clave.config(show="" if self.var_mostrar.get() else "•")

    def abrir_registro(self):
        """Abre el formulario de registro; la cuenta quedará pendiente de aprobación."""
        FormularioUsuario(self.winfo_toplevel(), modo="registro")

    def ingresar(self):
        if str(self.btn.cget("state")) == "disabled":      # bloqueado por intentos fallidos
            return
        usuario, clave = self.var_usuario.get().strip(), self.var_clave.get()
        if not usuario or not clave:
            self.lbl_error.config(text="Escriba usuario y contraseña")
            return
        try:
            datos, codigo = verificar_login(usuario, clave)
        except Exception as e:
            print("Error de BD:", repr(e))
            self.lbl_error.config(text="No se pudo consultar la base de datos. Revise config.ini y que "
                                       "haya ejecutado los scripts SQL.")
            return

        if datos:
            session.iniciar(datos)
            self.al_ingresar()
            return

        self.var_clave.set("")
        self.ent_clave.focus()
        if codigo != "credenciales":
            # La contraseña era correcta pero la cuenta está pendiente o desactivada: no cuenta como intento fallido
            self.lbl_error.config(text=MENSAJES_LOGIN[codigo])
            return
        self.intentos += 1
        if self.intentos >= MAX_INTENTOS:
            self.bloquear(SEGUNDOS_BLOQUEO)
        else:
            self.lbl_error.config(
                text=f"{MENSAJES_LOGIN['credenciales']}. Intentos restantes: {MAX_INTENTOS - self.intentos}")

    def bloquear(self, segundos):
        """Deshabilita el botón y cuenta hacia atrás sin congelar la ventana."""
        if segundos > 0:
            self.btn.config(state="disabled")
            self.lbl_error.config(text=f"Demasiados intentos. Espere {segundos} s")
            self.after(1000, lambda: self.bloquear(segundos - 1))
        else:
            self.intentos = 0
            self.btn.config(state="normal")
            self.lbl_error.config(text="")
