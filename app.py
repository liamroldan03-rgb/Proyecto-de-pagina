"""
Aplicacion Flask de soporte IT.

El modulo implementa:
1. Inicializacion y migracion basica de SQLite.
2. Autenticacion por sesion para usuarios.
3. Gestion de tickets (crear, listar, cambiar estado y eliminar).
4. Pantallas HTML para inicio, login, dashboard y tickets.
"""

from datetime import datetime
from functools import wraps
from pathlib import Path
import sqlite3

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = "soporteit123"

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database.db"

TICKET_STATES = ("Abierto", "En progreso", "Cerrado")
TICKET_PRIORITIES = ("Baja", "Media", "Alta")


def get_connection():
    """
    Crea una conexion SQLite lista para usar en la app.

    Returns:
        sqlite3.Connection: conexion abierta con `row_factory=sqlite3.Row`
        para acceder a columnas por nombre.

    Side Effects:
        Abre un handle a `database.db`. El cierre queda a cargo del llamador.
    """
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def ensure_column(cursor, table, column, definition):
    """
    Garantiza que una columna exista en una tabla.

    Args:
        cursor (sqlite3.Cursor): cursor de una conexion activa.
        table (str): nombre de tabla objetivo.
        column (str): nombre de columna a verificar.
        definition (str): definicion SQL usada en `ALTER TABLE ... ADD COLUMN`.

    Returns:
        None

    Side Effects:
        Ejecuta SQL sobre la base; si la columna no existe, la agrega.
    """
    cursor.execute(f"PRAGMA table_info({table})")
    columns = {row[1] for row in cursor.fetchall()}
    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def migrate_legacy_passwords(cursor):
    """
    Migra contraseñas heredadas desde columnas antiguas hacia `password`.

    La app original podia tener nombres de columna distintos por encoding
    (`contraseña`, variante unicode, variante mojibake). Esta rutina detecta la
    columna existente y copia su valor solo cuando `password` esta vacio.

    Args:
        cursor (sqlite3.Cursor): cursor de una conexion activa.

    Returns:
        None
    """
    cursor.execute("PRAGMA table_info(usuarios)")
    columns = {row[1] for row in cursor.fetchall()}
    legacy_column = next(
        (
            name
            for name in ("contraseña", "contrase\u00f1a", "contrase\u00c3\u00b1a")
            if name in columns
        ),
        None,
    )

    if legacy_column:
        cursor.execute(
            f"""
            UPDATE usuarios
            SET password = "{legacy_column}"
            WHERE (password IS NULL OR TRIM(password) = '')
              AND "{legacy_column}" IS NOT NULL
            """
        )


def hash_plain_passwords(cursor):
    """
    Convierte contraseñas en texto plano a hashes seguros de Werkzeug.

    Args:
        cursor (sqlite3.Cursor): cursor de una conexion activa.

    Returns:
        None

    Notes:
        Si el valor ya parece hash (`scrypt:` o `pbkdf2:`), no se modifica.
    """
    users = cursor.execute("SELECT id, password FROM usuarios").fetchall()
    for user in users:
        current_password = (user["password"] or "").strip()
        if not current_password:
            continue

        if not (
            current_password.startswith("scrypt:")
            or current_password.startswith("pbkdf2:")
        ):
            cursor.execute(
                "UPDATE usuarios SET password = ? WHERE id = ?",
                (generate_password_hash(current_password), user["id"]),
            )


def create_db():
    """
    Inicializa y migra la base de datos al esquema esperado por la app.

    Flujo principal:
    1. Crea tablas `usuarios` y `tickets` si no existen.
    2. Asegura columnas nuevas agregadas en versiones posteriores.
    3. Migra contraseñas heredadas y las hashea.
    4. Normaliza defaults de tickets existentes.
    5. Garantiza usuario admin inicial.

    Returns:
        None

    Side Effects:
        Escribe cambios en `database.db` y hace commit al finalizar.
    """
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL UNIQUE,
            password TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'Abierto',
            prioridad TEXT NOT NULL DEFAULT 'Media',
            creado_por TEXT NOT NULL DEFAULT 'sistema',
            fecha_creacion TEXT NOT NULL DEFAULT ''
        )
        """
    )

    ensure_column(cursor, "usuarios", "password", "TEXT")
    migrate_legacy_passwords(cursor)
    hash_plain_passwords(cursor)

    ensure_column(cursor, "tickets", "prioridad", "TEXT NOT NULL DEFAULT 'Media'")
    ensure_column(cursor, "tickets", "creado_por", "TEXT NOT NULL DEFAULT 'sistema'")
    ensure_column(cursor, "tickets", "fecha_creacion", "TEXT NOT NULL DEFAULT ''")

    cursor.execute(
        """
        UPDATE tickets
        SET prioridad = 'Media'
        WHERE prioridad IS NULL OR TRIM(prioridad) = ''
        """
    )
    cursor.execute(
        """
        UPDATE tickets
        SET creado_por = 'sistema'
        WHERE creado_por IS NULL OR TRIM(creado_por) = ''
        """
    )
    cursor.execute(
        """
        UPDATE tickets
        SET fecha_creacion = ?
        WHERE fecha_creacion IS NULL OR TRIM(fecha_creacion) = ''
        """,
        (datetime.now().strftime("%Y-%m-%d %H:%M"),),
    )

    admin = cursor.execute(
        "SELECT id, password FROM usuarios WHERE usuario = ?",
        ("admin",),
    ).fetchone()
    if admin is None:
        cursor.execute(
            "INSERT INTO usuarios (usuario, password) VALUES (?, ?)",
            ("admin", generate_password_hash("admin123")),
        )
    else:
        current_password = (admin["password"] or "").strip()
        if current_password == "admin123":
            cursor.execute(
                "UPDATE usuarios SET password = ? WHERE id = ?",
                (generate_password_hash("admin123"), admin["id"]),
            )

    connection.commit()
    connection.close()


def login_required(view):
    """
    Decorador para restringir acceso a rutas autenticadas.

    Args:
        view (Callable): funcion de vista Flask a envolver.

    Returns:
        Callable: nueva funcion que valida `session["usuario"]` antes
        de ejecutar la vista original.
    """
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        """
        Wrapper interno del decorador `login_required`.

        Returns:
            Response: redireccion a login si no hay sesion, o resultado
            original de la vista protegida.
        """
        if "usuario" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def verify_password(stored_password, candidate):
    """
    Valida una contraseña candidata contra un valor almacenado.

    Args:
        stored_password (str | None): valor almacenado en DB (hash o legacy).
        candidate (str): contraseña enviada por formulario.

    Returns:
        bool: `True` si coincide, `False` en caso contrario.

    Notes:
        Soporta compatibilidad con valores legacy en texto plano.
    """
    value = (stored_password or "").strip()
    if not value:
        return False

    if value.startswith("scrypt:") or value.startswith("pbkdf2:"):
        return check_password_hash(value, candidate)

    return value == candidate


@app.route("/")
def index():
    """
    Muestra pantalla de inicio publica.

    Returns:
        Response: redireccion al dashboard si ya hay sesion, o render de
        `index.html` para usuarios anonimos.
    """
    if "usuario" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Gestiona autenticacion de usuario.

    Metodo GET:
        Muestra formulario de login.

    Metodo POST:
        Valida campos, busca usuario, verifica contraseña y crea sesion.
        Si el password estaba en texto plano legacy, lo re-hashea.

    Returns:
        Response: render de login con error o redireccion al dashboard.
    """
    if "usuario" in session:
        return redirect(url_for("dashboard"))

    error = None
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        contraseña = request.form.get("contraseña", "")

        if not usuario or not contraseña:
            error = "Completa usuario y contraseña."
        else:
            connection = get_connection()
            db_user = connection.execute(
                "SELECT id, usuario, password FROM usuarios WHERE usuario = ?",
                (usuario,),
            ).fetchone()

            if db_user and verify_password(db_user["password"], contraseña):
                session["usuario"] = db_user["usuario"]

                if not (
                    db_user["password"].startswith("scrypt:")
                    or db_user["password"].startswith("pbkdf2:")
                ):
                    connection.execute(
                        "UPDATE usuarios SET password = ? WHERE id = ?",
                        (generate_password_hash(contraseña), db_user["id"]),
                    )
                    connection.commit()

                connection.close()
                return redirect(url_for("dashboard"))

            connection.close()
            error = "Usuario o contraseña incorrectos."

    return render_template("login.html", error=error)


@app.route("/dashboard")
@login_required
def dashboard():
    """
    Renderiza panel principal con metricas y ultimos tickets.

    Returns:
        Response: vista `dashboard.html` con:
        - usuario autenticado
        - estadisticas por estado
        - ultimos tickets creados
    """
    connection = get_connection()
    stats = connection.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN estado = 'Abierto' THEN 1 ELSE 0 END) AS abiertos,
            SUM(CASE WHEN estado = 'En progreso' THEN 1 ELSE 0 END) AS progreso,
            SUM(CASE WHEN estado = 'Cerrado' THEN 1 ELSE 0 END) AS cerrados
        FROM tickets
        """
    ).fetchone()
    ultimos_tickets = connection.execute(
        """
        SELECT id, titulo, estado, prioridad, fecha_creacion
        FROM tickets
        ORDER BY id DESC
        LIMIT 6
        """
    ).fetchall()
    connection.close()

    return render_template(
        "dashboard.html",
        usuario=session["usuario"],
        stats=stats,
        ultimos_tickets=ultimos_tickets,
    )


@app.route("/tickets")
@login_required
def tickets():
    """
    Lista todos los tickets ordenados por mas reciente.

    Returns:
        Response: vista `tickets.html` con dataset completo y lista de
        estados validos para selectores de cambio de estado.
    """
    connection = get_connection()
    rows = connection.execute(
        """
        SELECT id, titulo, descripcion, estado, prioridad, creado_por, fecha_creacion
        FROM tickets
        ORDER BY id DESC
        """
    ).fetchall()
    connection.close()

    return render_template(
        "tickets.html",
        tickets=rows,
        estados=TICKET_STATES,
    )


@app.route("/crear-ticket", methods=["GET", "POST"])
@login_required
def crear_ticket():
    """
    Crea nuevos tickets de soporte.

    Metodo GET:
        Muestra formulario de alta.

    Metodo POST:
        Valida titulo/descripcion/prioridad y guarda el ticket con estado
        inicial `Abierto`, usuario creador y timestamp.

    Returns:
        Response: render de formulario o redireccion al listado.
    """
    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        prioridad = request.form.get("prioridad", "Media")

        if prioridad not in TICKET_PRIORITIES:
            prioridad = "Media"

        if not titulo or not descripcion:
            flash("Debes completar titulo y descripcion.", "error")
            return redirect(url_for("crear_ticket"))

        connection = get_connection()
        connection.execute(
            """
            INSERT INTO tickets (titulo, descripcion, estado, prioridad, creado_por, fecha_creacion)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                titulo,
                descripcion,
                "Abierto",
                prioridad,
                session["usuario"],
                datetime.now().strftime("%Y-%m-%d %H:%M"),
            ),
        )
        connection.commit()
        connection.close()

        flash("Ticket creado correctamente.", "success")
        return redirect(url_for("tickets"))

    return render_template("crear_ticket.html", prioridades=TICKET_PRIORITIES)


@app.post("/tickets/<int:ticket_id>/estado")
@login_required
def cambiar_estado(ticket_id):
    """
    Actualiza el estado de un ticket existente.

    Args:
        ticket_id (int): identificador del ticket a modificar.

    Returns:
        Response: redireccion al listado con mensaje flash de exito/error.
    """
    nuevo_estado = request.form.get("estado", "Abierto")
    if nuevo_estado not in TICKET_STATES:
        flash("Estado invalido.", "error")
        return redirect(url_for("tickets"))

    connection = get_connection()
    updated = connection.execute(
        "UPDATE tickets SET estado = ? WHERE id = ?",
        (nuevo_estado, ticket_id),
    ).rowcount
    connection.commit()
    connection.close()

    if updated:
        flash("Estado actualizado.", "success")
    else:
        flash("No se encontro el ticket.", "error")
    return redirect(url_for("tickets"))


@app.post("/tickets/<int:ticket_id>/eliminar")
@login_required
def eliminar_ticket(ticket_id):
    """
    Elimina un ticket por ID.

    Args:
        ticket_id (int): identificador del ticket a eliminar.

    Returns:
        Response: redireccion al listado con mensaje flash de exito/error.
    """
    connection = get_connection()
    deleted = connection.execute(
        "DELETE FROM tickets WHERE id = ?",
        (ticket_id,),
    ).rowcount
    connection.commit()
    connection.close()

    if deleted:
        flash("Ticket eliminado.", "success")
    else:
        flash("No se encontro el ticket.", "error")
    return redirect(url_for("tickets"))


@app.route("/logout")
def logout():
    """
    Cierra la sesion del usuario actual.

    Returns:
        Response: redireccion al login con mensaje de sesion cerrada.
    """
    session.pop("usuario", None)
    flash("Sesion cerrada.", "success")
    return redirect(url_for("login"))


create_db()


if __name__ == "__main__":
    @app.route("/registro", methods=["GET", "POST"])
    def registro():
        """
        Gestiona el registro de nuevos usuarios.

        Metodo GET:
            Muestra formulario de registro.

        Metodo POST:
            Valida que usuario no exista, que las contraseñas coincidan
            y que tengan longitud minima. Crea el usuario con password hasheado.

        Returns:
            Response: render del formulario con errores o redireccion al login.
        """
        if "usuario" in session:
            return redirect(url_for("dashboard"))

        error = None

        if request.method == "POST":
            usuario    = request.form.get("usuario", "").strip()
            contraseña = request.form.get("contraseña", "")
            confirmar  = request.form.get("confirmar", "")

            # --- Validaciones ---
            if not usuario or not contraseña or not confirmar:
                error = "Todos los campos son obligatorios."
            elif len(usuario) < 3:
                error = "El nombre de usuario debe tener al menos 3 caracteres."
            elif len(contraseña) < 6:
                error = "La contraseña debe tener al menos 6 caracteres."
            elif contraseña != confirmar:
                error = "Las contraseñas no coinciden."
            else:
                connection = get_connection()
                existe = connection.execute(
                    "SELECT id FROM usuarios WHERE usuario = ?",
                    (usuario,),
                ).fetchone()

                if existe:
                    error = "Ese nombre de usuario ya esta en uso."
                    connection.close()
                else:
                    connection.execute(
                        "INSERT INTO usuarios (usuario, password) VALUES (?, ?)",
                        (usuario, generate_password_hash(contraseña)),
                    )
                    connection.commit()
                    connection.close()

                    flash("Cuenta creada correctamente. Ahora podes iniciar sesion.", "success")
                    return redirect(url_for("login"))

        return render_template("registro.html", error=error)
    app.run(debug=True)
