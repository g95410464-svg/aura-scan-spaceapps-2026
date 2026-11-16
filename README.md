# AURA Scan

Prototipo ejecutable de una web de lectura visual en vivo de instrumentos médicos para el reto de salud espacial de NASA Space Apps 2026. Nombre de trabajo; sin afiliación ni aprobación de NASA.

**Estado 0.5:** interfaz React/TypeScript, API FastAPI, OCR real en Python, confirmación de lecturas, historial privado e informes PDF. Aplicación publicada en Railway; repositorio público.

Web: https://aura-scan-spaceapps-2026-production.up.railway.app/

Repositorio: https://github.com/g95410464-svg/aura-scan-spaceapps-2026

## Qué funciona

- Acceso directo a cámara en vivo al abrir la web, sin registro, contraseña ni inicio de sesión. Un espacio anónimo por navegador se prepara automáticamente con cookie HttpOnly.
- Cámara continua con registro automático de lecturas estables, deduplicación y evidencia. No requiere disparar fotos manualmente.
- Observaciones automáticas sin revisar separadas de las mediciones confirmadas; ambas aparecen en el historial y el asistente.
- Carga de imagen alternativa de PNG/JPEG/WebP, hasta 8 MB y 12 megapíxeles; fotogramas en vivo hasta 2 MB.
- OCR con RapidOCR/ONNX y OpenCV, seguido de asociación por etiquetas y unidades visibles.
- Campos de tensiómetro, pulsioxímetro, termómetro, glucómetro y reloj inteligente declarado manualmente; son categorías experimentales, no modelos físicos certificados.
- Revisión y corrección antes de confirmar. Se conservan candidatos originales y auditoría.
- Historial aislado por espacio de navegador, contexto declarado y tiempos de captura, medición y confirmación separados.
- Informe PDF y comparación numérica con el registro anterior comparable.
- Asistente de recomendaciones que reúne lecturas confirmadas por alias, contexto de misión, descanso, ánimo y antecedentes declarados.
- Recomendaciones por reglas con razones y referencias NASA/CSA; FDA y MedlinePlus complementan calidad de medición y señales de alarma declaradas.
- Cronología, diferencias numéricas entre confirmaciones comparables y datos faltantes; no hay diagnóstico automático.
- Botón Simulación visible que ejecuta tres pantallas sintéticas con OCR real y guía por historial, asistente e informe; datos ficticios separados.
- Más resolución, área de lectura ajustable, controles de enfoque disponibles y segunda pasada de contraste si faltan campos.

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

Abrir http://127.0.0.1:8000, abrir **Probar el flujo continuo sin usar una cámara** y pulsar **Iniciar señal simulada**. El visitante de la web publicada solo abre el enlace; estos comandos son para desarrollo.

### Idiomas

La web abre en inglés por defecto. El selector **English / Español** cambia la interfaz sin recargar la página y recuerda la preferencia en este navegador. Los PDF se descargan en el idioma seleccionado. Alias, notas escritas y datos de medición se conservan sin traducción ni conversión; `lpm` se muestra como `bpm` en inglés. El catálogo de traducciones se comparte en `shared/i18n`.

### Acceso directo e historial

La primera pantalla es la cámara en vivo. No hay cuentas, registro, contraseña ni botón de entrada. El navegador recibe automáticamente un espacio privado con una cookie de 30 días por defecto, renovable al abrir la web mientras siga vigente. Al caducar o borrar la cookie se abre un espacio nuevo; el historial anterior no se recupera desde la interfaz ni se sincroniza entre dispositivos. Descargar el PDF permite conservar una copia del informe.

### Desarrollo de interfaz

Con el backend activo, ejecutar `npm run dev` dentro de `frontend/`. Vite redirige `/api` al backend. Si se usa otro origen, configurar `PUBLIC_ORIGIN` con ese origen autorizado.

### Pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest
cd frontend
npm run build
```

GitHub Actions verifica backend e interfaz en cada push y pull request. Las pruebas incluyen OCR real sobre imagen sintética, aislamiento entre navegadores, CSRF, unidades, correcciones auditadas e informe PDF.

## Contenedor y persistencia

`docker compose up --build` compila React y sirve todo desde Python en http://127.0.0.1:8000. La configuración local usa un volumen persistente y SQLite. Docker Desktop/Engine debe estar activo.

Para un host HTTPS: construir con `Dockerfile`, montar almacenamiento persistente en `/data`, establecer `SECURE_COOKIES=true` y `PUBLIC_ORIGIN`. Configurar `DATABASE_URL` para PostgreSQL si corresponde. La aplicación normaliza `postgres://` al controlador psycopg. Ver [.env.example](.env.example) y [despliegue](docs/DESPLIEGUE.md).

La versión inicial crea las tablas ausentes al iniciar; no incluye migraciones de esquemas existentes. Antes de evolucionar un despliegue con datos se necesitan migraciones versionadas y copia/restauración probada. El almacenamiento de capturas es local a un volumen, no un bucket externo.

## Objetivo del producto

La entrega prevista es una web publicada donde el astronauta muestra la pantalla de un instrumento médico a la cámara. La versión 0.5 interpreta etiquetas, valores y unidades, y prepara una lectura para confirmación; la identificación de modelos exactos sigue pendiente. La observación estable se guarda automáticamente sin revisar; la revisión posterior permite incorporarla a las mediciones confirmadas y al informe.

En el despliegue final, el usuario abrirá un enlace sin instalar Python ni iniciar servicios locales.

## Documentación

- [Plan por fases y criterios de aceptación](docs/PLAN.md)
- [Arquitectura propuesta](docs/ARQUITECTURA.md)
- [Requisitos y límites del MVP](docs/REQUISITOS.md)
- [Fuentes y función de los cinco recursos](docs/FUENTES.md)
- [Modelo de datos inicial](docs/MODELO_DATOS.md)
- [Demostración guiada y manejo de reflejos](docs/DEMOSTRACION.md)
- [PowerPoint breve en inglés: funcionamiento y demostración](output/presentation/AURA_Scan_English_Presentation_Concise.pptx)
- [Guion en inglés y lista para ensayar](output/presentation/AURA_Scan_English_Speaker_Notes.md)
- [Flujo de cámara en vivo y registro automático](docs/LECTURA_EN_VIVO.md)
- [Funcionamiento y límites del asistente](docs/ASISTENTE.md)
- [Estado real, comprobaciones y pendientes](docs/ESTADO.md)
- [Preparación del despliegue](docs/DESPLIEGUE.md)
- [Plan de arquitectura en PDF](output/pdf/AURA_Scan_Plan_de_Arquitectura.pdf) (documento de planificación previo a esta implementación).

## Organización

```text
backend/
  app/
    main.py          API y composición de la versión inicial
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
    main.tsx         Interfaz de la versión inicial
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

Las carpetas aún reservadas contienen `.gitkeep`. No se publica ninguna credencial, base de datos privada ni captura privada en este repositorio. `tmp/` contiene únicamente trabajo local ignorado.
