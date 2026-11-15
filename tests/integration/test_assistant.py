from fastapi.testclient import TestClient
from tests.conftest import open_workspace, confirmation


def snapshot(client, alias='ASTRO-01', demo=True, **extra):
    result=client.get('/api/assistant', params={'subject_alias':alias,'is_demo':demo,**extra})
    assert result.status_code==200, result.text
    return result.json()


def context(**overrides):
    return {'subject_alias':'ASTRO-01','is_demo':True,'environment':'station','sleep_hours':6.5,
            'mood':'strained','symptoms':'Cansancio declarado.','medical_notes':'Alergia declarada para pruebas.',
            'red_flags':[],**overrides}


def test_assistant_uses_only_confirmed_records_and_separates_demo(visitor_client,capture):
    assert snapshot(visitor_client)['record_count']==0
    visitor_client.post(f'/api/captures/{capture["id"]}/confirm',json=confirmation())
    data=snapshot(visitor_client)
    assert data['record_count']==1
    assert {m['code']:m['value'] for m in data['metrics']}=={'systolic':120,'diastolic':80,'pulse':72}
    assert data['diagnosis'] is None and data['treatment'] is None
    assert snapshot(visitor_client,demo=False)['record_count']==0
    assert snapshot(visitor_client,alias='OTHER')['record_count']==0
    assert len(data['sources'])==7
    assert all(r['source_ids'] for r in data['recommendations'])


def test_assistant_context_and_history_are_isolated(visitor_client,application,capture):
    visitor_client.post(f'/api/captures/{capture["id"]}/confirm',json=confirmation())
    response=visitor_client.post('/api/assistant/context',json=context())
    assert response.status_code==201
    own=snapshot(visitor_client)
    assert own['context']['sleep_hours']==6.5
    assert len(own['timeline'])==2
    assert any(r['id']=='wellbeing' for r in own['recommendations'])
    assert own['timeline'][0]['medical_notes']=='Alergia declarada para pruebas.'
    assert snapshot(visitor_client,demo=False)['context'] is None
    assert snapshot(visitor_client,alias='OTHER')['context'] is None
    with TestClient(application) as other:
        open_workspace(other)
        other_data=snapshot(other)
        assert other_data['context'] is None and other_data['timeline']==[]
        assert other.get('/api/assistant/subjects').json()['items']==[]


def test_changes_do_not_mix_units_or_instruments(visitor_client,capture):
    visitor_client.post(f'/api/captures/{capture["id"]}/confirm',json=confirmation())
    second=visitor_client.post('/api/captures/demo').json()
    new=confirmation();new['readings'][0]['value']=125
    visitor_client.post(f'/api/captures/{second["id"]}/confirm',json=new)
    data=snapshot(visitor_client,intent='changes')
    systolic=next(m for m in data['metrics'] if m['code']=='systolic')
    assert systolic['delta']==5
    assert systolic['comparison_basis']=='confirmation_order'
    assert len(systolic['series'])==2
    watch=visitor_client.post('/api/captures/demo').json()
    body=confirmation(device_type='smartwatch',readings=[{'code':'pulse','value':95,'unit':'lpm'}])
    assert visitor_client.post(f'/api/captures/{watch["id"]}/confirm',json=body).status_code==201
    pulse=next(m for m in snapshot(visitor_client)['metrics'] if m['code']=='pulse')
    assert pulse['value']==95 and pulse['delta'] is None
    assert pulse['device_type']=='smartwatch'
    for value,unit in [(36.7,'°C'),(98.6,'°F')]:
        photo=visitor_client.post('/api/captures/demo').json()
        body=confirmation(device_type='thermometer',readings=[{'code':'temperature','value':value,'unit':unit}])
        assert visitor_client.post(f'/api/captures/{photo["id"]}/confirm',json=body).status_code==201
    temperature=next(m for m in snapshot(visitor_client)['metrics'] if m['code']=='temperature')
    assert temperature['unit']=='°F' and temperature['delta'] is None


def test_declared_emergency_never_waits_for_more_measurements(visitor_client):
    assert visitor_client.post('/api/assistant/context',json=context(red_flags=['breathing'])).status_code==201
    data=snapshot(visitor_client,intent='radiation')
    assert data['status']=='urgent'
    assert data['recommendations'][0]['id']=='urgent'
    assert 'ahora' in data['answer']
    assert data['diagnosis'] is None
    assert visitor_client.post('/api/assistant/context',json=context(red_flags=[])).status_code==201
    assert snapshot(visitor_client)['status']!='urgent'
    assert len(snapshot(visitor_client)['timeline'])==2  # Earlier declaration is retained.


def test_context_validation_and_csrf(visitor_client):
    for body in [context(sleep_hours=25),context(red_flags=['invented']),context(subject_alias=' '),context(extra='forbidden')]:
        assert visitor_client.post('/api/assistant/context',json=body).status_code==422
    assert visitor_client.post('/api/assistant/context',json=context(),headers={'X-CSRF-Token':'wrong'}).status_code==403
    assert visitor_client.get('/api/assistant',params={'subject_alias':'x','intent':'diagnose'}).status_code==422


def test_radiation_answer_requests_real_dosimetry(visitor_client):
    data=snapshot(visitor_client,intent='radiation')
    assert 'detector especializado' in data['answer']
    recommendation=next(r for r in data['recommendations'] if r['id']=='radiation')
    assert recommendation['source_ids']==['csa-radiation']
    assert data['diagnosis'] is None
