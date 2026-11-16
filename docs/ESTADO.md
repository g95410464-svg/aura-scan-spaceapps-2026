# Estado de la versión 0.5

Fecha: 14 de noviembre de 2026.

## Implementado

- Web React/TypeScript compilada y servida desde FastAPI, con entrada directa a captura, revisión, historial y conocimiento.
- Entrada directa, sin cuentas ni formularios de acceso. Espacio anónimo automático, cookie HttpOnly/SameSite, caducidad y CSRF. Validación de origen para escrituras.
- Base de datos SQLAlchemy: espacios anónimos, sesiones de navegador, capturas, mediciones y auditoría. SQLite en desarrollo; URL PostgreSQL configurable.
- Captura con permiso del navegador y alternativa de carga. Límites de archivo, formato y píxeles; normalización sin metadatos EXIF y almacenamiento privado.
- OCR RapidOCR/ONNX real y asociación conservadora de etiquetas/unidades. Modelo exacto explícitamente desconocido; campos que no se leen no se completan por rango normal.
- Revisión manual obligatoria, conservación del valor extraído y de las correcciones, prevención de doble confirmación.
- PDF protegido por sesión, fuentes NASA/CSA y hallazgos informativos sobre procedencia y datos faltantes.
- Asistente por reglas con contexto, antecedentes declarados, cronología y recomendaciones con fuentes. Lectura experimental de reloj declarado manualmente.
- Contenedor, volumen persistente Railway y workflow de CI.
- Dominio público: https://aura-scan-spaceapps-2026-production.up.railway.app/ ; corregido el origen HTTPS tras el proxy.

## Verificado localmente

- 50 pruebas de backend: OCR sobre pantalla sintética, confirmación, auditoría, unidades, ausencia de hora, PDF, aislamiento entre navegadores, caducidad y ausencia de endpoints de cuentas y CSRF.
- Compilación TypeScript y Vite.
- Backend e interfaz aprobados también en GitHub Actions sobre Linux para el commit inicial.
- En navegador para la versión 0.4: entrada directa sin cuenta, demostración con OCR, confirmación, informe en pantalla y recarga seguida de historial conservado. Además, se comprobó el formulario de contexto, las recomendaciones según entorno/descanso/ánimo y su cronología.
- Carga de una imagen sintética desde el selector de archivos del navegador; OCR y campos revisables comprobados.
- El espacio anónimo se reutiliza al recargar mientras su cookie siga vigente; una cookie nueva no permite consultar el historial de otra.
- En la demostración sintética se extrajeron 120/80 mmHg y 72 lpm. No es una prueba de exactitud clínica o de dispositivos físicos.

## Pendiente

1. Descargar y auditar acceso/licencias/anotaciones de Datumo/TILDE y Smart Scan; reservar modelos y sesiones para evaluación.
2. Probar pantallas reales, especialmente LCD de siete segmentos, reflejos, cambios de ángulo, memoria y errores. El parser actual se basa en etiquetas y geometría de filas, no en un detector universal de instrumentos.
3. Entrenar/evaluar identificación de pantallas/modelos y reconocimiento más amplio. Las cinco categorías del formulario no equivalen a dispositivos físicamente validados.
4. Revisión clínica de escenarios y protocolos. Las reglas actuales no producen diagnóstico, riesgo de enfermedad ni pauta de tratamiento.
5. Ampliar validación de producción, retención, borrado y restauración. La aplicación ya está publicada en Railway.
6. Verificar PostgreSQL, construcción del contenedor, restauración, retención y eliminación de imágenes antes de habilitar datos reales. Docker no estaba activo durante la verificación local inicial.
7. Migraciones versionadas, paginación más allá de los últimos 100 registros, retención y borrado de datos.
8. Pruebas con cámara física y distintos navegadores/dispositivos. La revisión del navegador usó una imagen sintética, no una cámara real.

## Decisiones de alcance

La solicitud más reciente prioriza lectura de pantallas sin conexión digital al aparato. Se amplía a categorías por etiquetas cuando el modelo exacto no se conoce, manteniendo la confirmación. La imagen por sí sola no prueba sujeto, fecha o correcta técnica de medición.

El PDF de arquitectura conserva su fecha y estado de planificación original. Este documento describe el avance posterior.

La entrada directa sustituye el registro de la versión 0.1. El historial depende de una cookie anónima con 30 días de duración renovable por defecto; no se comparte entre navegadores ni se recupera al perder esa cookie. Las tablas antiguas permanecen conservadas y fuera de la API nueva.

El asistente usa reglas revisables y referencias, no un modelo diagnóstico o chat generativo. Véase `ASISTENTE.md`. La carga de una imagen sintética en el dominio público se verificó con respuesta 201 y OCR 120/80 mmHg y 72 lpm tras corregir la validación de origen.

## Cámara en vivo 0.4

La entrada principal mantiene la cámara abierta y registra automáticamente valores estables, sin disparador manual. Las observaciones sin revisar se conservan separadas de las mediciones confirmadas. La señal sintética continua se comprobó en navegador: un registro automático, deduplicación al continuar la misma pantalla y detención del flujo. Faltan pruebas de exactitud con cámara e instrumentos físicos; ver `LECTURA_EN_VIVO.md`.

## Entrega 0.5

Simulación guiada con tres lecturas sintéticas procesadas por OCR, historial aislado, contexto, recomendaciones y PDF con procedencia guionada. Mejoras de entrada de imagen y contraste, indicaciones de reflejo y normalización de geometría. No resuelven reflejos que oculten datos ni sustituyen la evaluación de dispositivos reales.
