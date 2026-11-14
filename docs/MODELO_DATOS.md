# Modelo de datos inicial

Esquema conceptual propuesto. La versión 0.1 implementa usuarios, sesiones de acceso, capturas, mediciones y auditoría con SQLAlchemy; los perfiles clínicos, protocolos y relaciones avanzadas siguen pendientes. Ver `ESTADO.md`.

| Entidad | Campos principales |
|---|---|
| Usuarios y perfiles | Identidad, permisos, vínculo al astronauta; antecedentes declarados separados de diagnósticos verificados. |
| Modelos de instrumento | Fabricante/modelo, categoría, campos esperados, unidades admitidas, distribución de pantalla, estados de error/memoria y versión de compatibilidad. |
| Sesiones de evaluación | Astronauta, autor, síntomas, contexto, inicio y estado. |
| Capturas | Sesión, archivo privado, hora de captura, calidad, modelo candidato y versión del análisis. |
| Extracciones | Captura, texto original, campo candidato, valor/unidad candidatos, coordenadas, confianza técnica y problemas detectados. |
| Mediciones confirmadas | Astronauta, sesión, extracción si existe, código de indicador, valor, unidad, hora de medición si se conoce, procedencia y confirmación. |
| Fuentes | Organismo, título, URL, versión/fecha, afirmaciones respaldadas y revisión. |
| Protocolos y reglas | Versión, fuentes, criterios, datos necesarios, exclusiones, actuaciones y estado de revisión. |
| Evaluaciones | Mediciones confirmadas utilizadas, reglas/versiones aplicadas, hallazgos, posibilidades, incertidumbre y datos faltantes. |
| Informes | Evaluación, versión, fecha, contenido y referencias a evidencias autorizadas. |
| Auditoría | Actor, entidad, operación, momento y cambios de valores o confirmaciones. |

## Reglas de integridad

- La captura pertenece a una sesión y a un sujeto identificados por el usuario; reconocer un dispositivo no identifica al paciente.
- Separar hora de captura, hora de medición y hora de confirmación. Conservar desconocidos explícitos.
- Mantener valor original y valor corregido; no sobrescribir la evidencia del OCR.
- Presión sistólica, diastólica y pulso son campos diferentes; no depender solo del orden visual.
- Temperatura debe conservar escala y lugar/tipo de medición cuando se conozca; temperatura cutánea no equivale automáticamente a temperatura central.
- Validar tipos, unidades y coherencia sin sustituir valores anómalos por valores normales.
- `pendiente`, `confirmada`, `rechazada` y `sustituida` describen el ciclo de una medición; solo las confirmadas pueden alimentar evaluaciones.
- Registrar correcciones con autor y fecha; distinguir datos reales, ficticios y manuales.
- El consentimiento, las restricciones de acceso y la política de retención se implementan antes de habilitar datos reales.
