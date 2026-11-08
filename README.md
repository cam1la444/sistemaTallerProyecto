# Taller Pro — Sistema de gestión de taller de autos y motos

## Instalación
1. `python -m pip install -r requirements.txt`  (Linux además: `sudo apt install python3-tk unixodbc-dev` y el driver `msodbcsql18`)
2. Copie `config.ini.example` como `config.ini` y complételo
   (`usuario` y `clave` vacíos = sesión de Windows; con `usuario = sa` usa SQL Server, también en Linux).
3. Ejecute `sql/01_schema.sql` completo en SQL Server (se puede repetir sin perder datos).
4. `python tools/probar_conexion.py` debe decir "CONEXIÓN CORRECTA" y "Tabla Usuarios correcta".
5. `python tools/crear_admin.py` (una sola vez) y luego `python main.py` (usuario `admin`, clave `admin123`).

Pantallas disponibles por ROL. 
|---|---|
| Administrador | Todas, incluida Usuarios |
| Vendedor | Inicio, Clientes, Órdenes, Ventas |
| Mecánico | Inicio, Clientes, Órdenes |
| Bodega | Inicio, Inventario |

Aporte al sistema: - Creacion de roles y accesos. Login y registrarse. Aporte al modulo de cliente (registrar cliente y su vehiculo)
PARTE A:  vistas de la ventana principal, roles, login, usuarios, registrarse, ingresar mediante la aceptacion de admin. LISTO✅

PARTE B: vistas de clientes y sus vehiculos (formularios y treeview), vista de ordenes de reparacion(formularios y treeview), validaciones y busqueda. EN PROCESO 🟠

PARTE C: inventario(servicios e insumos), ventas (reglas de descuento + IVA), factura pdf y reportes. EN PROCESO 🟠


Ejecutar la 02_datos para visualizar el inventario
inventario y ventas funciona en conjunto