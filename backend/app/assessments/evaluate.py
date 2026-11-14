from backend.app.knowledge.sources import SOURCES


def evaluate(readings, symptoms, measured_at, previous):
    findings=[]
    follow_up=['Verifica la técnica de uso y el modo actual/memoria en el manual del instrumento.']
    if not measured_at:
        findings.append('La hora de medición no está documentada; solo se conoce cuándo se capturó y confirmó.')
    if symptoms.strip():
        findings.append('Se adjuntaron síntomas declarados para la revisión del responsable médico.')
    else:
        findings.append('No se añadieron síntomas; esto no confirma su ausencia.')
    by_code={r['code']:r for r in readings}
    if {'systolic','diastolic'}.issubset(by_code) and by_code['systolic']['value']<=by_code['diastolic']['value']:
        findings.append('La relación entre presión sistólica y diastólica requiere revisar etiquetas, transcripción y medición.')
    trends=[]
    if previous:
        for reading in readings:
            old=next((r for r in previous.readings if r['code']==reading['code'] and r['unit']==reading['unit']),None)
            if old:
                trends.append({'code':reading['code'],'delta':round(reading['value']-old['value'],3),
                               'unit':reading['unit'],'previous_id':previous.id,'previous_confirmed_at':previous.created_at})
        findings.append('Las diferencias se calculan entre registros confirmados; no explican su causa ni su importancia clínica.')
    else:
        findings.append('No hay un registro anterior comparable para este alias y categoría.')
    follow_up.append('Conserva la lectura y el contexto para revisión del responsable médico de la misión.')
    return {'version':'traceability-0.1','status':'informational', 'findings':findings,'next_steps':follow_up,
            'trends':trends,'diagnosis':None,'treatment':None,
            'limitation':'Prototipo experimental de registro y apoyo informativo. No hay un motor diagnóstico ni tratamientos clínicos validados.',
            'sources':[s['id'] for s in SOURCES]}
