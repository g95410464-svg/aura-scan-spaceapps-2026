# Plan de ejecución

Actualización del 14/11/2026: existe una primera versión ejecutable con lectura por etiquetas, confirmación, historial y PDF. Este plan conserva el alcance completo; ver `ESTADO.md` para distinguir lo implementado de lo validado. La compatibilidad por modelo físico y los protocolos clínicos siguen pendientes.

## Objetivo verificable

Entregar una web accesible mediante HTTPS que permita mostrar un instrumento a la cámara, extraer sus lecturas, revisarlas, guardarlas y generar un informe con procedencia y una evaluación orientativa basada en conocimiento documentado.

El alcance inicial propuesto es un modelo concreto de termómetro, uno de tensiómetro y uno de pulsioxímetro. Su selección está pendiente de disponer de ejemplos autorizados. No se promete compatibilidad universal.

## Fase 0 — Evidencia y alcance

- [ ] Revisar el enunciado y las reglas oficiales de la sede; documentar requisitos de entrega y uso de recursos. El mínimo de un recurso fue informado por el usuario y no se ha verificado aquí como regla oficial.
- [ ] Elegir los tres modelos de instrumentos; reunir manuales y capturas de sus pantallas.
- [ ] Definir campos y etiquetas: temperatura/unidad; SYS/DIA/PUL; SpO2/PR, según cada modelo.
- [ ] Reunir ejemplos de lectura actual, memoria, error, batería baja, desenfoque, reflejos y cambios de ángulo.
- [ ] Separar imágenes de desarrollo y evaluación, por sesiones de captura, sin duplicar fotogramas casi idénticos entre ambos conjuntos.
- [ ] Definir escenarios clínicos acotados y qué protocolos adicionales necesitan revisión.

Aceptación: catálogo inicial, material de evaluación y límites escritos. Cada escenario tiene fuentes y datos requeridos; no hay tratamientos inventados.

## Fase 1 — Prueba del reconocimiento en Python

- [ ] Implementar control de calidad: pantalla visible, tamaño suficiente, reflejos y desenfoque.
- [ ] Evaluar localización de pantalla y reconocimiento del modelo mediante plantillas o un detector; escoger con evidencia.
- [ ] Implementar recorte, corrección de perspectiva y preparación de imagen.
- [ ] Comparar OCR general y reconocimiento de dígitos de siete segmentos sobre las capturas disponibles.
- [ ] Interpretar valores, decimales, etiquetas y unidades; rechazar campos ambiguos.
- [ ] Conservar el texto original y las coordenadas de cada campo para revisar errores.

Aceptación: informe por modelo con aciertos exactos por campo, errores de unidad/etiqueta y capturas rechazadas. Los umbrales de calidad se fijan antes de evaluar el conjunto reservado. Un dato ilegible no se completa por suposición.

## Fase 2 — Web y API

- [x] Crear interfaz de captura con permiso explícito de cámara y alternativa de cargar una imagen.
- [ ] Publicar un primer entorno de prueba con frontend y Python conectados mediante HTTPS.
- [x] Analizar una captura estable; no transmitir video continuamente en el MVP.
- [x] Mostrar la imagen original junto a los campos propuestos (recorte automático de pantalla pendiente).
- [ ] Permitir confirmar, corregir o repetir; si el dispositivo no se reconoce, permitir seleccionar un modelo compatible.
- [ ] Controlar tamaño y formato de archivos, tiempos de espera y errores de procesamiento.

Aceptación: el recorrido cámara → análisis → revisión funciona desde un navegador remoto sin instalaciones del usuario. Se comprueba también el comportamiento al denegar la cámara.

## Fase 3 — Base de datos e informe

- [ ] Implementar perfiles, evaluaciones, capturas, lecturas y eventos de auditoría.
- [x] Separar el valor extraído, el corregido y el confirmado; conservar los cambios.
- [x] Registrar sujeto por alias, categoría del instrumento, unidad, hora de captura y hora de medición si se conoce.
- [ ] Incorporar síntomas, antecedentes declarados y mediciones manuales con su procedencia (síntomas y transcripción manual implementados; antecedentes pendientes).
- [x] Crear historial y un informe imprimible/exportable a PDF.
- [x] Separar datos ficticios declarados de datos reales y limitar el acceso por usuario.

Aceptación: ninguna extracción pendiente alimenta una evaluación clínica. El informe permite rastrear cada dato hasta su captura y confirmación. Desconocer la hora de medición no se resuelve usando silenciosamente la hora de captura.

## Fase 4 — Conocimiento y apoyo a la evaluación

- [x] Convertir los cinco recursos en fichas de contexto estructuradas según `FUENTES.md` (no protocolos terapéuticos).
- [ ] Añadir fuentes clínicas específicas cuando los recursos generales no contienen un protocolo suficiente.
- [ ] Preparar tres escenarios demostrativos revisables; selección pendiente de la evidencia disponible.
- [ ] Implementar reglas explícitas que muestren hallazgos, posibilidades, datos faltantes y siguientes comprobaciones.
- [ ] Mantener independientes calidad de imagen, confianza de extracción e incertidumbre clínica.
- [ ] Versionar protocolos, condiciones de aplicación, exclusiones, fuentes y estado de revisión.
- [ ] Mostrar tratamientos concretos para uso real solo con protocolo aplicable y revisión clínica; en la demo, identificar cualquier contenido ilustrativo.

Aceptación: cada salida tiene reglas y fuentes rastreables. El sistema reconoce cuándo faltan datos. No emite un diagnóstico definitivo ni una pauta farmacológica a partir de una pantalla aislada. Una IA conversacional, si se añade, no inventa lecturas, fuentes ni protocolos.

## Fase 5 — Publicación y demostración

- [ ] Preparar despliegue reproducible del backend, frontend, base de datos y dependencias del OCR.
- [ ] Configurar secretos fuera del repositorio, límites de acceso, retención y eliminación de capturas.
- [ ] Verificar persistencia, aislamiento de usuarios, HTTPS, restauración de datos y errores de red.
- [ ] Probar modelos compatibles en las condiciones de captura declaradas y navegadores objetivo.
- [ ] Preparar una demo con datos ficticios: lectura correcta, lectura ilegible y corrección de OCR.
- [ ] Publicar instrucciones de uso y limitaciones junto al enlace final.

Aceptación: un evaluador abre el enlace y completa el recorrido sin configurar nada. Solo se anuncian las funciones efectivamente probadas.

## Ampliaciones posteriores

- Análisis del propio astronauta: pulso experimental por video y seguimiento de movimientos, con evaluación separada de la lectura de pantallas.
- Más modelos de dispositivos y carga de resultados de laboratorio o imágenes clínicas.
- Conexiones digitales directas cuando exista un dispositivo compatible y acceso autorizado.
- Comparación longitudinal personalizada con criterios clínicos revisados.
- Operación independiente de internet: requiere otra arquitectura; el MVP publicado con Python remoto necesita conexión.

## Decisiones abiertas

1. Modelos exactos y disponibilidad de capturas.
2. Escenarios clínicos y responsable de revisión.
3. Nombre final y diseño visual.
4. Proveedor y presupuesto de hosting, región y política de almacenamiento.
5. Navegadores objetivo, condiciones de captura y umbrales de aceptación.

No se fijan fechas ni costos hasta conocer equipo, plazo, modelos y recursos disponibles. El primer hito será demostrar lectura verificable de un instrumento de extremo a extremo.
