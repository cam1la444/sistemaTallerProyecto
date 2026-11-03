"""Ventana principal: menú lateral según el rol del usuario.

Seguridad: el menú solo muestra los botones permitidos, pero ADEMÁS mostrar() vuelve a comprobar el permiso
y verifica en la base de datos que la cuenta siga activa y con el mismo rol.
"""
import traceback
from tkinter import messagebox

import ttkbootstrap as ttk

from core import auth, session
from ui.clientes import ClientesFrame
from ui.inicio import InicioFrame
from ui.inventario import InventarioFrame
from ui.ordenes import OrdenesFrame
from ui.registro import CambiarClave
from ui.reportes import ReportesFrame
from ui.usuarios import UsuariosFrame
from ui.ventas import VentasFrame

# (clave, texto del menú, clase de la pantalla). La clave es la misma que usa session.PERMISOS.
MODULOS = [
    ("inicio", "Inicio", InicioFrame),
    ("clientes", "Clientes", ClientesFrame),
    ("ordenes", "Órdenes", OrdenesFrame),
    ("ventas", "Ventas", VentasFrame),
    ("inventario", "Inventario", InventarioFrame),
    ("reportes", "Reportes", ReportesFrame),
    ("usuarios", "Usuarios", UsuariosFrame),
]


class MainWindow(ttk.Frame):
    def __init__(self, master, al_cerrar_sesion):
        super().__init__(master)
        self.pack(fill="both", expand=True)
        self.al_cerrar_sesion = al_cerrar_sesion
        self.pantallas = {}          # pantallas ya creadas (se crean la primera vez que se abren)
        self.botones = {}            # clave de módulo -> botón del menú
        self.clave_actual = None
        self.textos = {clave: texto for clave, texto, _ in MODULOS}
        self.clases = {clave: clase for clave, _, clase in MODULOS}

        self._crear_menu()
        derecha = ttk.Frame(self)
        derecha.pack(side="right", fill="both", expand=True)
        self._crear_encabezado(derecha)
        self.contenido = ttk.Frame(derecha)
        self.contenido.pack(fill="both", expand=True)

        self.mostrar("inicio")

    # ------------------------------------------------------------------ construcción
    def _crear_menu(self):
        menu = ttk.Frame(self, padding=12, bootstyle="secondary")
        menu.pack(side="left", fill="y")
        ttk.Label(menu, text="Taller Pro", font=("", 16, "bold"), bootstyle="inverse-secondary").pack(pady=(0, 4))
        u = session.usuario_actual
        ttk.Label(menu, text=f"{u['NombreCompleto']}\n{session.etiqueta_rol(u['Rol'])}",
                  bootstyle="inverse-secondary", justify="center", wraplength=150).pack(pady=(0, 16))

        for clave, texto, _ in MODULOS:
            if session.tiene_acceso(clave):          # el rol decide qué botones existen
                boton = ttk.Button(menu, text=texto, width=18, bootstyle="secondary",
                                   command=lambda c=clave: self.mostrar(c))
                boton.pack(pady=2)
                self.botones[clave] = boton

        ttk.Button(menu, text="Cerrar sesión", width=18, bootstyle="danger-outline",
                   command=self.cerrar_sesion).pack(side="bottom")
        ttk.Button(menu, text="Cambiar contraseña", width=18, bootstyle="light-outline",
                   command=lambda: CambiarClave(self.winfo_toplevel())).pack(side="bottom", pady=(0, 6))

    def _crear_encabezado(self, padre):
        encabezado = ttk.Frame(padre, padding=(24, 14, 24, 0))
        encabezado.pack(fill="x")
        self.lbl_titulo = ttk.Label(encabezado, text="", font=("", 11))
        self.lbl_titulo.pack(side="left")
        u = session.usuario_actual
        ttk.Label(encabezado, text=f"{u['NombreCompleto']}  ·  {session.etiqueta_rol(u['Rol'])}",
                  ).pack(side="right")
        ttk.Separator(padre).pack(fill="x", padx=24, pady=(10, 0))

    # ------------------------------------------------------------------ navegación
    def mostrar(self, clave):
        """Abre un módulo, siempre que la sesión siga vigente y el rol tenga permiso."""
        if not self._sesion_vigente():
            return
        if not session.tiene_acceso(clave):
            messagebox.showwarning("Acceso denegado", "Su rol no tiene permiso para abrir esta pantalla.",
                                   parent=self.winfo_toplevel())
            return
        try:
            if clave not in self.pantallas:
                self.pantallas[clave] = self._crear_pantalla(clave)
        except Exception:
            traceback.print_exc()
            messagebox.showerror("Error", f"No se pudo abrir «{self.textos[clave]}». Revise la consola.",
                                 parent=self.winfo_toplevel())
            return

        if self.clave_actual in self.pantallas:
            self.pantallas[self.clave_actual].pack_forget()
        self.clave_actual = clave
        pantalla = self.pantallas[clave]
        pantalla.pack(fill="both", expand=True)
        self._resaltar(clave)
        try:
            pantalla.al_mostrar()
        except Exception:
            traceback.print_exc()
            messagebox.showerror("Error", f"No se pudieron cargar los datos de «{self.textos[clave]}».",
                                 parent=self.winfo_toplevel())

    def _crear_pantalla(self, clave):
        """Construye la pantalla de un módulo. Inicio recibe además cómo navegar y sus accesos."""
        clase = self.clases[clave]
        if clave == "inicio":
            accesos = [(c, t) for c, t, _ in MODULOS if session.tiene_acceso(c)]
            return clase(self.contenido, ir_a=self.mostrar, accesos=accesos)
        return clase(self.contenido)

    def _resaltar(self, clave):
        """Marca en el menú el módulo abierto y actualiza el título del encabezado."""
        for c, boton in self.botones.items():
            boton.config(bootstyle="primary" if c == clave else "secondary")
        self.lbl_titulo.config(text=self.textos[clave])

    # ------------------------------------------------------------------ sesión
    def _sesion_vigente(self):
        """Comprueba en la BD que la cuenta siga activa y con el mismo rol (otro administrador pudo cambiarla
        mientras esta sesión estaba abierta). Si no es así, cierra la sesión. Si la BD no responde, se deja
        continuar: el módulo que consulte la BD mostrará su propio error."""
        try:
            estado = auth.estado_sesion(session.usuario_actual["UsuarioID"])
        except Exception as e:
            print("No se pudo verificar la sesión:", repr(e))
            return True
        if estado is None or not estado["Activo"]:
            messagebox.showwarning("Sesión cerrada", "Su cuenta fue desactivada. Debe iniciar sesión de nuevo.",
                                   parent=self.winfo_toplevel())
        elif estado["Rol"] != session.usuario_actual["Rol"]:
            messagebox.showinfo("Sesión cerrada", "Su rol fue modificado. Inicie sesión de nuevo para aplicar "
                                "los cambios.", parent=self.winfo_toplevel())
        else:
            return True
        self.al_cerrar_sesion()
        return False

    def cerrar_sesion(self):
        if messagebox.askyesno("Cerrar sesión", "¿Desea cerrar la sesión?", parent=self.winfo_toplevel()):
            self.al_cerrar_sesion()
