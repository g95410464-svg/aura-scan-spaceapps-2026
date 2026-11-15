FIELDS = {
    'systolic': {'label': 'Presión sistólica', 'units': ['mmHg']},
    'diastolic': {'label': 'Presión diastólica', 'units': ['mmHg']},
    'pulse': {'label': 'Pulso', 'units': ['lpm']},
    'spo2': {'label': 'Saturación SpO2', 'units': ['%']},
    'temperature': {'label': 'Temperatura', 'units': ['°C', '°F']},
    'glucose': {'label': 'Glucosa', 'units': ['mg/dL', 'mmol/L']},
}

DEVICES = {
    'blood_pressure': {'label': 'Tensiómetro', 'fields': ['systolic', 'diastolic', 'pulse'], 'required': ['systolic', 'diastolic']},
    'oximeter': {'label': 'Pulsioxímetro', 'fields': ['spo2', 'pulse'], 'required': ['spo2']},
    'thermometer': {'label': 'Termómetro', 'fields': ['temperature'], 'required': ['temperature']},
    'glucometer': {'label': 'Glucómetro', 'fields': ['glucose'], 'required': ['glucose']},
    'smartwatch': {'label': 'Reloj inteligente (experimental)', 'fields': ['pulse', 'spo2'], 'required': ['pulse']},
}


def catalog():
    return [{'id': k, **v, 'model_status': 'unknown', 'validation': 'experimental',
             'indicators': [{'code': f, **FIELDS[f]} for f in v['fields']]} for k, v in DEVICES.items()]
