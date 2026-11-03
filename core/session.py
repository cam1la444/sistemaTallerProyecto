"""Usuario que inició sesión y permisos obtorgados por rol. """

ROLES = ["Administrador", "Vendedor", "Mecanico", "Bodega"]

ROLES_REGISTRO = ["Vendedor", "Mecanico", "Bodega"]

ETIQUETAS_ROL = {"Mecanico": "Mecánico"}

# las pantallas que ve cada rol. Las claves que se encuentra en ui/main_window.py.
PERMISOS = {
    "Administrador": ["inicio", "clientes", "ordenes", "ventas",
                      "inventario", "reportes", "usuarios"],
    "Vendedor":      ["inicio", "clientes", "ordenes", "ventas"],
    "Mecanico":      ["inicio", "clientes", "ordenes"],
    "Bodega":        ["inicio", "inventario"],
}

# Diccionario con las claves: UsuarioID, NombreCompleto, Rol  (None si nadie ha iniciado sesión)
usuario_actual = None


def iniciar(usuario):
    """Guarda al usuario que acaba de iniciar sesión."""
    global usuario_actual
    usuario_actual = usuario


def cerrar():
    """Olvida al usuario actual (cerrar sesión)."""
    global usuario_actual
    usuario_actual = None


def etiqueta_rol(rol):
    """Nombre del rol para mostrar en pantalla (con tilde)."""
    return ETIQUETAS_ROL.get(rol, rol)


def rol_actual():
    """Rol del usuario actual, o None si no hay sesión."""
    return usuario_actual["Rol"] if usuario_actual else None


def es_admin():
    """True si el usuario actual es Administrador."""
    return rol_actual() == "Administrador"


def tiene_acceso(clave_modulo):
    """True si el rol del usuario actual puede abrir ese módulo."""
    if usuario_actual is None:
        return False
    return clave_modulo in PERMISOS.get(usuario_actual["Rol"], [])


def modulos_permitidos():
    """Lista de claves de módulo que el rol actual puede abrir."""
    if usuario_actual is None:
        return []
    return list(PERMISOS.get(usuario_actual["Rol"], []))
