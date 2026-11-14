# AURA Scan

Primera versión ejecutable de una web de captura visual de instrumentos médicos para el reto de salud espacial de NASA Space Apps 2026. Nombre de trabajo; sin afiliación ni aprobación de NASA.

**Estado 0.1:** interfaz React/TypeScript, API FastAPI, OCR real en Python, confirmación de lecturas, historial privado e informes PDF. El despliegue público de la aplicación todavía no se ha realizado. El repositorio sí es público.

Repositorio: https://github.com/g95410464-svg/aura-scan-spaceapps-2026

## Qué funciona

- Registro e inicio de sesión con contraseñas Argon2 y sesiones en cookies HttpOnly.
- Captura desde cámara o carga de PNG/JPEG/WebP, hasta 8 MB y 12 megapíxeles.
- OCR con RapidOCR/ONNX y OpenCV, seguido de asociación por etiquetas y unidades visibles.
- Campos de tensiómetro, pulsioxímetro, termómetro y glucómetro; son categorías experimentales, no modelos físicos certificados.
- Revisión y corrección antes de confirmar. Se conservan candidatos originales y auditoría.
- Historial aislado por usuario, contexto declarado y tiempos de captura, medición y confirmación separados.
- Informe PDF y comparación numérica con el registro anterior comparable.
- Cinco recursos NASA/CSA integrados como fichas de contexto y referencias en informes.
- Demostración con pantalla sintética procesada por el mismo OCR, identificada como ficticia.

**Límite de la versión:** no hay clasificador entrenado de modelos exactos, conjunto Datumo/Smart Scan integrado, diagnóstico médico ni tratamiento validado. La prueba sintética no demuestra precisión sobre instrumentos reales ni de la ISS. El sistema no completa una unidad ausente por suposición; pide revisión.

## Ejecutar desde el código

Requisitos: Python 3.12 y Node.js 22. No se necesita una clave de IA ni Tesseract instalado por separado. Los modelos de OCR se incluyen en el paquete RapidOCR.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
cd frontend
npm ci
npm run build
cd ..
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

En Linux/macOS, sustituir `.\.venv\Scripts\python.exe` por `.venv/bin/python`.

Abrir http://127.0.0.1:8000, crear una cuenta de prueba y pulsar **Usar demostración**. El usuario de una futura web publicada solo abrirá el enlace; estos comandos son para desarrollo.

### Desarrollo de interfaz

Con el backend activo, ejecutar `npm run dev` dentro de `frontend/`. Vite redirige `/api` al backend. Si se usa otro origen, configurar `PUBLIC_ORIGIN` con ese origen autorizado.

### Pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest
cd frontend
npm run build
```

GitHub Actions verifica backend e interfaz en cada push y pull request. Las pruebas incluyen OCR real sobre imagen sintética, aislamiento entre usuarios, CSRF, unidades, correcciones auditadas e informe PDF.

## Contenedor y persistencia

`docker compose up --build` compila React y sirve todo desde Python en http://127.0.0.1:8000. La configuración local usa un volumen persistente y SQLite. Docker Desktop/Engine debe estar activo.

Para un host HTTPS: construir con `Dockerfile`, montar almacenamiento persistente en `/data`, establecer `SECURE_COOKIES=true` y `PUBLIC_ORIGIN`. Configurar `DATABASE_URL` para PostgreSQL si corresponde. La aplicación normaliza `postgres://` al controlador psycopg. Ver [.env.example](.env.example) y [despliegue](docs/DESPLIEGUE.md).

La versión inicial crea las tablas ausentes al iniciar; no incluye migraciones de esquemas existentes. Antes de evolucionar un despliegue con datos se necesitan migraciones versionadas y copia/restauración probada. El almacenamiento de capturas es local a un volumen, no un bucket externo.

## Producto

Una web publicada donde el astronauta muestra la pantalla de un instrumento médico a la cámara. Un servicio Python identifica un modelo compatible, interpreta sus etiquetas, valores y unidades, y prepara una lectura para confirmación. La lectura confirmada se incorpora al historial, a una evaluación orientativa y al informe.

El usuario final abre un enlace; no instala Python ni inicia servicios locales.

## Documentación

- [Plan por fases y criterios de aceptación](docs/PLAN.md)
- [Arquitectura propuesta](docs/ARQUITECTURA.md)
- [Requisitos y límites del MVP](docs/REQUISITOS.md)
- [Fuentes y función de los cinco recursos](docs/FUENTES.md)
- [Modelo de datos inicial](docs/MODELO_DATOS.md)
- [Estado real, comprobaciones y pendientes](docs/ESTADO.md)
- [Preparación del despliegue](docs/DESPLIEGUE.md)
- [Plan de arquitectura en PDF](output/pdf/AURA_Scan_Plan_de_Arquitectura.pdf) (documento de planificación previo a esta implementación).

## Organización

```text
backend/
  app/
    api/             Endpoints y contratos
    core/            Configuración y seguridad
    vision/          Calidad de captura, pantalla y OCR
    devices/         Catálogo de modelos y formatos compatibles
    measurements/   Validación, confirmación e historial de lecturas
    assessments/    Evaluación orientativa y datos faltantes
    knowledge/      Consulta de conocimiento y reglas versionadas
    reports/        Informes y trazabilidad
    storage/        Persistencia y acceso a evidencias
  migrations/       Cambios de esquema de base de datos
frontend/
  src/
    components/      Componentes comunes
    features/
      capture/       Cámara, carga y guía de encuadre
      measurements/ Revisión y confirmación
      assessments/  Evaluación y siguientes pasos
      reports/       Informe
      history/       Evolución temporal
    services/        Cliente de la API
  public/            Recursos públicos de interfaz
knowledge/
  sources/           Catálogo y extractos científicos revisados
  protocols/         Protocolos y reglas con fuentes y revisión
data/samples/        Material ficticio o autorizado para desarrollo
tests/
  vision/            Evaluación del reconocimiento
  integration/       Flujo de datos y reglas
  e2e/               Recorrido completo del navegador
docs/                Decisiones y planificación
infra/               Configuración futura de despliegue
```

Las carpetas aún reservadas contienen `.gitkeep`. No se publica ninguna credencial, base de datos de usuarios ni captura privada en este repositorio. `tmp/` contiene únicamente trabajo local ignorado.
