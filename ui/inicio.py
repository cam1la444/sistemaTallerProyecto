"""Pantalla de Inicio (primera que ve el usuario al entrar)."""
from datetime import datetime

import ttkbootstrap as ttk

from core import auth, session

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]

DESCRIPCIONES = {
    "clientes": "Registrar y buscar clientes",
    "ordenes": "Seguimiento de servicios",
    "ventas": "Cobrar y generar facturas",
    "inventario": "Insumos, servicios y stock",
    "reportes": "Ventas del día y estadísticas",
    "usuarios": "Cuentas, roles y accesos",
}


COLUMNAS = 4      # mosaicos por fila en "Accesos rápidos"


def fecha_larga(fecha):
    """Ej.: 'domingo 1 de noviembre de 2026' (sin depender del idioma del sistema)."""
    return f"{DIAS[fecha.weekday()]} {fecha.day} de {MESES[fecha.month - 1]} de {fecha.year}"


class InicioFrame(ttk.Frame):
    def __init__(self, master, ir_a, accesos):
        """ir_a(clave): abre otro módulo. accesos: lista [(clave, texto)] de los módulos permitidos."""
        super().__init__(master, padding=24)
        self.ir_a = ir_a
        self.accesos = accesos

        ttk.Label(self, text="Inicio", font=("", 20, "bold")).pack(anchor="w")
        u = session.usuario_actual
        self.lbl_saludo = ttk.Label(self, text=f"Bienvenido, {u['NombreCompleto']}", font=("", 12))
        self.lbl_saludo.pack(anchor="w", pady=(6, 0))
        self.lbl_fecha = ttk.Label(self, text="")
        self.lbl_fecha.pack(anchor="w", pady=(0, 18))

        self.zona_tarjetas = ttk.Frame(self)           # se llena en al_mostrar (solo administrador)
        self.zona_tarjetas.pack(fill="x")

        ttk.Label(self, text="Accesos rápidos", font=("", 13, "bold")).pack(anchor="w", pady=(18, 8))
        self.zona_accesos = ttk.Frame(self)
        self.zona_accesos.pack(fill="x")
        self._crear_accesos()

    def _crear_accesos(self):
        """Un botón por módulo permitido (excepto Inicio), de 4 en 4."""
        modulos = [(c, t) for c, t in self.accesos if c != "inicio"]
        for i, (clave, texto) in enumerate(modulos):
            marco = ttk.Frame(self.zona_accesos, padding=14, bootstyle="secondary")
            marco.grid(row=i // COLUMNAS, column=i % COLUMNAS, padx=(0, 12), pady=(0, 12), sticky="nsew")
            ttk.Button(marco, text=texto, command=lambda c=clave: self.ir_a(c)).pack(fill="x")
            ttk.Label(marco, text=DESCRIPCIONES.get(clave, ""), bootstyle="inverse-secondary",
                      wraplength=150).pack(anchor="w", pady=(8, 0))
        for col in range(COLUMNAS):
            self.zona_accesos.columnconfigure(col, weight=1, uniform="accesos")

    def al_mostrar(self):
        """Se llama cada vez que se abre Inicio: refresca la fecha y los contadores."""
        self.lbl_fecha.config(text=fecha_larga(datetime.now()) + "  ·  " +
                              session.etiqueta_rol(session.rol_actual()))
        for w in self.zona_tarjetas.winfo_children():
            w.destroy()
        if session.es_admin():
            self._tarjetas_admin()

    def _tarjetas_admin(self):
        try:
            activos, pendientes = auth.contar_usuarios_activos(), auth.contar_pendientes()
        except Exception as e:
            print("Error al contar usuarios:", repr(e))
            activos = pendientes = "—"
        self._tarjeta(0, "Usuarios activos", activos, "info")
        hay_pendientes = isinstance(pendientes, int) and pendientes > 0
        self._tarjeta(1, "Cuentas por aprobar", pendientes, "warning" if hay_pendientes else "secondary",
                      boton=("Revisar", lambda: self.ir_a("usuarios")) if hay_pendientes else None)
        for col in range(2):
            self.zona_tarjetas.columnconfigure(col, weight=1, uniform="tarjetas")

    def _tarjeta(self, columna, titulo, valor, estilo, boton=None):
        marco = ttk.Frame(self.zona_tarjetas, padding=16, bootstyle=estilo)
        marco.grid(row=0, column=columna, padx=(0, 12), sticky="nsew")
        ttk.Label(marco, text=titulo, bootstyle=f"inverse-{estilo}").pack(anchor="w")
        ttk.Label(marco, text=str(valor), font=("", 24, "bold"), bootstyle=f"inverse-{estilo}").pack(anchor="w")
        if boton:
            ttk.Button(marco, text=boton[0], bootstyle="dark", command=boton[1]).pack(anchor="w", pady=(6, 0))
