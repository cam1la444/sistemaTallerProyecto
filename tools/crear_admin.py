"""Crea el usuario administrador inicial (admin / admin123). Ejecutar una vez:
    python tools/crear_admin.py      (después de correr sql/01_schema.sql)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bcrypt
from core.database import consultar, ejecutar

if consultar("SELECT 1 AS x FROM Usuarios WHERE usuario = 'admin'"):
    print("El usuario admin ya existe.")
else:
    hash_ = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
    ejecutar("INSERT INTO Usuarios (usuario, nombre, password_hash, rol) VALUES (?,?,?,?)",
             ("admin", "Administrador General", hash_, "Administrador"))
    print("Listo: usuario admin / clave admin123 (cámbiela después).")
