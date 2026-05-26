HTML = '''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard | Soporte IT</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body class="page-app">
    <main class="shell">
        <header class="topbar">
            <div>
                <h1>Dashboard de Soporte</h1>
                <p class="muted">Bienvenido, {{ usuario }}</p>
            </div>
            <nav class="topbar-actions">
                <a class="btn btn-ghost" href="{{ url_for('tickets') }}">Ver tickets</a>
                <a class="btn btn-primary" href="{{ url_for('crear_ticket') }}">Nuevo ticket</a>
                <a class="btn btn-danger" href="{{ url_for('logout') }}">Cerrar sesion</a>
            </nav>
        </header>

        <section class="stats-grid">
            <article class="stat-card">
                <p>Total</p>
                <h2>{{ stats["total"] or 0 }}</h2>
            </article>
            <article class="stat-card">
                <p>Abiertos</p>
                <h2>{{ stats["abiertos"] or 0 }}</h2>
            </article>
            <article class="stat-card">
                <p>En progreso</p>
                <h2>{{ stats["progreso"] or 0 }}</h2>
            </article>
            <article class="stat-card">
                <p>Cerrados</p>
                <h2>{{ stats["cerrados"] or 0 }}</h2>
            </article>
        </section>

        <section class="panel">
            <div class="panel-head">
                <h3>Ultimos tickets</h3>
                <a class="link-inline" href="{{ url_for('tickets') }}">Abrir listado completo</a>
            </div>

            {% if ultimos_tickets %}
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Titulo</th>
                                <th>Estado</th>
                                <th>Prioridad</th>
                                <th>Fecha</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for ticket in ultimos_tickets %}
                                <tr>
                                    <td>#{{ ticket["id"] }}</td>
                                    <td>{{ ticket["titulo"] }}</td>
                                    <td>
                                        <span class="status status-{{ ticket['estado']|lower|replace(' ', '-') }}">
                                            {{ ticket["estado"] }}
                                        </span>
                                    </td>
                                    <td>{{ ticket["prioridad"] }}</td>
                                    <td>{{ ticket["fecha_creacion"] }}</td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            {% else %}
                <p class="empty-state">Aun no hay tickets cargados.</p>
            {% endif %}
        </section>
    </main>
</body>
</html>
'''
