# Balonmano — Android

App Android independiente, sin Streamlit ni conexión obligatoria.

Incluye:
- Partido en curso con botones grandes y minuto editable.
- Registro de jugadoras y acciones (Gol, Lanzamiento, Asistencia, Pérdida,
  Recuperación, 1x1 ganado/perdido, 7 metros, Exclusión, Contraataque),
  con las mismas zonas, resultados y nombres de acción que la app de Python.
- Portería integrada en Partido en curso (zona, tipo y dirección del
  lanzamiento, igual que en la app de Python), sin plantilla separada.
- Marcador automático corregido: un lanzamiento que termina en gol también
  suma al marcador (antes solo contaban las acciones "Gol" directas).
- Jugadoras: se pueden desactivar (mantener historial) o borrar
  definitivamente (con confirmación).
- Estadísticas en formato de tabla (por partido: jugadoras, portería,
  zonas, tipos y direcciones de lanzamiento).
- Estadísticas por jugadora: totales de toda la temporada y desglose
  partido a partido, tocando su nombre en la lista de jugadoras.
- Borrado de acciones, lanzamientos, partidos y jugadoras.
- SQLite local. La base de datos existente se incluye en
  `app/src/main/assets/balonmano.db`.

## Crear APK
Abrir en Android Studio y ejecutar `app > assembleDebug`, o subir el
proyecto a GitHub y ejecutar el workflow `Build APK` (Actions →
`Build APK` → `Run workflow`); el APK queda en el artefacto
`Balonmano-debug`.
