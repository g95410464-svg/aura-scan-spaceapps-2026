# Lectura continua 0.4

La cámara en vivo sustituye el disparador manual como entrada principal. La web mantiene la vista previa y envía un fotograma JPEG cada 1,8 segundos después de terminar el análisis anterior; la frecuencia efectiva depende de la red y del OCR. No se transmite audio ni se guarda un video.

## Registro automático

- Antes de iniciar se declara alias, categoría o detección por etiquetas, y si los datos son ficticios. No hay cuentas ni login.
- Se requiere un mínimo de tres fotogramas consistentes durante al menos tres segundos, sin huecos superiores a 15 segundos.
- Cada campo necesita etiqueta/unidad válida y confianza técnica OCR de al menos 0,90. Nitidez y brillo se comprueban con heurísticas. Pantallas de memoria/error/promedio y campos requeridos ausentes impiden guardar.
- Para absorber fluctuaciones pequeñas se permite hasta 2 lpm de diferencia de pulso y 1 punto de SpO2 respecto al primer valor candidato; los demás campos requieren coincidencia exacta. Son tolerancias de estabilidad del prototipo, no umbrales clínicos ni una validación de precisión.
- Se registra el valor real del último fotograma aceptado; no se calcula ni inventa un promedio. Se conserva una evidencia PNG de ese fotograma. Los demás fotogramas se procesan en memoria y se descartan.
- Se deduplican valores iguales o dentro de esas tolerancias durante la misma sesión. Otro cambio estable puede guardarse tras un mínimo de 10 segundos desde el anterior. La misma pantalla no genera filas en cada ciclo. Reiniciar la sesión permite registrar otra observación aunque muestre los mismos números; no es deduplicación entre sesiones.
- El resultado se guarda inmediatamente en `workspace_live_readings`, con procedencia `live_ocr_unreviewed` y estado pendiente. Es registro automático, sin pulsar Tomar captura ni Confirmar para guardarlo.

## Revisión y asistente

Las lecturas automáticas aparecen en el panel en vivo, el historial y el asistente, separadas de las mediciones revisadas. No se cuentan como mediciones confirmadas ni alimentan sus comparaciones hasta que se revise la evidencia. El alias se hereda de la sesión y se puede corregir al revisar. La hora registrada es la observación de la pantalla; la hora real de medición sigue siendo desconocida salvo declaración posterior.

Revisar evidencia permite comprobar etiquetas, números, unidades y el modo del instrumento, corregirlos y confirmar. La confirmación conserva la observación original, actualiza su estado y añade la medición al seguimiento e informe PDF existente. No se producen diagnósticos ni tratamientos automáticos.

## Control de la cámara

Detener, cambiar de sección, ocultar la página o cerrar el componente cancela el envío y cierra las pistas de cámara. Una respuesta tardía se ignora en la interfaz; el servidor rechaza fotogramas después de cerrar la sesión. Un fotograma ya aceptado antes de la detención conserva su registro. Las sesiones duran como máximo dos horas. No se analiza en segundo plano.

Los errores de permiso, cámara ausente/ocupada, conexión o inferencia detienen el flujo y conservan los registros previos. Se mantiene una carga de imagen alternativa en una sección secundaria, sin exigirla para usar la cámara.

## Seguridad y capacidad

Las rutas conservan cookie anónima, aislamiento por navegador, origen exacto y CSRF. Cada fotograma admite hasta 2 MB; se valida el formato y el límite de píxeles. Se limita el ritmo a 60 fotogramas por minuto por IP y no se envían solicitudes solapadas desde la interfaz. El OCR sigue serializado por proceso. Un cambio condicional de secuencia y una restricción única evitan duplicados por reintentos concurrentes.

Tablas nuevas: `workspace_live_sessions` y `workspace_live_readings`. No se altera destructivamente el esquema anterior. En Railway se conservan en SQLite dentro del volumen ya configurado.

## Comprobación y límites

La señal simulada es opcional, está marcada como ficticia y repite una pantalla generada a través del mismo circuito OCR → estabilidad → registro. No es una webcam simulada del navegador ni evidencia de precisión sobre un instrumento físico. Permite probar el registro automático sin disponer de cámara.

Las pruebas cubren estabilidad temporal, deduplicación, oscilaciones de pulso, baja confianza, unidades ausentes, memoria, cierre, caducidad, aislamiento, revisión posterior, OCR real sintético y reintentos simultáneos. La exactitud sobre cámaras y aparatos reales debe evaluarse con ejemplos autorizados y modelos reservados. No hay un detector universal de modelos de instrumentos; los relojes se declaran manualmente.
