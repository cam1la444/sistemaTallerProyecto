"""Módulo Reportes. Responsable: A.
Solo edite SU archivo. main_window.py ya importa esta clase."""
import ttkbootstrap as ttk


class ReportesFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=20)
        ttk.Label(self, text="Reportes", font=("", 20, "bold")).pack(anchor="w")
        ttk.Label(self, text="En construcción (responsable: A)").pack(anchor="w", pady=10)
        # TODO: aquí va la vista (tabla) y el formulario de este módulo

    def al_mostrar(self):
        """Se llama cada vez que el usuario abre esta pantalla: refresque los datos aquí."""
        pass
