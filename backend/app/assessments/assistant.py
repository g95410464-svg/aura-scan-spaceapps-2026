"""Evidence-based follow-up rules; no disease classifier or generated prescriptions."""
from datetime import datetime, timezone
from backend.app.devices.catalog import FIELDS, DEVICES
from backend.app.knowledge.sources import SOURCES

SUPPORTING_SOURCES = [
    {'id':'fda-oximeter', 'organization':'FDA', 'title':'Uso y límites del pulsioxímetro',
     'url':'https://www.fda.gov/consumers/consumer-updates/pulse-oximeter-basics',
     'summary':'La interpretación requiere síntomas y conocer las limitaciones del instrumento.'},
    {'id':'medline-emergency', 'organization':'MedlinePlus', 'title':'Señales de una emergencia médica',
     'url':'https://medlineplus.gov/ency/article/001927.htm',
     'summary':'Señales generales de alarma; en una misión se sigue su protocolo de emergencia.'},
]
ENVIRONMENTS = {'unknown':'Sin especificar','station':'Estación espacial','spacecraft':'Nave espacial',
                'moon':'Superficie lunar','mars':'Superficie de Marte','earth':'Tierra / simulación'}
RED_FLAGS = {'chest_pain':'Dolor o presión intensa en el pecho', 'breathing':'Dificultad importante para respirar',
             'consciousness':'Desmayo o confusión nueva'}


def context_data(item):
    if item is None:
        return None
    return {key:getattr(item,key) for key in ['id','subject_alias','is_demo','created_at','environment','sleep_hours','mood','symptoms','medical_notes','red_flags']}


def build_assistant(records, contexts, subject_alias, is_demo, intent='overview'):
    # Callers scope by browser, alias and demo status before passing any evidence.
    records = sorted(records, key=lambda r:r.created_at, reverse=True)
    contexts = sorted(contexts, key=lambda c:c.created_at, reverse=True)
    context = contexts[0] if contexts else None
    observations, recommendations, gaps = [], [], []
    metrics = []
    def recommend(code, title, action, reason, source_ids, priority='follow_up'):
        recommendations.append({'id':code,'title':title,'action':action,'reason':reason,
                                'source_ids':source_ids,'priority':priority})
    codes = list(dict.fromkeys(r['code'] for record in records for r in record.readings))
    for code in codes:
        samples = [(record, reading) for record in records for reading in record.readings if reading['code']==code]
        record, reading = samples[0]
        comparable = [(r,v) for r,v in samples[1:] if v['unit']==reading['unit'] and r.device_type==record.device_type]
        previous = comparable[0] if comparable else None
        # Numeric comparison follows confirmation order; never imply measurement chronology when unknown.
        delta = round(reading['value']-previous[1]['value'],3) if previous else None
        metrics.append({'code':code,'label':FIELDS[code]['label'],'value':reading['value'],'unit':reading['unit'],
                        'record_id':record.id,'device_type':record.device_type,'confirmed_at':record.created_at,
                        'measured_at':record.measured_at,'delta':delta,'previous_id':previous[0].id if previous else None,
                        'comparison_basis':'confirmation_order' if previous else None,
                        'series':[{'value':v['value'],'confirmed_at':r.created_at,'measured_at':r.measured_at}
                                  for r,v in reversed([(r,v) for r,v in samples if v['unit']==reading['unit'] and r.device_type==record.device_type][:20])]})
    if records:
        count=len(records); categories=len({r.device_type for r in records})
        observations.append(f'{count} '+('registro confirmado' if count==1 else 'registros confirmados')+f' de {categories} '+('categoría de instrumento' if categories==1 else 'categorías de instrumento')+' para este alias.')
        if any(m['delta'] is not None for m in metrics):
            observations.append('Las diferencias comparan las dos últimas confirmaciones de cada indicador con igual unidad y categoría; no establecen mejoría, enfermedad ni orden de medición.')
            recommend('repeat','Construye una serie comparable','Repite las mediciones indicadas en el plan de misión con el mismo instrumento y condiciones; registra fecha, actividad y síntomas.',
                      'Las diferencias necesitan contexto antes de que el responsable médico pueda interpretarlas.',['nasa-research','csa-science'])
        else:
            gaps.append('Falta otra lectura de la misma categoría y unidad para comparar los indicadores.')
        if any(not r.measured_at for r in records):
            gaps.append('Hay lecturas sin hora de medición; la hora de confirmación no demuestra cuándo se midieron.')
        if any(r.measured_at and (datetime.now(timezone.utc)-datetime.fromisoformat(r.measured_at)).total_seconds()>86400 for r in records[:1]):
            gaps.append('La última lectura confirmada se midió hace más de 24 horas; no describe necesariamente el estado actual.')
        if any(r.symptoms.strip() for r in records):
            observations.append('Hay síntomas o contexto declarados en mediciones previas. Se conservan en la cronología para revisión médica.')
    else:
        gaps.append('Todavía no hay mediciones confirmadas para este alias y tipo de datos.')
        recommend('first','Incorpora la primera lectura','Fotografía la pantalla del instrumento, revisa etiquetas, valores y unidades y confirma el alias antes de guardarla.',
                  'El asistente solo utiliza lecturas que una persona ha revisado.',['nasa-research'])
    if 'spo2' in codes:
        recommend('oxygen','Revisa la calidad de SpO₂','Sigue el manual del pulsioxímetro y registra cómo te sientes. Si la lectura o los síntomas preocupan, consulta al responsable médico; no te guíes solo por el porcentaje.',
                  'El instrumento puede tener errores por condiciones de uso y características de la persona.',['fda-oximeter','nasa-risks'])
    if {'systolic','diastolic','pulse'} & set(codes):
        recommend('circulation','Añade contexto cardiovascular','Anota si estabas en reposo o después de actividad, el instrumento y los síntomas; comparte los cambios con el responsable médico.',
                  'NASA estudia adaptaciones cardiovasculares al vuelo espacial; una lectura por sí sola no identifica su causa.',['nasa-risks'])
    if 'glucose' in codes:
        recommend('glucose','Documenta el contexto de glucosa','Añade cuándo comiste y cualquier indicación médica previa. Usa los objetivos individuales del plan médico de misión.',
                  'Sin contexto y objetivos individuales no se puede interpretar una cifra como diagnóstico.',['csa-science'])
    if 'temperature' in codes:
        recommend('temperature','Identifica cómo mediste la temperatura','Registra el lugar y tipo de medición y los síntomas. Una pantalla no distingue temperatura cutánea de temperatura central.',
                  'Las lecturas de distintos métodos no deben tratarse como equivalentes.',['nasa-research'])
    if any(r.device_type=='smartwatch' for r in records):
        gaps.append('El reloj aporta datos de bienestar: modelo, precisión y aptitud clínica no están verificados. Confirma lecturas preocupantes con el equipo autorizado por la misión.')
    if not context:
        gaps.append('Falta el contexto de misión, descanso, estado de ánimo y antecedentes declarados.')
    else:
        observations.append(f'Entorno declarado: {ENVIRONMENTS[context.environment]}. La fecha y hora de la declaración se muestran en el contexto y la cronología.')
        if context.sleep_hours is not None:
            observations.append(f'Sueño declarado: {context.sleep_hours:g} horas. Es un autorreporte; no prueba un trastorno del sueño.')
            recommend('rest','Contrasta el descanso con tu plan de misión','Registraste '+f'{context.sleep_hours:g} horas. Compara este descanso con tu horario previsto y documenta somnolencia o dificultades para dormir.',
                      'Los horarios y el sueño forman parte del seguimiento de salud y rendimiento.',['nasa-risks','nasa-research'])
        if context.sleep_hours is None or context.mood=='unknown':
            gaps.append('Completa sueño y estado de ánimo para contextualizar el seguimiento.')
        if context.mood in {'strained','low'}:
            recommend('wellbeing','Comparte cómo te estás sintiendo','Registra descanso y estado de ánimo y conversa con el apoyo médico o psicológico de la misión si el malestar persiste.',
                      'Aislamiento y alteraciones del sueño forman parte de los riesgos estudiados por NASA.',['nasa-hazards','nasa-risks'])
        if context.medical_notes.strip():
            observations.append('Hay antecedentes o tratamientos declarados; el asistente no verifica diagnósticos ni modifica pautas médicas.')
        if context.symptoms.strip():
            recommend('symptoms','Comunica los síntomas declarados','Comparte el contexto y la evolución con el responsable médico. El texto libre se conserva, pero este motor no lo interpreta clínicamente.',
                      'Los síntomas pueden requerir evaluación aunque las lecturas parezcan habituales.',['medline-emergency'])
        if context.environment in {'moon','mars','spacecraft'}:
            recommend('autonomy','Prepara la consulta con Tierra','Reúne las lecturas, sus horas, síntomas y antecedentes para el responsable médico. Sigue el plan de comunicación de misión ante demoras.',
                      'La distancia puede limitar la asistencia inmediata; organizar la evidencia facilita la evaluación.',['nasa-hazards','csa-science'])
        if context.environment in {'station','spacecraft'}:
            recommend('habitat','Añade las condiciones del hábitat','Si hay síntomas, registra las condiciones y alertas del hábitat disponibles para la tripulación. No ajustes los sistemas de soporte vital a partir de esta web.',
                      'Los entornos cerrados requieren vigilancia propia; los signos vitales no sustituyen los sensores ambientales.',['nasa-hazards'])
    recommend('routine','Completa el seguimiento de bienestar','Registra descanso, actividad y estado de ánimo junto con las mediciones previstas por tu misión.',
              'HRP investiga medidas físicas y psicológicas; CSA destaca la preparación médica para misiones lejanas.',['nasa-research','nasa-hazards','csa-science'])
    recommend('radiation','La exposición requiere un detector dedicado','Si la misión dispone de dosimetría, consulta sus registros y el protocolo de protección radiológica con la tripulación.',
              'CSA desarrolla CANS para medir neutrones; ni la cámara, ni SpO₂ ni el pulso miden esa exposición.',['csa-radiation'])
    gaps.append('Estos instrumentos no determinan densidad ósea, estado inmunitario ni exposición a radiación.')
    red_flags = context.red_flags if context else []
    urgent = bool(red_flags)
    if urgent:
        recommend('urgent','Solicita ayuda médica ahora','Activa el protocolo de emergencia de la misión y avisa al responsable médico. No esperes otra captura ni una comparación del historial.',
                  'Has marcado señales de alarma: '+', '.join(RED_FLAGS[flag] for flag in red_flags)+'.',
                  ['medline-emergency'],'urgent')
        recommendations.sort(key=lambda item:item['priority']!='urgent')
    changes = [f"{m['label']}: {m['delta']:+g} {m['unit']}" for m in metrics if m['delta'] is not None]
    answers = {
        'overview':f'Reuní {len(records)} '+('registro confirmado' if len(records)==1 else 'registros confirmados')+f' para {subject_alias}. A continuación se muestran la evidencia disponible y los siguientes pasos.',
        'changes':('Entre las últimas confirmaciones comparables: '+ '; '.join(changes)+'. ' if changes else 'Todavía faltan confirmaciones comparables. ')+'Un aumento o descenso no equivale a un diagnóstico; revisa tiempos, técnica y contexto.',
        'next':'Para completar tu seguimiento: '+gaps[0]+' Sigue las mediciones previstas en tu plan de misión; las recomendaciones explican su propósito.',
        'mission':('Entorno declarado: '+ENVIRONMENTS[context.environment]+'. ' if context else 'Aún no has declarado el entorno de misión. ')+'Los cinco peligros espaciales orientan qué vigilar; no explican por sí solos los síntomas.',
        'radiation':'La radiación necesita datos de un detector especializado. Los signos vitales de un reloj, tensiómetro u oxímetro no permiten calcular tu dosis.',
    }
    timeline = [{'kind':'measurement','id':r.id,'created_at':r.created_at,'measured_at':r.measured_at,
                 'title':DEVICES[r.device_type]['label'],'readings':r.readings,'notes':r.symptoms} for r in records]
    timeline += [{'kind':'context','id':c.id,'created_at':c.created_at,'title':'Contexto y antecedentes declarados',
                  'notes':c.symptoms,'medical_notes':c.medical_notes,'sleep_hours':c.sleep_hours,'mood':c.mood,
                  'environment':ENVIRONMENTS[c.environment],'red_flags':c.red_flags} for c in contexts]
    timeline.sort(key=lambda item:item['created_at'], reverse=True)
    return {'version':'follow-up-0.3','subject_alias':subject_alias,'is_demo':is_demo,
            'status':'urgent' if urgent else 'collecting' if not records else 'review',
            'status_label':'Señales de alarma declaradas' if urgent else 'Recopilando evidencia' if not records else 'Seguimiento para revisión',
            'answer':('Hay señales de alarma declaradas. Solicita ayuda médica ahora. ' if urgent else '')+answers[intent],
            'record_count':len(records),'context':context_data(context),'metrics':metrics,'observations':observations,
            'recommendations':recommendations,'missing_data':gaps,'timeline':timeline[:50],
            'sources':SOURCES+SUPPORTING_SOURCES,'diagnosis':None,'treatment':None,
            'limitation':'Orientación por reglas y fuentes, sin diagnóstico ni prescripción. El texto libre no se interpreta clínicamente. La evaluación corresponde al responsable médico de la misión.'}
