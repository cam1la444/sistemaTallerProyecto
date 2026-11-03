"""Acceso a SQL Server."""
import configparser
import os
import pyodbc

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _cadena_conexion():
    """Arma la cadena de conexión leyendo config.ini.
    Si 'usuario' está vacío, usa la sesión de Windows (sin clave)."""
    cfg = configparser.ConfigParser()
    if not cfg.read(os.path.join(RAIZ, "config.ini")):
        raise FileNotFoundError("Falta config.ini: copie config.ini.example y complételo.")
    s = cfg["sqlserver"]
    cadena = (f"DRIVER={{{s['driver']}}};SERVER={s['servidor']};DATABASE={s['base']};"
              "TrustServerCertificate=yes")
    # OJO: estas son las claves del archivo config.ini (usuario / clave), NO las columnas de la tabla Usuarios
    if s.get("usuario", "").strip():
        clave = s.get("clave", "").replace("}", "}}")      # las llaves protegen claves con ; o }
        return cadena + f";UID={s['usuario']};PWD={{{clave}}}"
    return cadena + ";Trusted_Connection=yes"


def get_connection():
    """Devuelve una conexión nueva (timeout de 5 s para que la app no se congele)."""
    return pyodbc.connect(_cadena_conexion(), timeout=5)


def consultar(sql, params=()):
    """SELECT: devuelve lista de diccionarios. Use siempre ? para los parámetros."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        columnas = [c[0] for c in cur.description]
        return [dict(zip(columnas, fila)) for fila in cur.fetchall()]


def ejecutar(sql, params=()):
    """INSERT / UPDATE / DELETE con commit. Devuelve filas afectadas."""
    with get_connection() as conn:   # el 'with' hace commit o rollback solo
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur.rowcount
