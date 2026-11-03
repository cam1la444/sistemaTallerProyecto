"""Prueba SOLO la conexión a SQL Server y dice qué está pasando. Ejecutar:
    python tools/probar_conexion.py
Sirve para diagnosticar errores de conexión antes de abrir la aplicación."""
import configparser
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import RAIZ, consultar

ruta = os.path.join(RAIZ, "config.ini")
cfg = configparser.ConfigParser()
if not cfg.read(ruta):
    sys.exit("No existe config.ini. Copie config.ini.example como config.ini y complételo.")

s = cfg["sqlserver"]
usa_sql = bool(s.get("usuario", "").strip())
print("Servidor :", s.get("servidor"))
print("Base     :", s.get("base"))
print("Entrada  :", f"usuario SQL '{s['usuario'].strip()}'" if usa_sql
      else "sesión de Windows (usuario y clave vacíos en config.ini)")

try:
    fila = consultar("SELECT @@SERVERNAME AS servidor, DB_NAME() AS base, SUSER_SNAME() AS entro_como")[0]
    print("\nCONEXIÓN CORRECTA ->", fila)
    columnas = [f["COLUMN_NAME"] for f in consultar(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Usuarios'")]
    esperadas = {"id_usuario", "usuario", "nombre", "password_hash", "rol", "activo", "pendiente", "fecha_creacion"}
    if not columnas:
        print("Falta la tabla Usuarios: ejecute sql/01_schema.sql")
    elif not esperadas <= set(columnas):
        print("La tabla Usuarios no tiene las columnas esperadas. Faltan:", sorted(esperadas - set(columnas)))
        print("Ejecute sql/01_schema.sql (si la base tiene el otro esquema, vea la guía: borrar la base y crearla de nuevo).")
    else:
        print("Tabla Usuarios correcta.")
except Exception as e:
    print("\nNO CONECTÓ:", e)
    if not usa_sql:
        print("\nPista: está entrando con la sesión de Windows. Si no está en Windows, o el servidor "
              "no acepta su cuenta de Windows, ponga usuario y clave de SQL en config.ini (por ejemplo sa).")
    sys.exit(1)
