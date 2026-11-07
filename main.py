"""Punto de entrada. Solo arranca la app; la lógica vive en core/ y ui/."""
import traceback
from tkinter import messagebox

import ttkbootstrap as ttk

from core import session
from ui.login import LoginFrame
from ui.main_window import MainWindow

app = ttk.Window(title="Taller Pro", themename="darkly", size=(1100, 650), minsize=(900, 550))


def error_inesperado(tipo, valor, tb):
    """Si una pantalla falla, se muestra el aviso y la aplicación sigue abierta (no se cierra ni se congela)."""
    traceback.print_exception(tipo, valor, tb)
    messagebox.showerror("Error inesperado", f"Ocurrió un error: {valor}\n\nPuede seguir usando el sistema.")


app.report_callback_exception = error_inesperado
app.style.configure("Treeview", rowheight=28)     # filas mas cómodas en todas las tablas


def limpiar():
    for w in app.winfo_children():
        w.destroy()


def mostrar_login():
    limpiar()
    LoginFrame(app, al_ingresar=mostrar_principal).pack(fill="both", expand=True)


def mostrar_principal():
    limpiar()
    MainWindow(app, al_cerrar_sesion=cerrar_sesion)


def cerrar_sesion():
    session.cerrar()
    mostrar_login()


mostrar_login()
app.mainloop()
