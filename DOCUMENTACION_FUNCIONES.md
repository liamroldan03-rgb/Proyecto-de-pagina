# Documentacion de Funciones - Sistema Soporte IT

Este documento resume las funciones implementadas en los archivos creados/modificados para la aplicacion.

## 1) `D:/sistema-soporte/app.py`

### `get_connection()`
- **Objetivo:** abrir conexion SQLite con acceso por nombre de columna (`sqlite3.Row`).
- **Entrada:** ninguna.
- **Salida:** `sqlite3.Connection`.
- **Efectos:** abre handle a `database.db`; quien llama debe cerrar.

### `ensure_column(cursor, table, column, definition)`
- **Objetivo:** garantizar que una columna exista en una tabla.
- **Entradas:**
  - `cursor`: cursor de SQLite activo.
  - `table`: nombre de tabla.
  - `column`: nombre de columna.
  - `definition`: definicion SQL de la columna.
- **Salida:** `None`.
- **Efectos:** si no existe la columna, ejecuta `ALTER TABLE ... ADD COLUMN`.

### `migrate_legacy_passwords(cursor)`
- **Objetivo:** migrar password desde columnas legacy (`contrasena`, variante unicode, variante mojibake) a `password`.
- **Entrada:** `cursor`.
- **Salida:** `None`.
- **Efectos:** actualiza registros de `usuarios` con `password` vacio.

### `hash_plain_passwords(cursor)`
- **Objetivo:** convertir passwords en texto plano a hash seguro (Werkzeug).
- **Entrada:** `cursor`.
- **Salida:** `None`.
- **Efectos:** actualiza `usuarios.password` cuando no detecta prefijo de hash (`scrypt:` o `pbkdf2:`).

### `create_db()`
- **Objetivo:** inicializar y migrar esquema de base.
- **Entrada:** ninguna.
- **Salida:** `None`.
- **Efectos principales:**
  - crea tablas `usuarios` y `tickets` si faltan.
  - agrega columnas nuevas si faltan.
  - migra y hashea passwords legacy.
  - normaliza defaults de tickets existentes.
  - crea/actualiza usuario `admin`.

### `login_required(view)`
- **Objetivo:** decorador de proteccion por sesion.
- **Entrada:** funcion de vista Flask.
- **Salida:** nueva funcion wrapper.
- **Efectos:** redirige a `/login` cuando no existe `session["usuario"]`.

### `wrapped_view(*args, **kwargs)` (interna de `login_required`)
- **Objetivo:** aplicar la validacion de sesion antes de la vista original.
- **Entrada:** argumentos de la vista decorada.
- **Salida:** respuesta Flask (redirect o respuesta original).

### `verify_password(stored_password, candidate)`
- **Objetivo:** validar password enviado contra hash/password almacenado.
- **Entradas:**
  - `stored_password`: valor DB (hash o legacy).
  - `candidate`: password ingresado.
- **Salida:** `bool`.
- **Logica:** usa `check_password_hash` para hashes y comparacion directa para legacy.

### `index()`
- **Ruta:** `GET /`
- **Objetivo:** mostrar inicio o redirigir a dashboard si ya hay sesion.
- **Salida:** render `index.html` o redirect.

### `login()`
- **Ruta:** `GET|POST /login`
- **Objetivo:** autenticar usuario.
- **Entrada POST:** `usuario`, `contrasena`.
- **Salida:** render `login.html` con error o redirect a `/dashboard`.
- **Efectos:** crea sesion y rehashea password legacy al iniciar sesion correcto.

### `dashboard()`
- **Ruta:** `GET /dashboard`
- **Objetivo:** mostrar metricas y ultimos tickets.
- **Salida:** render `dashboard.html` con `usuario`, `stats`, `ultimos_tickets`.

### `tickets()`
- **Ruta:** `GET /tickets`
- **Objetivo:** mostrar listado completo de tickets.
- **Salida:** render `tickets.html` con `tickets` y `estados`.

### `crear_ticket()`
- **Ruta:** `GET|POST /crear-ticket`
- **Objetivo:** alta de ticket.
- **Entrada POST:** `titulo`, `descripcion`, `prioridad`.
- **Salida:** render formulario o redirect a `/tickets`.
- **Efectos:** inserta ticket en DB y muestra mensajes flash.

### `cambiar_estado(ticket_id)`
- **Ruta:** `POST /tickets/<ticket_id>/estado`
- **Objetivo:** cambiar estado de ticket.
- **Entrada:** `ticket_id` + form `estado`.
- **Salida:** redirect a `/tickets`.
- **Efectos:** update en DB y mensaje flash.

### `eliminar_ticket(ticket_id)`
- **Ruta:** `POST /tickets/<ticket_id>/eliminar`
- **Objetivo:** eliminar ticket.
- **Entrada:** `ticket_id`.
- **Salida:** redirect a `/tickets`.
- **Efectos:** delete en DB y mensaje flash.

### `logout()`
- **Ruta:** `GET /logout`
- **Objetivo:** cerrar sesion.
- **Entrada:** ninguna.
- **Salida:** redirect a `/login`.
- **Efectos:** borra `session["usuario"]`.

---

## 2) `D:/sistema-soporte/templates/tickets.html`

### `applyFilters()`
- **Tipo:** funcion JavaScript del cliente.
- **Objetivo:** filtrar filas por texto y estado en la tabla.
- **Entradas:** no recibe parametros; toma valores de `#searchInput` y `#stateFilter`.
- **Salida:** `void`.
- **Efectos:** cambia `row.style.display` para ocultar/mostrar filas.

---

## 3) Archivos sin funciones ejecutables propias

Los siguientes archivos no definen funciones Python/JS (solo estructura HTML o constantes string):
- `D:/sistema-soporte/templates/index.html`
- `D:/sistema-soporte/templates/login.html`
- `D:/sistema-soporte/templates/dashboard.html`
- `D:/sistema-soporte/templates/crear_ticket.html`
- `D:/sistema-soporte/static/style.css`
- `D:/sistema-soporte/templates_py/index.py`
- `D:/sistema-soporte/templates_py/login.py`
- `D:/sistema-soporte/templates_py/dashboard.py`
- `D:/sistema-soporte/templates_py/crear_ticket.py`
- `D:/sistema-soporte/templates_py/tickets.py`

En `templates_py/*.py` la variable `HTML` almacena el template para edicion/copiado.
