from backend.app.vision.reader import parse_tokens


def token(text,x,y=30):
    return {'text':text,'x':x,'y':y,'h':25,'confidence':.98,'box':[]}


def test_numbers_without_labels_are_not_assigned():
    result=parse_tokens([token('120',200),token('80',200,100),token('72',200,180)])
    assert result['fields']==[]
    assert result['device_type']=='unknown'


def test_label_geometry_not_list_order_determines_indicator():
    tokens=[token('80',300,120),token('DIA',40,120),token('mmHg',500,50),token('SYS',40),token('120',300)]
    result=parse_tokens(tokens)
    assert {f['code']:f['value'] for f in result['fields']}=={'systolic':120,'diastolic':80}
    assert result['device_model'] is None


def test_missing_pressure_unit_is_not_guessed():
    result=parse_tokens([token('SYS',40),token('120',300)])
    assert result['fields'][0]['unit'] is None
    assert any('unidad' in warning for warning in result['warnings'])


def test_value_from_another_row_does_not_match():
    assert parse_tokens([token('SYS',40),token('120',300,150)])['fields']==[]


def test_temperature_keeps_visible_decimal_and_unit():
    result=parse_tokens([token('36,7',50),token('°C',180)])
    assert result['fields'][0]['value']==36.7
    assert result['fields'][0]['unit']=='°C'


def test_glucose_unit_not_converted_or_assumed():
    result=parse_tokens([token('5.6',40),token('mmol/L',180)])
    assert result['fields'][0]['value']==5.6
    assert result['fields'][0]['unit']=='mmol/L'


def test_conflicting_category_requests_review():
    result=parse_tokens([token('SYS',40),token('120',300)],'thermometer')
    assert any('no coincide' in warning for warning in result['warnings'])


def test_memory_screen_is_flagged():
    result=parse_tokens([token('SYS',40),token('120',300),token('MEM',20,180)])
    assert any('memoria' in warning for warning in result['warnings'])


def test_combined_label_value_and_unit():
    result=parse_tokens([token('SYS120 mmHg',200)])
    assert result['fields'][0]['value']==120
    assert result['fields'][0]['unit']=='mmHg'


def test_oximeter_combined_field_keeps_percentage():
    result=parse_tokens([token('SpO2 98%',200)])
    assert result['device_type']=='oximeter'
    assert result['fields'][0]['value']==98
    assert result['fields'][0]['unit']=='%'


def test_smartwatch_is_declared_not_inferred_from_appearance():
    result=parse_tokens([token('HR 72 bpm',200)],'smartwatch')
    assert result['device_type']=='smartwatch'
    assert result['fields'][0]['value']==72
    assert result['device_model'] is None
    assert any('no verifica' in warning for warning in result['warnings'])
