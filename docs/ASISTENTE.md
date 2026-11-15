# Asistente de seguimiento 0.3

La sección Asistente de salud sustituye las fichas de Conocimiento. Funciona con reglas explícitas, sin modelo generativo ni envío de datos de salud a un proveedor de IA.

## Flujo

1. Cámara o archivo → OCR de números, etiquetas y unidades → revisión humana obligatoria.
2. La confirmación une la lectura al alias dentro del espacio privado de ese navegador. El alias no autentica una identidad ni identifica automáticamente a quien se midió.
3. El asistente reúne hasta 500 mediciones confirmadas por alias y tipo de datos, con hasta 50 declaraciones de contexto. Nunca combina datos ficticios con reales ni datos de otro navegador.
4. Se pueden añadir entorno, sueño, ánimo, síntomas y antecedentes/alergias/tratamientos declarados. Cada actualización se conserva como evento, no sobrescribe declaraciones anteriores. El texto libre se conserva para revisión humana: no se interpreta ni se usa para establecer diagnósticos.
5. Se actualizan evidencia disponible, diferencias numéricas, datos faltantes, recomendaciones con propósito y fuentes, y los últimos 50 eventos de la cronología.

## Reglas y límites

- Solo lecturas confirmadas; capturas pendientes no alimentan el asistente.
- Diferencias entre las dos últimas confirmaciones de igual indicador, unidad y categoría. No significan mejoría, empeoramiento ni orden real de medición; se muestran por separado las horas conocidas de medición y confirmación. Modelos exactos y equivalencia entre instrumentos no están verificados.
- El reloj inteligente se declara en el formulario; acepta pulso y SpO2 con etiquetas visibles. No es un clasificador entrenado ni se presume que el reloj sea apto para decisiones clínicas.
- Las recomendaciones dependen de los indicadores presentes y del contexto declarado. No hay puntuación de enfermedad, probabilidades diagnósticas, umbrales universales de normalidad, medicación ni dosificación.
- Marcar dolor/ presión intensa de pecho, dificultad importante para respirar o desmayo/confusión nueva muestra una alerta inmediata en el formulario, y tras guardar prioriza activar el protocolo de emergencia. No depende de otra medición. No seleccionar estas casillas no descarta una emergencia.
- Las consultas guiadas resumen seguimiento, cambios, datos faltantes, entorno o radiación. No son un chat abierto ni un diagnóstico por inteligencia artificial.
- Los informes PDF existentes documentan cada medición. El contexto y antecedentes nuevos se consultan en la cronología; aún no se exportan como informe médico longitudinal completo.

## Papel de las fuentes

| Fuente | Aplicación |
| --- | --- |
| NASA: peligros | Entorno, aislamiento, distancia y condiciones del hábitat; no atribuir automáticamente la causa de un síntoma. |
| NASA: riesgos | Contexto cardiovascular, sueño y bienestar; no un catálogo de tratamientos. |
| NASA: investigación HRP | Seguimiento consistente de medidas físicas y psicológicas. |
| CSA: CANS | Solicitar dosimetría dedicada; no inferir exposición por cámara, pulso o SpO2. |
| CSA: ciencia en el espacio | Preparar información y autonomía ante misiones lejanas. |
| FDA: Pulse Oximeter Basics | Técnica, síntomas y limitaciones de precisión. |
| MedlinePlus: Recognizing medical emergencies | Señales generales de alarma; en misión se usa su protocolo propio. |

Las referencias se consultaron el 14 de noviembre de 2026. Los enlaces originales se conservan junto a cada recomendación. Son una base de contexto, no aprobación de las reglas por NASA/CSA/FDA/MedlinePlus ni un protocolo médico validado.

## Persistencia y acceso

Sin cuentas ni login. Cookie HttpOnly/SameSite con 30 días por defecto (`AURA_SESSION_HOURS=720`); al abrir la web se renueva si queda menos de la mitad. Una cookie perdida o caducada no permite recuperar el espacio. Los datos siguen separados entre navegadores y no hay recuperación entre dispositivos.

Se añadió un volumen Railway de 500 MB en `/aura-data`, destinado a SQLite y capturas. No recupera datos de despliegues previos en almacenamiento efímero. Antes de usar datos médicos reales faltan revisión clínica, política de retención y borrado, restauración probada y una estrategia de continuidad entre dispositivos.
