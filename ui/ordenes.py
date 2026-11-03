"""Módulo Órdenes de servicio. Responsable:  (reservado, se agrega al final).
Solo edite SU archivo. main_window.py ya importa esta clase."""
import ttkbootstrap as ttk


class OrdenesFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=20)
        ttk.Label(self, text="Órdenes de servicio", font=("", 20, "bold")).pack(anchor="w")
        ttk.Label(self, text="En construcción (responsable: C (reservado, se agrega al final))").pack(anchor="w", pady=10)
        # TODO: aquí va la vista (tabla) y el formulario de este módulo

    def al_mostrar(self):
        """Se llama cada vez que el usuario abre esta pantalla: refresque los datos aquí."""
        pass
