
import streamlit as st
import sqlite3
from datetime import date


# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="Estadísticas Balonmano",
    page_icon="🤾",
    layout="wide"
)

DB_PATH = "balonmano_app/database/balonmano.db"


# ============================================================
# CONFIGURACIÓN DE ESTADÍSTICAS
# ============================================================

ZONAS_PORTERIA = [
    "Extremo izquierdo",
    "6 metros",
    "Lateral izquierdo",
    "Central",
    "Lateral derecho",
    "Extremo derecho",
    "7 metros"
]

TIPOS_LANZAMIENTO = [
    "Apoyo",
    "Salto",
    "Vaselina",
    "Rosca",
    "1x1"
]

DIRECCIONES_LANZAMIENTO = [
    "Arriba",
    "Centro",
    "Abajo",
    "Izquierda",
    "Derecha"
]

RESULTADOS_PORTERIA = [
    "Parada",
    "Gol"
]

POSICIONES_JUGADOR = [
    "Portero/a",
    "Central",
    "Lateral izquierdo",
    "Lateral derecho",
    "Extremo izquierdo",
    "Extremo derecho",
    "Pivote"
]


# ============================================================
# BASE DE DATOS
# ============================================================

def conectar():

    return sqlite3.connect(DB_PATH)


# ============================================================
# JUGADORES
# ============================================================

def obtener_jugadores():

    conexion = conectar()

    jugadores = conexion.execute("""
        SELECT
            id,
            dorsal,
            nombre,
            posicion
        FROM jugadores
        WHERE activo = 1
        ORDER BY dorsal
    """).fetchall()

    conexion.close()

    return jugadores


# ============================================================
# PARTIDOS
# ============================================================

def obtener_partidos():

    conexion = conectar()

    partidos = conexion.execute("""
        SELECT
            id,
            equipo,
            rival,
            fecha,
            competicion,
            goles_favor,
            goles_contra
        FROM partidos
        ORDER BY fecha DESC
    """).fetchall()

    conexion.close()

    return partidos


def crear_partido(
    equipo,
    rival,
    fecha,
    competicion
):

    conexion = conectar()

    cursor = conexion.cursor()

    cursor.execute("""
        INSERT INTO partidos
        (
            equipo,
            rival,
            fecha,
            competicion,
            goles_favor,
            goles_contra
        )
        VALUES (?, ?, ?, ?, 0, 0)
    """, (
        equipo,
        rival,
        fecha,
        competicion
    ))

    conexion.commit()

    partido_id = cursor.lastrowid

    conexion.close()

    return partido_id

# ============================================================
# ACCIONES DE JUGADORAS
# ============================================================

ACCIONES_JUGADORAS = [
    "Gol",
    "Lanzamiento",
    "Asistencia",
    "Pérdida",
    "Recuperación",
    "1x1 ganado",
    "1x1 perdido",
    "7 metros - Gol",
    "7 metros - Lanzamiento",
    "Exclusión",
    "Contraataque - Gol"
]


def registrar_accion(
    partido_id,
    jugador_id,
    minuto,
    accion,
    zona="",
    resultado="",
    observacion=""
):

    conexion = conectar()

    conexion.execute("""
        INSERT INTO acciones
        (
            partido_id,
            jugador_id,
            minuto,
            accion,
            zona,
            resultado,
            observacion
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        partido_id,
        jugador_id,
        minuto,
        accion,
        zona,
        resultado,
        observacion
    ))

    conexion.commit()
    conexion.close()


def obtener_acciones_partido(partido_id):

    conexion = conectar()

    acciones = conexion.execute("""
        SELECT
            a.id,
            a.minuto,
            j.nombre,
            j.dorsal,
            a.accion,
            a.zona,
            a.resultado,
            a.observacion
        FROM acciones a

        INNER JOIN jugadores j
            ON a.jugador_id = j.id

        WHERE a.partido_id = ?

        ORDER BY a.minuto, a.id
    """, (
        partido_id,
    )).fetchall()

    conexion.close()

    return acciones


def eliminar_accion(accion_id, partido_id):
    conexion = conectar()
    conexion.execute(
        """
        DELETE FROM acciones
        WHERE id = ? AND partido_id = ?
        """,
        (accion_id, partido_id)
    )
    conexion.commit()
    conexion.close()


def recalcular_marcador(partido_id):
    """
    Recalcula el marcador a partir de las acciones registradas.
    Así el resultado nunca depende de un contador manual.
    """
    conexion = conectar()

    goles_favor = conexion.execute(
        """
        SELECT COUNT(*)
        FROM acciones
        WHERE partido_id = ?
          AND (
              accion = 'Gol'
              OR (accion = 'Lanzamiento' AND resultado = 'Gol')
              OR accion = '7m gol'
              OR (accion = 'Contraataque' AND resultado = 'Gol')
          )
        """,
        (partido_id,)
    ).fetchone()[0]

    goles_contra = conexion.execute(
        """
        SELECT COUNT(*)
        FROM lanzamientos_porteria
        WHERE partido_id = ?
          AND resultado = 'Gol'
        """,
        (partido_id,)
    ).fetchone()[0]

    conexion.execute(
        """
        UPDATE partidos
        SET goles_favor = ?, goles_contra = ?
        WHERE id = ?
        """,
        (goles_favor, goles_contra, partido_id)
    )

    conexion.commit()
    conexion.close()
# ============================================================
# ESTADÍSTICAS DE JUGADORAS
# ============================================================

def calcular_estadisticas_jugadoras(partido_id):

    conexion = conectar()

    acciones = conexion.execute("""
        SELECT
            jugador_id,
            accion
        FROM acciones
        WHERE partido_id = ?
    """, (
        partido_id,
    )).fetchall()

    jugadores = conexion.execute("""
        SELECT
            id,
            nombre,
            dorsal
        FROM jugadores
        WHERE activo = 1
        ORDER BY dorsal
    """).fetchall()

    conexion.close()

    estadisticas = []

    for jugador in jugadores:

        jugador_id = jugador[0]
        nombre = jugador[1]
        dorsal = jugador[2]

        acciones_jugadora = [
            accion
            for accion in acciones
            if accion[0] == jugador_id
        ]

        # ====================================================
        # GOLES
        # ====================================================

        goles = sum(
            1
            for accion in acciones_jugadora
            if accion[1] == "Gol"
        )

        # ====================================================
        # LANZAMIENTOS
        #
        # Un "Gol" también cuenta como lanzamiento.
        # ====================================================

        lanzamientos_normales = sum(
            1
            for accion in acciones_jugadora
            if accion[1] == "Lanzamiento"
        )

        lanzamientos = (
            lanzamientos_normales
            + goles
        )

        # ====================================================
        # ASISTENCIAS
        # ====================================================

        asistencias = sum(
            1
            for accion in acciones_jugadora
            if accion[1] == "Asistencia"
        )

        # ====================================================
        # PÉRDIDAS
        # ====================================================

        perdidas = sum(
            1
            for accion in acciones_jugadora
            if accion[1] == "Pérdida"
        )

        # ====================================================
        # RECUPERACIONES
        # ====================================================

        recuperaciones = sum(
            1
            for accion in acciones_jugadora
            if accion[1] == "Recuperación"
        )

        # ====================================================
        # 1 CONTRA 1
        # ====================================================

        uno_contra_uno_ganados = sum(
            1
            for accion in acciones_jugadora
            if accion[1] == "1x1 ganado"
        )

        uno_contra_uno_perdidos = sum(
            1
            for accion in acciones_jugadora
            if accion[1] == "1x1 perdido"
        )

        # ====================================================
        # 7 METROS
        # ====================================================

        siete_metros_goles = sum(
            1
            for accion in acciones_jugadora
            if accion[1] == "7 metros - Gol"
        )

        siete_metros_lanzamientos = sum(
            1
            for accion in acciones_jugadora
            if accion[1] == "7 metros - Lanzamiento"
        )

        # ====================================================
        # EXCLUSIONES
        # ====================================================

        exclusiones = sum(
            1
            for accion in acciones_jugadora
            if accion[1] == "Exclusión"
        )

        # ====================================================
        # CONTRAATAQUES
        # ====================================================

        contraataques_goles = sum(
            1
            for accion in acciones_jugadora
            if accion[1] == "Contraataque - Gol"
        )

        # ====================================================
        # GUARDAR RESULTADO
        # ====================================================

        estadisticas.append({

            "id": jugador_id,

            "Jugadora":
                f"#{dorsal} {nombre}",

            "Minutos":
                0,

            "Goles":
                goles,

            "Lanzamientos":
                lanzamientos,

            "Asistencias":
                asistencias,

            "Pérdidas":
                perdidas,

            "Recuperaciones":
                recuperaciones,

            "1x1 ganados":
                uno_contra_uno_ganados,

            "1x1 perdidos":
                uno_contra_uno_perdidos,

            "7m goles":
                siete_metros_goles,

            "7m lanzamientos":
                siete_metros_lanzamientos,

            "Exclusiones":
                exclusiones,

            "Contraataques goles":
                contraataques_goles
        })

    return estadisticas
# ============================================================
# MENÚ LATERAL
# ============================================================

st.sidebar.title("🤾 Balonmano")

st.sidebar.markdown("---")

pagina = st.sidebar.radio(
    "Navegación",
    [
        "🏠 Inicio",
        "➕ Nuevo partido",
        "▶️ Partido en curso",
        "📋 Partidos",
        "👥 Jugadores",
        "🥅 Porteros",
        "📊 Estadísticas"
    ]
)

st.sidebar.markdown("---")

st.sidebar.info(
    "Aplicación de estadísticas de balonmano"
)


# ============================================================
# INICIO
# ============================================================

if pagina == "🏠 Inicio":

    st.title(
        "🤾 Estadísticas de Balonmano"
    )

    st.subheader(
        "Panel principal"
    )

    partidos = obtener_partidos()

    jugadores = obtener_jugadores()

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Partidos registrados",
            len(partidos)
        )

    with col2:

        st.metric(
            "Jugadores",
            len(jugadores)
        )

    with col3:

        st.metric(
            "Estado",
            "Preparado"
        )

    st.markdown("---")

    st.write(
        """
        Bienvenido a la aplicación de estadísticas de balonmano.

        Desde el menú lateral podrás:

        - Crear nuevos partidos.
        - Registrar acciones de las jugadoras desde '▶️ Partido en curso'.
        - Registrar estadísticas de portería.
        - Gestionar la plantilla.
        - Consultar partidos anteriores.
        - Consultar estadísticas.
        """
    )


# ============================================================
# NUEVO PARTIDO
# ============================================================

elif pagina == "➕ Nuevo partido":

    st.title(
        "➕ Nuevo partido"
    )

    st.write(
        "Introduce los datos básicos del partido."
    )

    with st.form("nuevo_partido"):

        equipo = st.text_input(
            "Equipo"
        )

        rival = st.text_input(
            "Rival"
        )

        fecha = st.date_input(
            "Fecha",
            value=date.today()
        )

        competicion = st.text_input(
            "Competición"
        )

        guardar = st.form_submit_button(
            "💾 Crear partido"
        )

        if guardar:

            if equipo.strip() == "":

                st.error(
                    "Introduce el nombre de tu equipo."
                )

            elif rival.strip() == "":

                st.error(
                    "Introduce el rival."
                )

            else:

                partido_id = crear_partido(
                    equipo,
                    rival,
                    fecha.isoformat(),
                    competicion
                )

                st.success(
                    f"Partido creado correctamente. ID: {partido_id}"
                )

# ============================================================
# PARTIDO EN CURSO
# ============================================================

elif pagina == "▶️ Partido en curso":

    st.title("▶️ Partido en curso")

    partidos = obtener_partidos()

    if len(partidos) == 0:
        st.warning("Todavía no hay partidos creados.")
        st.info("Ve a '➕ Nuevo partido' para crear uno.")
    else:
        # --------------------------------------------------------
        # SELECCIÓN DEL PARTIDO
        # --------------------------------------------------------
        opciones_partidos = [
            (
                p[0],
                f"{p[3]} — {p[1]} vs {p[2]}"
            )
            for p in partidos
        ]

        partido_guardado = st.session_state.get("partido_id_actual")
        ids_partidos = [p[0] for p in opciones_partidos]

        if partido_guardado not in ids_partidos:
            partido_guardado = ids_partidos[0]

        indice = ids_partidos.index(partido_guardado)

        partido_id_actual = st.radio(
            "🎮 Partido",
            ids_partidos,
            index=indice,
            format_func=lambda pid: next(
                texto for id_, texto in opciones_partidos if id_ == pid
            ),
            horizontal=False,
            key="selector_partido_actual"
        )

        st.session_state["partido_id_actual"] = partido_id_actual

        # Mantener el marcador sincronizado con las acciones.
        recalcular_marcador(partido_id_actual)

        # --------------------------------------------------------
        # DATOS Y MARCADOR
        # --------------------------------------------------------
        conexion = conectar()
        partido_actual = conexion.execute(
            """
            SELECT equipo, rival, fecha, competicion,
                   goles_favor, goles_contra
            FROM partidos
            WHERE id = ?
            """,
            (partido_id_actual,)
        ).fetchone()
        conexion.close()

        if partido_actual is None:
            st.error("No se ha podido cargar el partido.")
        else:
            equipo_actual, rival_actual, fecha_actual, competicion_actual, \
                goles_favor, goles_contra = partido_actual

            st.success(
                f"🤾 {equipo_actual} vs {rival_actual}"
                + (f" — {competicion_actual}" if competicion_actual else "")
            )

            marcador_col1, marcador_col2, marcador_col3 = st.columns([2, 1, 2])

            with marcador_col1:
                st.metric("🏠 Mi equipo", equipo_actual)

            with marcador_col2:
                st.metric("🆚 MARCADOR", f"{goles_favor} - {goles_contra}")

            with marcador_col3:
                st.metric("👥 Rival", rival_actual)

            st.caption(f"📅 {fecha_actual}")

            st.markdown("---")

            # ----------------------------------------------------
            # REINICIAR EL FLUJO
            # ----------------------------------------------------
            if "accion_paso" not in st.session_state:
                st.session_state.accion_paso = "jugadora"

            if st.session_state.get("accion_partido_id") != partido_id_actual:
                st.session_state.accion_partido_id = partido_id_actual
                st.session_state.accion_paso = "jugadora"
                st.session_state.jugadora_id_accion = None
                st.session_state.accion_tipo = None
                st.session_state.accion_zona = None
                st.session_state.accion_resultado = None

            minuto_actual = st.number_input(
                "⏱️ Minuto",
                min_value=0,
                max_value=120,
                value=st.session_state.get("minuto_actual", 1),
                step=1,
                key="minuto_actual"
            )

            jugadores = obtener_jugadores()

            if len(jugadores) == 0:
                st.warning("No hay jugadoras activas.")
                st.info("Puedes añadirlas desde '👥 Jugadores'.")
            else:
                jugadores_dict = {
                    jugador[0]: jugador
                    for jugador in jugadores
                }

                # ------------------------------------------------
                # PASO 1: JUGADORA
                # ------------------------------------------------
                if st.session_state.accion_paso == "jugadora":
                    st.subheader("1️⃣ ¿Qué jugadora?")
                    st.caption("Pulsa directamente sobre su dorsal.")

                    columnas = st.columns(4)

                    for i, jugador in enumerate(jugadores):
                        jugador_id, dorsal, nombre, posicion = jugador

                        with columnas[i % 4]:
                            if st.button(
                                f"#{dorsal}  {nombre}",
                                key=f"jugadora_{partido_id_actual}_{jugador_id}",
                                use_container_width=True
                            ):
                                st.session_state.jugadora_id_accion = jugador_id
                                st.session_state.accion_paso = "accion"
                                st.rerun()

                # ------------------------------------------------
                # PASO 2: ACCIÓN
                # ------------------------------------------------
                elif st.session_state.accion_paso == "accion":
                    jugadora = jugadores_dict.get(
                        st.session_state.jugadora_id_accion
                    )

                    if jugadora is None:
                        st.session_state.accion_paso = "jugadora"
                        st.rerun()

                    jugador_id, dorsal, nombre, posicion = jugadora

                    st.subheader(
                        f"2️⃣ ¿Qué ha hecho #{dorsal} {nombre}?"
                    )

                    if st.button("↩️ Cambiar jugadora"):
                        st.session_state.accion_paso = "jugadora"
                        st.rerun()

                    acciones_botones = [
                        ("⚽ Gol", "Gol"),
                        ("🎯 Lanzamiento", "Lanzamiento"),
                        ("🤝 Asistencia", "Asistencia"),
                        ("❌ Pérdida", "Pérdida"),
                        ("🔄 Recuperación", "Recuperación"),
                        ("⚔️ 1x1 ganado", "1x1 ganado"),
                        ("🛡️ 1x1 perdido", "1x1 perdido"),
                        ("7️⃣ 7 metros", "7m"),
                        ("🟥 Exclusión", "Exclusión"),
                        ("🏃 Contraataque", "Contraataque")
                    ]

                    columnas = st.columns(3)

                    for i, (texto_boton, valor) in enumerate(acciones_botones):
                        with columnas[i % 3]:
                            if st.button(
                                texto_boton,
                                key=f"accion_{partido_id_actual}_{valor}",
                                use_container_width=True
                            ):
                                st.session_state.accion_tipo = valor

                                if valor in {
                                    "Gol",
                                    "Asistencia",
                                    "Pérdida",
                                    "Recuperación",
                                    "1x1 ganado",
                                    "1x1 perdido",
                                    "Exclusión"
                                }:
                                    st.session_state.accion_paso = "confirmar"
                                elif valor == "7m":
                                    st.session_state.accion_paso = "resultado_7m"
                                elif valor == "Contraataque":
                                    st.session_state.accion_paso = "resultado_contra"
                                elif valor == "Lanzamiento":
                                    st.session_state.accion_paso = "zona_lanzamiento"

                                st.rerun()

                # ------------------------------------------------
                # LANZAMIENTO: ZONA
                # ------------------------------------------------
                elif st.session_state.accion_paso == "zona_lanzamiento":
                    st.subheader("3️⃣ ¿Desde dónde ha lanzado?")
                    st.caption("Selecciona la zona.")

                    zonas = [
                        "Extremo izquierdo",
                        "6 metros",
                        "Lateral izquierdo",
                        "Central",
                        "Lateral derecho",
                        "Extremo derecho",
                        "7 metros"
                    ]

                    columnas = st.columns(3)

                    for i, zona in enumerate(zonas):
                        with columnas[i % 3]:
                            if st.button(
                                zona,
                                key=f"zona_{partido_id_actual}_{i}",
                                use_container_width=True
                            ):
                                st.session_state.accion_zona = zona
                                st.session_state.accion_paso = "resultado_lanzamiento"
                                st.rerun()

                    if st.button("↩️ Volver a acciones"):
                        st.session_state.accion_paso = "accion"
                        st.rerun()

                # ------------------------------------------------
                # LANZAMIENTO: RESULTADO
                # ------------------------------------------------
                elif st.session_state.accion_paso == "resultado_lanzamiento":
                    st.subheader("4️⃣ ¿Cómo ha terminado el lanzamiento?")

                    columnas = st.columns(3)

                    for i, (texto, resultado) in enumerate([
                        ("⚽ Gol", "Gol"),
                        ("🧤 Parada", "Parada"),
                        ("❌ Fallo", "Fallo")
                    ]):
                        with columnas[i]:
                            if st.button(
                                texto,
                                key=f"resultado_lanzamiento_{partido_id_actual}_{i}",
                                use_container_width=True
                            ):
                                registrar_accion(
                                    partido_id_actual,
                                    st.session_state.jugadora_id_accion,
                                    minuto_actual,
                                    "Lanzamiento",
                                    st.session_state.accion_zona,
                                    resultado,
                                    ""
                                )
                                recalcular_marcador(partido_id_actual)
                                st.session_state.accion_paso = "jugadora"
                                st.session_state.accion_zona = None
                                st.success("✅ Lanzamiento registrado.")
                                st.rerun()

                    if st.button("↩️ Volver a zona"):
                        st.session_state.accion_paso = "zona_lanzamiento"
                        st.rerun()

                # ------------------------------------------------
                # 7 METROS: RESULTADO
                # ------------------------------------------------
                elif st.session_state.accion_paso == "resultado_7m":
                    st.subheader("3️⃣ 7 metros: ¿qué ha ocurrido?")

                    columnas = st.columns(3)

                    opciones_7m = [
                        ("⚽ Gol", "7m gol", "Gol"),
                        ("🧤 Parada", "7m lanzamiento", "Parada"),
                        ("❌ Fallo", "7m lanzamiento", "Fallo")
                    ]

                    for i, (texto, accion, resultado) in enumerate(opciones_7m):
                        with columnas[i]:
                            if st.button(
                                texto,
                                key=f"7m_{partido_id_actual}_{i}",
                                use_container_width=True
                            ):
                                registrar_accion(
                                    partido_id_actual,
                                    st.session_state.jugadora_id_accion,
                                    minuto_actual,
                                    accion,
                                    "7 metros",
                                    resultado,
                                    ""
                                )
                                recalcular_marcador(partido_id_actual)
                                st.session_state.accion_paso = "jugadora"
                                st.success("✅ 7 metros registrado.")
                                st.rerun()

                    if st.button("↩️ Volver a acciones"):
                        st.session_state.accion_paso = "accion"
                        st.rerun()

                # ------------------------------------------------
                # CONTRAATAQUE: RESULTADO
                # ------------------------------------------------
                elif st.session_state.accion_paso == "resultado_contra":
                    st.subheader("3️⃣ Contraataque: ¿cómo ha terminado?")

                    columnas = st.columns(2)

                    for i, (texto, resultado) in enumerate([
                        ("⚽ Gol", "Gol"),
                        ("❌ Fallo", "Fallo")
                    ]):
                        with columnas[i]:
                            if st.button(
                                texto,
                                key=f"contra_{partido_id_actual}_{i}",
                                use_container_width=True
                            ):
                                registrar_accion(
                                    partido_id_actual,
                                    st.session_state.jugadora_id_accion,
                                    minuto_actual,
                                    "Contraataque",
                                    "",
                                    resultado,
                                    ""
                                )
                                recalcular_marcador(partido_id_actual)
                                st.session_state.accion_paso = "jugadora"
                                st.success("✅ Contraataque registrado.")
                                st.rerun()

                    if st.button("↩️ Volver a acciones"):
                        st.session_state.accion_paso = "accion"
                        st.rerun()

                # ------------------------------------------------
                # CONFIRMAR ACCIONES DIRECTAS
                # ------------------------------------------------
                elif st.session_state.accion_paso == "confirmar":
                    jugadora = jugadores_dict.get(
                        st.session_state.jugadora_id_accion
                    )
                    accion = st.session_state.accion_tipo

                    st.subheader(
                        f"3️⃣ Confirmar: {accion}"
                    )

                    st.info(
                        f"#{jugadora[1]} {jugadora[2]} · Minuto {minuto_actual}"
                    )

                    col1, col2 = st.columns(2)

                    with col1:
                        if st.button(
                            "✅ Registrar",
                            type="primary",
                            use_container_width=True
                        ):
                            registrar_accion(
                                partido_id_actual,
                                st.session_state.jugadora_id_accion,
                                minuto_actual,
                                accion,
                                "",
                                "Éxito",
                                ""
                            )
                            recalcular_marcador(partido_id_actual)
                            st.session_state.accion_paso = "jugadora"
                            st.session_state.accion_tipo = None
                            st.success(f"✅ {accion} registrada.")
                            st.rerun()

                    with col2:
                        if st.button(
                            "↩️ Cancelar",
                            use_container_width=True
                        ):
                            st.session_state.accion_paso = "accion"
                            st.session_state.accion_tipo = None
                            st.rerun()

            # ----------------------------------------------------
            # ÚLTIMAS ACCIONES + ELIMINAR
            # ----------------------------------------------------
            st.markdown("---")
            st.subheader("📋 Últimas acciones")

            acciones_registradas = obtener_acciones_partido(partido_id_actual)

            if len(acciones_registradas) == 0:
                st.info("Todavía no hay acciones registradas en este partido.")
            else:
                st.caption(
                    "Puedes eliminar cualquier acción si se ha registrado por error."
                )

                for accion in reversed(acciones_registradas[-20:]):
                    (
                        accion_id,
                        minuto,
                        nombre,
                        dorsal,
                        accion_nombre,
                        zona,
                        resultado,
                        observacion
                    ) = accion

                    iconos = {
                        "Gol": "⚽",
                        "Lanzamiento": "🎯",
                        "Asistencia": "🤝",
                        "Pérdida": "❌",
                        "Recuperación": "🔄",
                        "1x1 ganado": "⚔️",
                        "1x1 perdido": "🛡️",
                        "7m gol": "7️⃣",
                        "7m lanzamiento": "7️⃣",
                        "Exclusión": "🟥",
                        "Contraataque": "🏃"
                    }

                    texto = (
                        f"{iconos.get(accion_nombre, '📌')} "
                        f"Min {minuto} · #{dorsal} {nombre} · {accion_nombre}"
                    )

                    col1, col2 = st.columns([6, 1])

                    with col1:
                        detalle = []
                        if zona:
                            detalle.append(zona)
                        if resultado:
                            detalle.append(resultado)
                        if observacion:
                            detalle.append(observacion)

                        st.write(
                            texto
                            + (f" — {' · '.join(detalle)}" if detalle else "")
                        )

                    with col2:
                        if st.button(
                            "🗑️",
                            key=f"eliminar_accion_{accion_id}",
                            help="Eliminar esta acción"
                        ):
                            eliminar_accion(accion_id, partido_id_actual)
                            recalcular_marcador(partido_id_actual)
                            st.rerun()


# ============================================================
# PARTIDOS
# ============================================================

elif pagina == "📋 Partidos":

    st.title(
        "📋 Partidos registrados"
    )

    partidos = obtener_partidos()

    if len(partidos) == 0:

        st.info(
            "Todavía no hay partidos registrados."
        )

    else:

        for partido in partidos:

            (
                partido_id,
                equipo,
                rival,
                fecha,
                competicion,
                goles_favor,
                goles_contra
            ) = partido

            with st.expander(
                f"{fecha} — {equipo} vs {rival}"
            ):

                col1, col2, col3 = st.columns(3)

                with col1:

                    st.write(
                        f"**Competición:** {competicion}"
                    )

                with col2:

                    st.write(
                        f"**Resultado:** "
                        f"{goles_favor} - {goles_contra}"
                    )

                with col3:

                    st.write(
                        f"**ID partido:** {partido_id}"
                    )


# ============================================================
# JUGADORES
# ============================================================

elif pagina == "👥 Jugadores":

    st.title(
        "👥 Gestión de plantilla"
    )

    st.write(
        "Desde aquí puedes añadir y modificar los jugadores."
    )

    # --------------------------------------------------------
    # AÑADIR JUGADOR
    # --------------------------------------------------------

    st.subheader(
        "➕ Añadir jugador"
    )

    with st.form("form_nuevo_jugador"):

        col1, col2, col3 = st.columns(3)

        with col1:

            nombre = st.text_input(
                "Nombre"
            )

        with col2:

            dorsal = st.number_input(
                "Dorsal",
                min_value=0,
                max_value=99,
                value=1
            )

        with col3:

            posicion = st.selectbox(
                "Posición",
                POSICIONES_JUGADOR
            )

        guardar = st.form_submit_button(
            "💾 Añadir jugador"
        )

        if guardar:

            if nombre.strip() == "":

                st.error(
                    "Introduce el nombre del jugador."
                )

            else:

                conexion = conectar()

                conexion.execute("""
                    INSERT INTO jugadores
                    (
                        nombre,
                        dorsal,
                        posicion,
                        activo
                    )
                    VALUES (?, ?, ?, 1)
                """, (
                    nombre,
                    dorsal,
                    posicion
                ))

                conexion.commit()

                conexion.close()

                st.success(
                    f"Jugador {nombre} añadido correctamente."
                )

                st.rerun()

    st.markdown("---")

    # --------------------------------------------------------
    # LISTA DE JUGADORES
    # --------------------------------------------------------

    st.subheader(
        "📋 Plantilla"
    )

    jugadores = obtener_jugadores()

    if len(jugadores) == 0:

        st.info(
            "No hay jugadores registrados."
        )

    else:

        for jugador in jugadores:

            (
                jugador_id,
                dorsal_actual,
                nombre_actual,
                posicion_actual
            ) = jugador

            with st.expander(
                f"#{dorsal_actual} — {nombre_actual}"
            ):

                with st.form(
                    f"editar_jugador_{jugador_id}"
                ):

                    col1, col2, col3 = st.columns(3)

                    with col1:

                        nuevo_nombre = st.text_input(
                            "Nombre",
                            value=nombre_actual
                        )

                    with col2:

                        nuevo_dorsal = st.number_input(
                            "Dorsal",
                            min_value=0,
                            max_value=99,
                            value=dorsal_actual
                        )

                    with col3:

                        if posicion_actual in POSICIONES_JUGADOR:

                            indice_posicion = (
                                POSICIONES_JUGADOR.index(
                                    posicion_actual
                                )
                            )

                        else:

                            indice_posicion = 0

                        nueva_posicion = st.selectbox(
                            "Posición",
                            POSICIONES_JUGADOR,
                            index=indice_posicion
                        )

                    col_guardar, col_eliminar = st.columns(2)

                    with col_guardar:

                        actualizar = st.form_submit_button(
                            "💾 Guardar cambios"
                        )

                    with col_eliminar:

                        eliminar = st.form_submit_button(
                            "🗑️ Desactivar jugador"
                        )

                    if actualizar:

                        conexion = conectar()

                        conexion.execute("""
                            UPDATE jugadores

                            SET
                                nombre = ?,
                                dorsal = ?,
                                posicion = ?

                            WHERE id = ?
                        """, (
                            nuevo_nombre,
                            nuevo_dorsal,
                            nueva_posicion,
                            jugador_id
                        ))

                        conexion.commit()

                        conexion.close()

                        st.success(
                            "Jugador actualizado correctamente."
                        )

                        st.rerun()

                    if eliminar:

                        conexion = conectar()

                        conexion.execute("""
                            UPDATE jugadores

                            SET activo = 0

                            WHERE id = ?
                        """, (
                            jugador_id,
                        ))

                        conexion.commit()

                        conexion.close()

                        st.success(
                            "Jugador desactivado."
                        )

                        st.rerun()


# ============================================================
# PORTEROS
# ============================================================

elif pagina == "🥅 Porteros":

    st.title("🥅 Gestión de porteros")

    st.write(
        "Desde aquí puedes gestionar los porteros "
        "y registrar sus lanzamientos."
    )

    # ========================================================
    # PARTIDO ACTUAL
    # ========================================================

    partido_id_actual = st.session_state.get(
        "partido_id_actual",
        None
    )

    if partido_id_actual is None:

        st.warning(
            "⚠️ No hay ningún partido seleccionado."
        )

        st.info(
            "Ve primero a '▶️ Partido en curso' "
            "y selecciona el partido."
        )

    else:

        conexion = conectar()

        partido_actual = conexion.execute("""
            SELECT
                equipo,
                rival,
                fecha,
                competicion
            FROM partidos
            WHERE id = ?
        """, (
            partido_id_actual,
        )).fetchone()

        conexion.close()

        if partido_actual is not None:

            equipo_actual = partido_actual[0]
            rival_actual = partido_actual[1]
            fecha_actual = partido_actual[2]
            competicion_actual = partido_actual[3]

            st.success(
                f"🎮 Partido activo: "
                f"{equipo_actual} vs {rival_actual} "
                f"— {fecha_actual}"
            )

    # ========================================================
    # AÑADIR PORTERO
    # ========================================================

    st.markdown("---")

    st.subheader("➕ Añadir portero/a")

    with st.form("form_nuevo_portero"):

        col1, col2 = st.columns(2)

        with col1:

            nombre_portero = st.text_input(
                "Nombre"
            )

        with col2:

            dorsal_portero = st.number_input(
                "Dorsal",
                min_value=0,
                max_value=99,
                value=1
            )

        guardar_portero = st.form_submit_button(
            "💾 Añadir portero/a"
        )

        if guardar_portero:

            if nombre_portero.strip() == "":

                st.error(
                    "Introduce el nombre del portero/a."
                )

            else:

                conexion = conectar()

                conexion.execute("""
                    INSERT INTO porteros
                    (
                        nombre,
                        dorsal,
                        activo
                    )
                    VALUES (?, ?, 1)
                """, (
                    nombre_portero,
                    dorsal_portero
                ))

                conexion.commit()

                conexion.close()

                st.success(
                    f"Portero/a {nombre_portero} "
                    "añadido correctamente."
                )

                st.rerun()

    # ========================================================
    # LISTA DE PORTEROS
    # ========================================================

    st.markdown("---")

    st.subheader(
        "📋 Porteros de la plantilla"
    )

    conexion = conectar()

    porteros = conexion.execute("""
        SELECT
            id,
            dorsal,
            nombre
        FROM porteros
        WHERE activo = 1
        ORDER BY dorsal
    """).fetchall()

    conexion.close()

    if len(porteros) == 0:

        st.info(
            "Todavía no hay porteros registrados."
        )

    else:

        for portero in porteros:

            (
                portero_id,
                dorsal_actual,
                nombre_actual
            ) = portero

            with st.expander(
                f"#{dorsal_actual} — {nombre_actual}"
            ):

                with st.form(
                    f"editar_portero_{portero_id}"
                ):

                    col1, col2 = st.columns(2)

                    with col1:

                        nuevo_nombre = st.text_input(
                            "Nombre",
                            value=nombre_actual
                        )

                    with col2:

                        nuevo_dorsal = st.number_input(
                            "Dorsal",
                            min_value=0,
                            max_value=99,
                            value=dorsal_actual
                        )

                    col_guardar, col_eliminar = st.columns(2)

                    with col_guardar:

                        actualizar_portero = (
                            st.form_submit_button(
                                "💾 Guardar cambios"
                            )
                        )

                    with col_eliminar:

                        eliminar_portero = (
                            st.form_submit_button(
                                "🗑️ Desactivar portero/a"
                            )
                        )

                    if actualizar_portero:

                        conexion = conectar()

                        conexion.execute("""
                            UPDATE porteros
                            SET
                                nombre = ?,
                                dorsal = ?
                            WHERE id = ?
                        """, (
                            nuevo_nombre,
                            nuevo_dorsal,
                            portero_id
                        ))

                        conexion.commit()
                        conexion.close()

                        st.success(
                            "Portero/a actualizado correctamente."
                        )

                        st.rerun()

                    if eliminar_portero:

                        conexion = conectar()

                        conexion.execute("""
                            UPDATE porteros
                            SET activo = 0
                            WHERE id = ?
                        """, (
                            portero_id,
                        ))

                        conexion.commit()
                        conexion.close()

                        st.success(
                            "Portero/a desactivado."
                        )

                        st.rerun()

    # ========================================================
    # REGISTRAR LANZAMIENTO
    # ========================================================

    st.markdown("---")

    st.subheader(
        "🎯 Registrar lanzamiento"
    )

    # --------------------------------------------------------
    # COMPROBAR SI HAY PARTIDO
    # --------------------------------------------------------

    if partido_id_actual is None:

        st.warning(
            "Selecciona primero un partido en "
            "'▶️ Partido en curso'."
        )

    else:

        # ----------------------------------------------------
        # PORTEROS DISPONIBLES
        # ----------------------------------------------------

        conexion = conectar()

        porteros_activos = conexion.execute("""
            SELECT
                id,
                dorsal,
                nombre
            FROM porteros
            WHERE activo = 1
            ORDER BY dorsal
        """).fetchall()

        conexion.close()

        if len(porteros_activos) == 0:

            st.warning(
                "Primero debes añadir al menos "
                "un portero/a."
            )

        else:

            nombres_porteros = [
                f"#{portero[1]} - {portero[2]}"
                for portero in porteros_activos
            ]

            # ------------------------------------------------
            # FORMULARIO
            # ------------------------------------------------

            with st.form(
                "form_lanzamiento"
            ):

                st.write(
                    "🎯 Nuevo lanzamiento"
                )

                col1, col2 = st.columns(2)

                with col1:

                    portero_seleccionado = (
                        st.selectbox(
                            "Portero/a",
                            nombres_porteros
                        )
                    )

                with col2:

                    minuto = st.number_input(
                        "Minuto",
                        min_value=0,
                        max_value=120,
                        value=1
                    )

                # --------------------------------------------
                # ZONA
                # --------------------------------------------

                zona = st.selectbox(
                    "Zona de lanzamiento",
                    ZONAS_PORTERIA
                )

                # --------------------------------------------
                # TIPO
                # --------------------------------------------

                tipo = st.selectbox(
                    "Tipo de lanzamiento",
                    TIPOS_LANZAMIENTO
                )

                # --------------------------------------------
                # DIRECCIÓN
                # --------------------------------------------

                direccion = st.selectbox(
                    "Dirección",
                    DIRECCIONES_LANZAMIENTO
                )

                # --------------------------------------------
                # RESULTADO
                # --------------------------------------------

                resultado = st.radio(
                    "Resultado",
                    RESULTADOS_PORTERIA,
                    horizontal=True
                )

                # --------------------------------------------
                # OBSERVACIÓN
                # --------------------------------------------

                observacion = st.text_input(
                    "Observación"
                )

                # --------------------------------------------
                # BOTÓN
                # --------------------------------------------

                registrar = st.form_submit_button(
                    "🎯 REGISTRAR LANZAMIENTO"
                )

                if registrar:

                    portero_index = (
                        nombres_porteros.index(
                            portero_seleccionado
                        )
                    )

                    portero_id = porteros_activos[
                        portero_index
                    ][0]

                    conexion = conectar()

                    conexion.execute("""
                        INSERT INTO lanzamientos_porteria
                        (
                            partido_id,
                            portero_id,
                            zona,
                            tipo,
                            direccion,
                            resultado,
                            minuto,
                            observacion
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        partido_id_actual,
                        portero_id,
                        zona,
                        tipo,
                        direccion,
                        resultado,
                        minuto,
                        observacion
                    ))

                    conexion.commit()
                    conexion.close()

                    st.success(
                        "✅ Lanzamiento registrado "
                        "correctamente."
                    )

                    st.rerun()

    # ========================================================
    # LANZAMIENTOS REGISTRADOS EN ESTE PARTIDO
    # ========================================================

    st.markdown("---")

    st.subheader(
        "📋 Lanzamientos registrados"
    )

    conexion = conectar()

    lanzamientos = conexion.execute("""
        SELECT
            lp.id,
            p.nombre,
            lp.zona,
            lp.tipo,
            lp.direccion,
            lp.resultado,
            lp.minuto,
            lp.observacion
        FROM lanzamientos_porteria lp

        INNER JOIN porteros p
            ON lp.portero_id = p.id

        WHERE lp.partido_id = ?

        ORDER BY lp.minuto, lp.id
    """, (
        partido_id_actual,
    )).fetchall()

    conexion.close()

    if len(lanzamientos) == 0:

        st.info(
            "Todavía no hay lanzamientos "
            "registrados en este partido."
        )

    else:

        st.write(
            f"Total de lanzamientos: "
            f"**{len(lanzamientos)}**"
        )

        for lanzamiento in lanzamientos:

            (
                lanzamiento_id,
                nombre_portero,
                zona_lanzamiento,
                tipo_lanzamiento,
                direccion_lanzamiento,
                resultado_lanzamiento,
                minuto_lanzamiento,
                observacion_lanzamiento
            ) = lanzamiento

            if resultado_lanzamiento == "Parada":

                icono = "🧤"

            else:

                icono = "⚽"

            with st.expander(
                f"{icono} Min {minuto_lanzamiento} — "
                f"{resultado_lanzamiento} — "
                f"{zona_lanzamiento}"
            ):

                col1, col2 = st.columns(2)

                with col1:

                    st.write(
                        f"**Portero/a:** "
                        f"{nombre_portero}"
                    )

                    st.write(
                        f"**Zona:** "
                        f"{zona_lanzamiento}"
                    )

                    st.write(
                        f"**Tipo:** "
                        f"{tipo_lanzamiento}"
                    )

                with col2:

                    st.write(
                        f"**Dirección:** "
                        f"{direccion_lanzamiento}"
                    )

                    st.write(
                        f"**Resultado:** "
                        f"{resultado_lanzamiento}"
                    )

                    st.write(
                        f"**Minuto:** "
                        f"{minuto_lanzamiento}"
                    )

                if observacion_lanzamiento:

                    st.write(
                        f"**Observación:** "
                        f"{observacion_lanzamiento}"
                    )

                if st.button(
                    "🗑️ Eliminar lanzamiento",
                    key=f"eliminar_lanzamiento_{lanzamiento_id}"
                ):
                    conexion = conectar()
                    conexion.execute(
                        """
                        DELETE FROM lanzamientos_porteria
                        WHERE id = ? AND partido_id = ?
                        """,
                        (lanzamiento_id, partido_id_actual)
                    )
                    conexion.commit()
                    conexion.close()

                    recalcular_marcador(partido_id_actual)
                    st.rerun()
# ============================================================
# ESTADÍSTICAS
# ============================================================

elif pagina == "📊 Estadísticas":

    st.title("📊 Estadísticas")

    # ========================================================
    # SELECCIONAR PARTIDO
    # ========================================================

    partidos = obtener_partidos()

    if len(partidos) == 0:

        st.info(
            "Todavía no hay partidos registrados."
        )

    else:

        opciones_partidos = []

        for partido in partidos:

            (
                partido_id,
                equipo,
                rival,
                fecha,
                competicion,
                goles_favor,
                goles_contra
            ) = partido

            texto = (
                f"{fecha} — "
                f"{equipo} vs {rival}"
            )

            opciones_partidos.append(
                (partido_id, texto)
            )

        textos_partidos = [
            partido[1]
            for partido in opciones_partidos
        ]

        partido_seleccionado = st.selectbox(
            "Selecciona el partido",
            textos_partidos
        )

        indice_partido = textos_partidos.index(
            partido_seleccionado
        )

        partido_id_estadisticas = (
            opciones_partidos[indice_partido][0]
        )

        # ====================================================
        # DATOS DEL PARTIDO
        # ====================================================

        conexion = conectar()

        partido = conexion.execute(
            """
            SELECT
                equipo,
                rival,
                fecha,
                competicion,
                goles_favor,
                goles_contra,
                observaciones
            FROM partidos
            WHERE id = ?
            """,
            (
                partido_id_estadisticas,
            )
        ).fetchone()

        conexion.close()

        if partido is not None:

            (
                equipo,
                rival,
                fecha,
                competicion,
                goles_favor,
                goles_contra,
                observaciones
            ) = partido

            st.markdown("---")

            st.header(
                f"🤾 {equipo} vs {rival}"
            )

            st.caption(
                f"{fecha} — {competicion}"
            )

            # =================================================
            # MARCADOR
            # =================================================

            col1, col2, col3 = st.columns(3)

            with col1:

                st.metric(
                    "🏠 Mi equipo",
                    equipo
                )

            with col2:

                st.metric(
                    "🆚 Resultado",
                    f"{goles_favor} - {goles_contra}"
                )

            with col3:

                st.metric(
                    "👥 Rival",
                    rival
                )

            if observaciones:

                st.info(
                    f"📝 {observaciones}"
                )

        # ====================================================
        # PESTAÑAS DE ESTADÍSTICAS
        # ====================================================

        tab_jugadoras, tab_porteria = st.tabs(
            [
                "👥 Jugadoras",
                "🥅 Portería"
            ]
        )

        # ====================================================
        # ESTADÍSTICAS DE JUGADORAS
        # ====================================================

        with tab_jugadoras:

            st.subheader(
                "👥 Estadísticas de jugadoras"
            )

            conexion = conectar()

            jugadores = conexion.execute(
                """
                SELECT
                    id,
                    dorsal,
                    nombre,
                    posicion
                FROM jugadores
                WHERE activo = 1
                ORDER BY dorsal
                """
            ).fetchall()

            conexion.close()

            if len(jugadores) == 0:

                st.info(
                    "No hay jugadoras registradas."
                )

            else:

                # --------------------------------------------
                # OBTENER ACCIONES
                # --------------------------------------------

                conexion = conectar()

                acciones = conexion.execute(
                    """
                    SELECT
                        id,
                        jugador_id,
                        minuto,
                        accion,
                        zona,
                        resultado,
                        observacion
                    FROM acciones
                    WHERE partido_id = ?
                    ORDER BY minuto, id
                    """,
                    (
                        partido_id_estadisticas,
                    )
                ).fetchall()

                conexion.close()

                # --------------------------------------------
                # OBTENER ESTADÍSTICAS MANUALES
                # --------------------------------------------

                conexion = conectar()

                estadisticas_guardadas = conexion.execute(
                    """
                    SELECT
                        jugador_id,
                        minutos,
                        goles,
                        lanzamientos,
                        asistencias,
                        perdidas,
                        recuperaciones,
                        uno_contra_uno_ganados,
                        uno_contra_uno_perdidos,
                        siete_metros_goles,
                        siete_metros_lanzamientos,
                        exclusiones,
                        contraataques_goles
                    FROM estadisticas_jugadores
                    WHERE partido_id = ?
                    """,
                    (
                        partido_id_estadisticas,
                    )
                ).fetchall()

                conexion.close()

                # --------------------------------------------
                # CONVERTIR ESTADÍSTICAS GUARDADAS
                # EN UN DICCIONARIO
                # --------------------------------------------

                stats_por_jugadora = {}

                for fila in estadisticas_guardadas:

                    (
                        jugador_id,
                        minutos,
                        goles,
                        lanzamientos,
                        asistencias,
                        perdidas,
                        recuperaciones,
                        uno_ganados,
                        uno_perdidos,
                        siete_goles,
                        siete_lanzamientos,
                        exclusiones,
                        contraataques_goles
                    ) = fila

                    stats_por_jugadora[jugador_id] = {
                        "minutos": minutos or 0,
                        "goles": goles or 0,
                        "lanzamientos": lanzamientos or 0,
                        "asistencias": asistencias or 0,
                        "perdidas": perdidas or 0,
                        "recuperaciones": recuperaciones or 0,
                        "uno_ganados": uno_ganados or 0,
                        "uno_perdidos": uno_perdidos or 0,
                        "siete_goles": siete_goles or 0,
                        "siete_lanzamientos": siete_lanzamientos or 0,
                        "exclusiones": exclusiones or 0,
                        "contraataques_goles": contraataques_goles or 0
                    }

                # --------------------------------------------
                # ASEGURAR QUE TODAS LAS JUGADORAS
                # TENGAN ESTADÍSTICAS
                # --------------------------------------------

                for jugador in jugadores:

                    jugador_id = jugador[0]

                    if jugador_id not in stats_por_jugadora:

                        stats_por_jugadora[jugador_id] = {
                            "minutos": 0,
                            "goles": 0,
                            "lanzamientos": 0,
                            "asistencias": 0,
                            "perdidas": 0,
                            "recuperaciones": 0,
                            "uno_ganados": 0,
                            "uno_perdidos": 0,
                            "siete_goles": 0,
                            "siete_lanzamientos": 0,
                            "exclusiones": 0,
                            "contraataques_goles": 0
                        }

                # --------------------------------------------
                # SUMAR ACCIONES REGISTRADAS
                # --------------------------------------------

                for accion in acciones:

                    jugador_id = accion[1]
                    tipo_accion = accion[3]
                    resultado = accion[5]

                    if jugador_id not in stats_por_jugadora:
                        continue

                    stats = stats_por_jugadora[jugador_id]

                    # GOL
                    if tipo_accion == "Gol":

                        stats["goles"] += 1
                        stats["lanzamientos"] += 1

                    # LANZAMIENTO
                    elif tipo_accion == "Lanzamiento":

                        stats["lanzamientos"] += 1

                        if resultado == "Gol":

                            stats["goles"] += 1

                    # ASISTENCIA
                    elif tipo_accion == "Asistencia":

                        stats["asistencias"] += 1

                    # PÉRDIDA
                    elif tipo_accion == "Pérdida":

                        stats["perdidas"] += 1

                    # RECUPERACIÓN
                    elif tipo_accion == "Recuperación":

                        stats["recuperaciones"] += 1

                    # 1 CONTRA 1 GANADO
                    elif tipo_accion == "1x1 ganado":

                        stats["uno_ganados"] += 1

                    # 1 CONTRA 1 PERDIDO
                    elif tipo_accion == "1x1 perdido":

                        stats["uno_perdidos"] += 1

                    # 7 METROS GOL
                    elif tipo_accion == "7m gol":

                        stats["siete_goles"] += 1
                        stats["siete_lanzamientos"] += 1

                    # 7 METROS LANZAMIENTO
                    elif tipo_accion == "7m lanzamiento":

                        stats["siete_lanzamientos"] += 1

                    # EXCLUSIÓN
                    elif tipo_accion == "Exclusión":

                        stats["exclusiones"] += 1

                    # CONTRAATAQUE
                    elif tipo_accion == "Contraataque":

                        if resultado == "Gol":

                            stats["contraataques_goles"] += 1

                # --------------------------------------------
                # CREAR TABLA
                # --------------------------------------------

                datos_jugadoras = []

                for jugador in jugadores:

                    (
                        jugador_id,
                        dorsal,
                        nombre,
                        posicion
                    ) = jugador

                    stats = stats_por_jugadora[jugador_id]

                    lanzamientos = stats["lanzamientos"]
                    goles = stats["goles"]

                    if lanzamientos > 0:

                        porcentaje_lanzamiento = (
                            goles
                            / lanzamientos
                            * 100
                        )

                    else:

                        porcentaje_lanzamiento = 0

                    datos_jugadoras.append(
                        {
                            "Jugadora": (
                                f"#{dorsal} {nombre}"
                            ),

                            "Posición": posicion,

                            "Min": stats["minutos"],

                            "Goles": goles,

                            "Lanz.": lanzamientos,

                            "% Lanz.": (
                                f"{porcentaje_lanzamiento:.1f}%"
                            ),

                            "Asist.": stats["asistencias"],

                            "Pérdidas": stats["perdidas"],

                            "Recup.": stats["recuperaciones"],

                            "1x1 +": stats["uno_ganados"],

                            "1x1 -": stats["uno_perdidos"],

                            "7m G": stats["siete_goles"],

                            "7m L": stats["siete_lanzamientos"],

                            "Exclus.": stats["exclusiones"],

                            "Contra G": (
                                stats[
                                    "contraataques_goles"
                                ]
                            )
                        }
                    )

                # --------------------------------------------
                # MOSTRAR TABLA
                # --------------------------------------------

                st.dataframe(
                    datos_jugadoras,
                    use_container_width=True,
                    hide_index=True
                )

                # --------------------------------------------
                # RESUMEN DEL EQUIPO
                # --------------------------------------------

                st.markdown("---")

                st.subheader(
                    "📊 Resumen ofensivo"
                )

                total_goles_jugadoras = sum(
                    stats["goles"]
                    for stats in stats_por_jugadora.values()
                )

                total_lanzamientos_jugadoras = sum(
                    stats["lanzamientos"]
                    for stats in stats_por_jugadora.values()
                )

                total_asistencias = sum(
                    stats["asistencias"]
                    for stats in stats_por_jugadora.values()
                )

                total_perdidas = sum(
                    stats["perdidas"]
                    for stats in stats_por_jugadora.values()
                )

                total_recuperaciones = sum(
                    stats["recuperaciones"]
                    for stats in stats_por_jugadora.values()
                )

                col1, col2, col3, col4, col5 = st.columns(5)

                with col1:

                    st.metric(
                        "⚽ Goles",
                        total_goles_jugadoras
                    )

                with col2:

                    st.metric(
                        "🎯 Lanzamientos",
                        total_lanzamientos_jugadoras
                    )

                with col3:

                    st.metric(
                        "🤝 Asistencias",
                        total_asistencias
                    )

                with col4:

                    st.metric(
                        "❌ Pérdidas",
                        total_perdidas
                    )

                with col5:

                    st.metric(
                        "🔄 Recuperaciones",
                        total_recuperaciones
                    )

                # --------------------------------------------
                # ACCIONES REGISTRADAS
                # --------------------------------------------

                st.markdown("---")

                st.subheader(
                    "📋 Acciones registradas"
                )

                if len(acciones) == 0:

                    st.info(
                        "Todavía no hay acciones "
                        "registradas en este partido."
                    )

                else:

                    datos_acciones = []

                    jugadores_dict = {
                        jugador[0]: (
                            f"#{jugador[1]} {jugador[2]}"
                        )
                        for jugador in jugadores
                    }

                    for accion in acciones:

                        (
                            accion_id,
                            jugador_id,
                            minuto,
                            tipo_accion,
                            zona,
                            resultado,
                            observacion
                        ) = accion

                        datos_acciones.append(
                            {
                                "Min": minuto,
                                "Jugadora": (
                                    jugadores_dict.get(
                                        jugador_id,
                                        "Desconocida"
                                    )
                                ),
                                "Acción": tipo_accion,
                                "Zona": zona,
                                "Resultado": resultado,
                                "Observación": observacion
                            }
                        )

                    st.dataframe(
                        datos_acciones,
                        use_container_width=True,
                        hide_index=True
                    )

        # ====================================================
        # ESTADÍSTICAS DE PORTERÍA
        # ====================================================

        with tab_porteria:

            st.subheader(
                "🥅 Estadísticas de portería"
            )

            conexion = conectar()

            lanzamientos = conexion.execute(
                """
                SELECT
                    id,
                    portero_id,
                    zona,
                    tipo,
                    direccion,
                    resultado,
                    minuto,
                    observacion
                FROM lanzamientos_porteria
                WHERE partido_id = ?
                ORDER BY minuto, id
                """,
                (
                    partido_id_estadisticas,
                )
            ).fetchall()

            conexion.close()

            # --------------------------------------------
            # ESTADÍSTICAS GENERALES
            # --------------------------------------------

            total_lanzamientos = len(
                lanzamientos
            )

            total_paradas = sum(
                1
                for lanzamiento in lanzamientos
                if lanzamiento[5] == "Parada"
            )

            total_goles = sum(
                1
                for lanzamiento in lanzamientos
                if lanzamiento[5] == "Gol"
            )

            if total_lanzamientos > 0:

                porcentaje_paradas = (
                    total_paradas
                    / total_lanzamientos
                    * 100
                )

            else:

                porcentaje_paradas = 0

            col1, col2, col3, col4 = st.columns(4)

            with col1:

                st.metric(
                    "🎯 Lanzamientos",
                    total_lanzamientos
                )

            with col2:

                st.metric(
                    "🧤 Paradas",
                    total_paradas
                )

            with col3:

                st.metric(
                    "⚽ Goles recibidos",
                    total_goles
                )

            with col4:

                st.metric(
                    "📈 % Paradas",
                    f"{porcentaje_paradas:.1f}%"
                )

            # --------------------------------------------
            # PORTEROS/AS
            # --------------------------------------------

            st.markdown("---")

            st.subheader(
                "🥅 Estadísticas por portero/a"
            )

            conexion = conectar()

            porteros_partido = conexion.execute(
                """
                SELECT DISTINCT
                    p.id,
                    p.nombre,
                    p.dorsal
                FROM lanzamientos_porteria lp
                INNER JOIN porteros p
                    ON lp.portero_id = p.id
                WHERE lp.partido_id = ?
                ORDER BY p.dorsal
                """,
                (
                    partido_id_estadisticas,
                )
            ).fetchall()

            conexion.close()

            datos_porteros = []

            for portero in porteros_partido:

                portero_id = portero[0]
                nombre_portero = portero[1]
                dorsal_portero = portero[2]

                lanzamientos_portero = [
                    lanzamiento
                    for lanzamiento in lanzamientos
                    if lanzamiento[1] == portero_id
                ]

                total_portero = len(
                    lanzamientos_portero
                )

                paradas_portero = sum(
                    1
                    for lanzamiento in lanzamientos_portero
                    if lanzamiento[5] == "Parada"
                )

                goles_portero = sum(
                    1
                    for lanzamiento in lanzamientos_portero
                    if lanzamiento[5] == "Gol"
                )

                if total_portero > 0:

                    porcentaje_portero = (
                        paradas_portero
                        / total_portero
                        * 100
                    )

                else:

                    porcentaje_portero = 0

                datos_porteros.append(
                    {
                        "Portero/a": (
                            f"#{dorsal_portero} "
                            f"{nombre_portero}"
                        ),

                        "Lanzamientos": total_portero,

                        "Paradas": paradas_portero,

                        "Goles": goles_portero,

                        "% Paradas": (
                            f"{porcentaje_portero:.1f}%"
                        )
                    }
                )

            if len(datos_porteros) > 0:

                st.dataframe(
                    datos_porteros,
                    use_container_width=True,
                    hide_index=True
                )

            else:

                st.info(
                    "Todavía no hay estadísticas "
                    "de portería para este partido."
                )

            # --------------------------------------------
            # LANZAMIENTOS POR ZONA
            # --------------------------------------------

            st.markdown("---")

            st.subheader(
                "📍 Lanzamientos por zona"
            )

            datos_zonas = []

            for zona in ZONAS_PORTERIA:

                lanzamientos_zona = [
                    lanzamiento
                    for lanzamiento in lanzamientos
                    if lanzamiento[2] == zona
                ]

                total_zona = len(
                    lanzamientos_zona
                )

                paradas_zona = sum(
                    1
                    for lanzamiento in lanzamientos_zona
                    if lanzamiento[5] == "Parada"
                )

                goles_zona = sum(
                    1
                    for lanzamiento in lanzamientos_zona
                    if lanzamiento[5] == "Gol"
                )

                if total_zona > 0:

                    porcentaje_zona = (
                        paradas_zona
                        / total_zona
                        * 100
                    )

                else:

                    porcentaje_zona = 0

                datos_zonas.append(
                    {
                        "Zona": zona,
                        "Lanzamientos": total_zona,
                        "Paradas": paradas_zona,
                        "Goles": goles_zona,
                        "% Paradas": (
                            f"{porcentaje_zona:.1f}%"
                        )
                    }
                )

            st.dataframe(
                datos_zonas,
                use_container_width=True,
                hide_index=True
            )

            # --------------------------------------------
            # LANZAMIENTOS POR TIPO
            # --------------------------------------------

            st.markdown("---")

            st.subheader(
                "🎯 Lanzamientos por tipo"
            )

            datos_tipos = []

            for tipo in TIPOS_LANZAMIENTO:

                lanzamientos_tipo = [
                    lanzamiento
                    for lanzamiento in lanzamientos
                    if lanzamiento[3] == tipo
                ]

                total_tipo = len(
                    lanzamientos_tipo
                )

                paradas_tipo = sum(
                    1
                    for lanzamiento in lanzamientos_tipo
                    if lanzamiento[5] == "Parada"
                )

                goles_tipo = sum(
                    1
                    for lanzamiento in lanzamientos_tipo
                    if lanzamiento[5] == "Gol"
                )

                if total_tipo > 0:

                    porcentaje_tipo = (
                        paradas_tipo
                        / total_tipo
                        * 100
                    )

                else:

                    porcentaje_tipo = 0

                datos_tipos.append(
                    {
                        "Tipo": tipo,
                        "Lanzamientos": total_tipo,
                        "Paradas": paradas_tipo,
                        "Goles": goles_tipo,
                        "% Paradas": (
                            f"{porcentaje_tipo:.1f}%"
                        )
                    }
                )

            st.dataframe(
                datos_tipos,
                use_container_width=True,
                hide_index=True
            )

            # --------------------------------------------
            # LANZAMIENTOS POR DIRECCIÓN
            # --------------------------------------------

            st.markdown("---")

            st.subheader(
                "↗️ Lanzamientos por dirección"
            )

            datos_direcciones = []

            for direccion in DIRECCIONES_LANZAMIENTO:

                lanzamientos_direccion = [
                    lanzamiento
                    for lanzamiento in lanzamientos
                    if lanzamiento[4] == direccion
                ]

                total_direccion = len(
                    lanzamientos_direccion
                )

                paradas_direccion = sum(
                    1
                    for lanzamiento in lanzamientos_direccion
                    if lanzamiento[5] == "Parada"
                )

                goles_direccion = sum(
                    1
                    for lanzamiento in lanzamientos_direccion
                    if lanzamiento[5] == "Gol"
                )

                if total_direccion > 0:

                    porcentaje_direccion = (
                        paradas_direccion
                        / total_direccion
                        * 100
                    )

                else:

                    porcentaje_direccion = 0

                datos_direcciones.append(
                    {
                        "Dirección": direccion,
                        "Lanzamientos": total_direccion,
                        "Paradas": paradas_direccion,
                        "Goles": goles_direccion,
                        "% Paradas": (
                            f"{porcentaje_direccion:.1f}%"
                        )
                    }
                )

            st.dataframe(
                datos_direcciones,
                use_container_width=True,
                hide_index=True
            )

            # --------------------------------------------
            # MENSAJE SIN DATOS
            # --------------------------------------------


            if total_lanzamientos == 0:

                st.info(
                    "Este partido todavía no tiene "
                    "lanzamientos de portería registrados."
                )
