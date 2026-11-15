# Arquitectura propuesta

Estado: arquitectura propuesta con una primera implementación parcial. Ver `ESTADO.md` para funciones comprobadas y límites de la versión 0.3.

```text
Navegador (cámara o imagen)
    → HTTPS: captura seleccionada
Servicio Python / FastAPI
    → calidad → modelo de instrumento → pantalla → OCR → campos candidatos
Navegador (revisión y confirmación)
    → API de mediciones
PostgreSQL + almacenamiento privado de evidencias
    → evaluación mediante reglas y conocimiento versionado
    → historial e informe
```

## Componentes

- Frontend propuesto: React, TypeScript y Vite, con instrucciones de encuadre y revisión de campos.
- Backend inicial: Python y FastAPI; OpenCV y RapidOCR/ONNX para lectura experimental. El reconocimiento especializado de LCD y modelos requiere pruebas adicionales.
- Persistencia propuesta: PostgreSQL para registros; almacenamiento privado separado para imágenes. No poner evidencias médicas en `frontend/public`.
- Conocimiento: catálogo de fuentes y protocolos versionados; solo reglas revisadas alimentan las funciones clínicas habilitadas.
- Publicación: frontend y API bajo el mismo origen HTTPS cuando el proveedor lo permita. Python y sus dependencias se despliegan en infraestructura administrada por el proyecto.
- Los proveedores y librerías exactas se eligen después de verificar compatibilidad, licencia y costo. No se han contratado servicios.

## Responsabilidades

La cámara la abre el navegador del usuario. Python recibe una captura; abrir una cámara desde Python en el servidor no da acceso a la cámara remota del usuario.

La identificación del aparato, la extracción de una lectura y su interpretación clínica son etapas independientes. Un error o dato faltante se conserva como tal, sin fabricar un valor para continuar.

No se requiere Bluetooth ni integración con el fabricante para leer una pantalla visible. Esto no garantiza compatibilidad con cualquier instrumento o LCD.

## API tentativa

- `POST /api/captures`: recibir una imagen autorizada.
- `POST /api/captures/{id}/analyze`: extraer candidatos y problemas de calidad.
- `GET /api/device-models`: consultar modelos y campos compatibles.
- `POST /api/measurements`: confirmar valores revisados y su procedencia.
- `GET /api/measurements`: consultar historial autorizado.
- `POST /api/assessments`: evaluar datos confirmados y síntomas.
- `GET /api/assessments/{id}/report`: consultar informe y referencias.

Los contratos y el procesamiento asíncrono se concretan durante la implementación. Autenticación y autorización aplican a capturas, mediciones, evaluaciones e informes.

## Privacidad y trazabilidad

- Separar las sesiones y datos de cada astronauta.
- No registrar imágenes, síntomas o credenciales en logs de infraestructura.
- Definir retención y eliminación de capturas antes de habilitar datos reales.
- Guardar versión del reconocedor, cambios del usuario y versión de reglas.
- No confundir la confianza del OCR con una probabilidad de enfermedad.
- Un valor fuera de rango no se corrige a un valor normal: se revisa o se solicita repetir la lectura.

## Disponibilidad

La web publicada no exige instalación al usuario. El procesamiento Python remoto depende de red y del servidor; no se promete funcionamiento sin conexión en este alcance.

La sección Asistente reúne la evidencia confirmada por alias, añade contexto y aplica reglas de seguimiento con fuentes. `workspace_health_contexts` conserva las declaraciones de forma acumulativa. No hay un motor de diagnóstico generativo; véase `ASISTENTE.md`.
