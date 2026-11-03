"""Login, registro y administración de usuarios. 
"""
import re
import secrets
import string
import unicodedata

import bcrypt
import pyodbc

from core import session
from core.database import consultar, ejecutar


#mensaje para el login
MENSAJES_LOGIN = {
    "credenciales": "Usuario o contraseña incorrectos",
    "pendiente": "Su cuenta está pendiente de aprobación. Pida a un administrador que la active.",
    "inactivo": "Su cuenta está desactivada. Comuníquese con un administrador.",
}

LARGO_MIN_CLAVE = 8
LARGO_MAX_CLAVE = 72          # límite de bcrypt (72 bytes)


class ErrorUsuario(Exception):
    """Error de validación o de regla de negocio. Su mensaje ya está listo para mostrarse al usuario."""


#validacion en los campos
def validar_nombre_completo(texto):
    """Nombre de la persona: 3 a 100 caracteres, solo letras, espacios, punto, apóstrofo o guion."""
    texto = " ".join((texto or "").split())          # quita espacios repetidos
    if len(texto) < 3:
        return None, "Escriba el nombre completo (mínimo 3 letras)"
    if len(texto) > 100:
        return None, "Máximo 100 caracteres"
    if not re.fullmatch(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' .\-]+", texto):
        return None, "Solo letras y espacios"
    return texto, None


def validar_usuario(texto):
    """Nombre de usuario: 4 a 20 caracteres en minúscula, números, punto o guion bajo."""
    texto = (texto or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9_.]{4,20}", texto):
        return None, "4 a 20 caracteres: letras sin tilde, números, punto o _"
    return texto, None


def validar_clave(texto):
    """Contraseña: 8 a 72 caracteres, con al menos una letra y un número."""
    texto = texto or ""
    if len(texto) < LARGO_MIN_CLAVE:
        return None, f"Mínimo {LARGO_MIN_CLAVE} caracteres"
    if len(texto.encode("utf-8")) > LARGO_MAX_CLAVE:
        return None, f"Máximo {LARGO_MAX_CLAVE} caracteres"
    if not any(c.isalpha() for c in texto) or not any(c.isdigit() for c in texto):
        return None, "Debe tener letras y números"
    return texto, None


def sugerir_usuario(nombre_completo):
    """Propone un usuario: inicial del primer nombre + último apellido (ej. 'Ana Pérez' -> 'aperez')."""
    sin_tildes = unicodedata.normalize("NFKD", nombre_completo or "")
    sin_tildes = "".join(c for c in sin_tildes if not unicodedata.combining(c))
    partes = re.sub(r"[^A-Za-z ]", "", sin_tildes).lower().split()
    if len(partes) < 2:
        return partes[0] if partes else ""
    return (partes[0][0] + partes[-1])[:20]


def generar_clave_temporal(largo=10):
    """Contraseña aleatoria que cumple las reglas (con letras y números)."""
    alfabeto = string.ascii_letters + string.digits
    alfabeto = "".join(c for c in alfabeto if c not in "0OIl1")      # sin caracteres que se confunden
    while True:
        clave = "".join(secrets.choice(alfabeto) for _ in range(largo))
        if validar_clave(clave)[1] is None:
            return clave


def _hash(clave):
    """Convierte la contraseña en un hash bcrypt (nunca se guarda la contraseña en texto)."""
    return bcrypt.hashpw(clave.encode("utf-8"), bcrypt.gensalt()).decode()


#funcion verificar login
def verificar_login(usuario, clave):
    """Devuelve (datos, codigo_error).

    - Si todo está bien: ({'UsuarioID', 'NombreCompleto', 'Rol'}, None)
    - Si falla: (None, 'credenciales' | 'pendiente' | 'inactivo')   -> ver MENSAJES_LOGIN
    Solo se revela que la cuenta está pendiente/desactivada si la contraseña es correcta.
    """
    usuario = (usuario or "").strip().lower()
    filas = consultar(
        "SELECT id_usuario AS UsuarioID, nombre AS NombreCompleto, password_hash AS PasswordHash, "
        "rol AS Rol, activo AS Activo, pendiente AS Pendiente "
        "FROM Usuarios WHERE usuario = ?", (usuario,))
    clave_bytes = (clave or "").encode("utf-8")
    if not filas or len(clave_bytes) > LARGO_MAX_CLAVE:
        return None, "credenciales"
    fila = filas[0]
    if not bcrypt.checkpw(clave_bytes, fila["PasswordHash"].encode("utf-8")):
        return None, "credenciales"
    if fila["Pendiente"]:
        return None, "pendiente"
    if not fila["Activo"]:
        return None, "inactivo"
    return {"UsuarioID": fila["UsuarioID"], "NombreCompleto": fila["NombreCompleto"],
            "Rol": fila["Rol"]}, None


def estado_sesion(usuario_id):
    """Consulta el estado ACTUAL de un usuario (para detectar si lo desactivaron o le cambiaron el rol
    mientras tenía la sesión abierta). Devuelve {'Activo', 'Rol'} o None si ya no existe."""
    filas = consultar("SELECT activo AS Activo, rol AS Rol FROM Usuarios WHERE id_usuario = ?", (usuario_id,))
    return filas[0] if filas else None


#funcion para crear nuevos usuarios oc uentas
def _validar_datos(nombre, usuario, clave):
    """Valida los tres campos y devuelve los valores limpios; lanza ErrorUsuario si algo falla."""
    nombre, error = validar_nombre_completo(nombre)
    if error:
        raise ErrorUsuario("Nombre: " + error)
    usuario, error = validar_usuario(usuario)
    if error:
        raise ErrorUsuario("Usuario: " + error)
    clave, error = validar_clave(clave)
    if error:
        raise ErrorUsuario("Contraseña: " + error)
    return nombre, usuario, clave


def existe_usuario(usuario):
    """True si el nombre de usuario ya está tomado."""
    return bool(consultar("SELECT 1 AS x FROM Usuarios WHERE usuario = ?", (usuario,)))


def _insertar(nombre, usuario, clave, rol, activo, pendiente):
    """INSERT común a registro y creación por administrador."""
    if existe_usuario(usuario):
        raise ErrorUsuario("Ese nombre de usuario ya existe. Elija otro.")
    try:
        ejecutar(
            "INSERT INTO Usuarios (nombre, usuario, password_hash, rol, activo, pendiente) "
            "VALUES (?,?,?,?,?,?)",
            (nombre, usuario, _hash(clave), rol, activo, pendiente))
    except pyodbc.IntegrityError:          # alguien lo creó justo en este instante
        raise ErrorUsuario("Ese nombre de usuario ya existe. Elija otro.")


def registrar_cuenta(nombre, usuario, clave, rol):
    """Registro desde la pantalla de login. La cuenta queda PENDIENTE (no puede entrar) hasta que
    un administrador la apruebe. No permite pedir el rol Administrador."""
    if rol not in session.ROLES_REGISTRO:
        raise ErrorUsuario("Elija un rol válido")
    nombre, usuario, clave = _validar_datos(nombre, usuario, clave)
    _insertar(nombre, usuario, clave, rol, activo=0, pendiente=1)


def _exigir_admin():
    """Todas las operaciones de administración verifican el rol, aunque la pantalla ya lo oculte."""
    if not session.es_admin():
        raise ErrorUsuario("Solo un administrador puede realizar esta acción")


def crear_usuario(nombre, usuario, clave, rol):
    """El administrador crea una cuenta ya activa, con cualquier rol."""
    _exigir_admin()
    if rol not in session.ROLES:
        raise ErrorUsuario("Elija un rol válido")
    nombre, usuario, clave = _validar_datos(nombre, usuario, clave)
    _insertar(nombre, usuario, clave, rol, activo=1, pendiente=0)


#administracion de usuarios solo POR el admin
def estado_texto(fila):
    """'Pendiente', 'Activo' o 'Inactivo' según las banderas de la fila."""
    if fila["Pendiente"]:
        return "Pendiente"
    return "Activo" if fila["Activo"] else "Inactivo"


def listar_usuarios():
    """Todos los usuarios (pendientes primero), cada uno con la clave extra 'Estado'."""
    _exigir_admin()
    filas = consultar(
        "SELECT id_usuario AS UsuarioID, nombre AS NombreCompleto, usuario AS NombreUsuario, rol AS Rol, "
        "activo AS Activo, pendiente AS Pendiente, fecha_creacion AS FechaCreacion "
        "FROM Usuarios ORDER BY pendiente DESC, nombre")
    for fila in filas:
        fila["Estado"] = estado_texto(fila)
    return filas


def contar_usuarios_activos():
    """Cantidad de usuarios que pueden iniciar sesión."""
    return consultar("SELECT COUNT(*) AS n FROM Usuarios WHERE activo = 1")[0]["n"]


def contar_pendientes():
    """Cantidad de cuentas esperando aprobación."""
    return consultar("SELECT COUNT(*) AS n FROM Usuarios WHERE pendiente = 1")[0]["n"]


def _no_es_uno_mismo(usuario_id, accion):
    """Un administrador no puede quitarse a sí mismo el acceso o el rol: así siempre queda al menos
    un administrador activo (el que ejecuta la acción)."""
    if session.usuario_actual and usuario_id == session.usuario_actual["UsuarioID"]:
        raise ErrorUsuario(f"No puede {accion} su propia cuenta")


def aprobar(usuario_id):
    """Activa una cuenta pendiente."""
    _exigir_admin()
    ejecutar("UPDATE Usuarios SET activo = 1, pendiente = 0 WHERE id_usuario = ?", (usuario_id,))


def cambiar_activo(usuario_id, activo):
    """Activa (True) o desactiva (False) una cuenta. Desactivar también sirve para rechazar un pendiente.
    Las cuentas no se borran para conservar el historial (facturas, entradas de stock)."""
    _exigir_admin()
    if not activo:
        _no_es_uno_mismo(usuario_id, "desactivar")
    ejecutar("UPDATE Usuarios SET activo = ?, pendiente = 0 WHERE id_usuario = ?",
             (1 if activo else 0, usuario_id))


def cambiar_rol(usuario_id, rol):
    """Cambia el rol de una cuenta (los permisos salen del rol, ver session.PERMISOS)."""
    _exigir_admin()
    if rol not in session.ROLES:
        raise ErrorUsuario("Elija un rol válido")
    _no_es_uno_mismo(usuario_id, "cambiar el rol de")
    ejecutar("UPDATE Usuarios SET rol = ? WHERE id_usuario = ?", (rol, usuario_id))


def restablecer_clave(usuario_id):
    """Genera una contraseña temporal, la guarda cifrada y la devuelve para entregársela al empleado."""
    _exigir_admin()
    temporal = generar_clave_temporal()
    ejecutar("UPDATE Usuarios SET password_hash = ? WHERE id_usuario = ?", (_hash(temporal), usuario_id))
    return temporal


def cambiar_clave_propia(clave_actual, clave_nueva):
    """El usuario que tiene la sesión abierta cambia su propia contraseña."""
    if session.usuario_actual is None:
        raise ErrorUsuario("No hay una sesión abierta")
    uid = session.usuario_actual["UsuarioID"]
    filas = consultar("SELECT password_hash AS PasswordHash FROM Usuarios WHERE id_usuario = ?", (uid,))
    actual = (clave_actual or "").encode("utf-8")
    if (not filas or len(actual) > LARGO_MAX_CLAVE
            or not bcrypt.checkpw(actual, filas[0]["PasswordHash"].encode("utf-8"))):
        raise ErrorUsuario("La contraseña actual no es correcta")
    clave_nueva, error = validar_clave(clave_nueva)
    if error:
        raise ErrorUsuario("Contraseña nueva: " + error)
    if clave_nueva == clave_actual:
        raise ErrorUsuario("La contraseña nueva debe ser distinta de la actual")
    ejecutar("UPDATE Usuarios SET password_hash = ? WHERE id_usuario = ?", (_hash(clave_nueva), uid))
