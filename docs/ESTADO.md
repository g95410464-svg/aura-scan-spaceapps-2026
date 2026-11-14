# Estado de la versión 0.1

Fecha: 14 de noviembre de 2026.

## Implementado

- Web React/TypeScript compilada y servida desde FastAPI, con experiencia de acceso, captura, revisión, historial y conocimiento.
- Registro/login, hash Argon2, cookie de sesión HttpOnly/SameSite, caducidad y CSRF para operaciones autenticadas. Validación de origen para escrituras.
- Base de datos SQLAlchemy: usuarios, sesiones, capturas, mediciones y auditoría. SQLite en desarrollo; URL PostgreSQL configurable.
- Captura con permiso del navegador y alternativa de carga. Límites de archivo, formato y píxeles; normalización sin metadatos EXIF y almacenamiento privado.
- OCR RapidOCR/ONNX real y asociación conservadora de etiquetas/unidades. Modelo exacto explícitamente desconocido; campos que no se leen no se completan por rango normal.
- Revisión manual obligatoria, conservación del valor extraído y de las correcciones, prevención de doble confirmación.
- PDF protegido por sesión, fuentes NASA/CSA y hallazgos informativos sobre procedencia y datos faltantes.
- Preparación de contenedor, configuración de persistencia y workflow de CI.

## Verificado localmente

- 23 pruebas de backend: OCR sobre pantalla sintética, confirmación, auditoría, unidades, ausencia de hora, PDF, acceso entre usuarios y CSRF.
- Compilación TypeScript y Vite.
- En navegador: registro de una cuenta ficticia, demostración con OCR, confirmación, informe en pantalla, historial y las cinco fichas científicas.
- En la demostración sintética se extrajeron 120/80 mmHg y 72 lpm. No es una prueba de exactitud clínica o de dispositivos físicos.

## Pendiente

1. Descargar y auditar acceso/licencias/anotaciones de Datumo/TILDE y Smart Scan; reservar modelos y sesiones para evaluación.
2. Probar pantallas reales, especialmente LCD de siete segmentos, reflejos, cambios de ángulo, memoria y errores. El parser actual se basa en etiquetas y geometría de filas, no en un detector universal de instrumentos.
3. Entrenar/evaluar identificación de pantallas/modelos y reconocimiento más amplio. Los cuatro tipos del formulario no equivalen a cuatro dispositivos físicamente validados.
4. Revisión clínica de escenarios y protocolos. Las reglas actuales no producen diagnóstico, riesgo de enfermedad ni pauta de tratamiento.
5. Publicación de la aplicación en un host elegido y verificación del enlace HTTPS. El repositorio de GitHub es público, pero no constituye hosting de Python.
6. Verificar PostgreSQL, construcción del contenedor, restauración, retención y eliminación de imágenes antes de habilitar datos reales. Docker no estaba activo durante la verificación local inicial.
7. Migraciones versionadas, paginación más allá de los últimos 100 registros, administración de cuentas y borrado de datos.
8. Pruebas con cámara física y distintos navegadores/dispositivos. La revisión del navegador usó una imagen sintética, no una cámara real.

## Decisiones de alcance

La solicitud más reciente prioriza lectura de pantallas sin conexión digital al aparato. Se amplía a categorías por etiquetas cuando el modelo exacto no se conoce, manteniendo la confirmación. La imagen por sí sola no prueba sujeto, fecha o correcta técnica de medición.

El PDF de arquitectura conserva su fecha y estado de planificación original. Este documento describe el avance posterior.
