# Requisitos del producto

## Confirmados en la conversación

- [x] Entrega virtual mediante una web publicada, con entrada directa al sistema, sin registro ni inicio de sesión.
- [x] Python para el análisis de imágenes.
- [x] Reconocer instrumentos compatibles y leer sus pantallas LCD mediante cámara.
- [x] Agregar las mediciones al historial e informe para aportar información a la evaluación de salud.
- [x] Base de datos de astronautas y mediciones.
- [x] Base de conocimientos sobre riesgos, evaluaciones y actuaciones documentadas.
- [x] Integrar los cinco recursos proporcionados por el usuario.
- [x] Responder al reto de monitoreo de salud de astronautas compartido en el chat.

Estas marcas confirman decisiones de alcance, no funciones implementadas.

## Requisitos funcionales propuestos

- RF01: capturar una imagen desde la web y cargar un archivo como alternativa.
- RF02: identificar un modelo compatible o solicitar selección cuando no sea concluyente.
- RF03: extraer números, etiquetas, decimales y unidades con evidencia visual.
- RF04: advertir estados ilegibles, errores del instrumento y posibles pantallas de memoria.
- RF05: revisar, corregir y confirmar antes de incorporar datos a una evaluación.
- RF06: guardar historial por astronauta y procedencia por medición.
- RF07: recoger síntomas y contexto declarados.
- RF08: mostrar una evaluación orientativa, datos faltantes y actuaciones respaldadas por reglas y fuentes.
- RF09: generar un informe imprimible con valores, tiempos, procedencias y referencias.
- RF10: disponer de una demostración identificada como ficticia.
- RF11: abrir directamente la captura al visitar la web, sin cuentas; separar el historial mediante un espacio anónimo de navegador.

## Límites del MVP

- Compatibilidad con modelos definidos y probados; no reconocimiento universal.
- Prioridad: un modelo de termómetro, uno de tensiómetro y uno de pulsioxímetro.
- El análisis del cuerpo mediante cámara queda como ampliación con validación independiente.
- No asumir que ver el instrumento prueba a quién se midió, que la técnica fue correcta o que la lectura es reciente.
- No derivar diagnósticos definitivos o tratamientos personalizados de una imagen aislada.
- Los cinco recursos científicos no se presentan como una biblioteca clínica completa.
- No prometer exactitud médica, aprobación de NASA, acceso a datos privados de la ISS ni funcionamiento offline.

## Evidencia de aceptación

Conservar resultados de pruebas de reconocimiento por dispositivo, ejemplos de errores, capturas del recorrido publicado y trazabilidad del informe. Las métricas de rendimiento solo se anuncian después de medirlas.
