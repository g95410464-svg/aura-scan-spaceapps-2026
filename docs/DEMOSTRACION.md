# Demostración para la entrega

## Ruta principal

Abrir https://aura-scan-spaceapps-2026-production.up.railway.app/ y pulsar **Simulación**. El servidor ejecuta OCR real en tres pantallas sintéticas, crea un alias de demostración aislado y añade registros ficticios con procedencia `simulation_scripted`. El recorrido conduce por Lecturas, Historial, Asistente e Informe. Al repetir una solicitud con el mismo identificador no se duplica el escenario.

Valores guionados: presión inicial 120/80 mmHg y pulso 72 lpm; segunda presión 126/82 y pulso 78; oxímetro 98% y pulso 75. El asistente muestra +6 mmHg de sistólica y +2 mmHg de diastólica como diferencias numéricas, sin diagnosticar su causa.

Todos los valores, horas y contexto son ficticios. La simulación no representa una evaluación clínica ni valida la precisión en instrumentos reales. La confirmación guionada del escenario no se presenta como revisión humana. El modo en vivo conserva su registro automático pendiente de revisión.

## Cámara y reflejos

Se solicita una fuente de hasta 2560×1440 si la cámara la ofrece. La interfaz muestra los píxeles realmente recibidos; no promete una resolución que el equipo no soporte. El fotograma conserva hasta 2048 px de lado y se comprime en JPEG con calidad ajustable para mantener el límite de 2 MB. El área central se puede recortar entre 1× y 3×; se deben incluir etiquetas y unidades.

Se solicita enfoque, exposición y balance de blancos continuos solo si las capacidades del dispositivo lo permiten. Si el OCR original está incompleto, una segunda pasada con contraste local CLAHE intenta mejorar las condiciones desiguales. No se mezclan lecturas contradictorias entre versiones. La geometría del parser se normaliza para que aumentar resolución no rompa la asociación de filas.

Una zona sobreexpuesta puede haber perdido la información del número. Se advierte de posibles reflejos y se recomienda ajustar ligeramente el ángulo y usar luz lateral. El procesamiento no reconstruye números tapados por un reflejo. Faltan pruebas de exactitud en dispositivos físicos y LCD de siete segmentos.

## Presentación

El PowerPoint en inglés se entrega en `output/presentation`. Las notas del presentador contienen un guion y las referencias. La presentación usa una fotografía de contexto NASA y capturas de datos ficticios del producto; no muestra que NASA haya probado o aprobado la aplicación.

## Interfaz breve

La vista principal prioriza cifras y acciones cortas. Las razones, fuentes, evidencia y cronología se abren bajo demanda. Se muestran tres acciones y el resto queda en «Más acciones». Las señales de alarma declaradas conservan la instrucción de emergencia visible y prioritaria. El PowerPoint breve mantiene la explicación completa en las notas.

## Idioma para presentar

La web abre en inglés y recuerda la elección del selector English / Español. El recorrido en inglés es Simulation → Next: History → Next: Assistant → Next: Report. Las fuentes y mensajes se traducen al mostrarlos; el contenido original de las notas y las mediciones no cambia. El PDF usa el idioma activo.
