HTML = '''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login | Soporte IT</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body class="page-auth">
    <main class="shell">
        <section class="panel auth-panel">
            <h1>Iniciar sesion</h1>
            <p class="muted">Accede al sistema de tickets de soporte.</p>

            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert {% if category == 'error' %}alert-error{% else %}alert-success{% endif %}">
                            {{ message }}
                        </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}

            {% if error %}
                <div class="alert alert-error">{{ error }}</div>
            {% endif %}

            <form method="POST" class="form-grid">
                <label for="usuario">Usuario</label>
                <input id="usuario" type="text" name="usuario" placeholder="Tu usuario" required>

                <label for="contrasena">Contrasena</label>
                <input id="contrasena" type="password" name="contrasena" placeholder="Tu contrasena" required>

                <button class="btn btn-primary" type="submit">Ingresar</button>
            </form>

            <p class="help-text">Usuario inicial: <strong>admin</strong> | Clave inicial: <strong>admin123</strong></p>
            <a class="link-inline" href="{{ url_for('index') }}">Volver al inicio</a>
        </section>
    </main>
</body>
</html>
'''
