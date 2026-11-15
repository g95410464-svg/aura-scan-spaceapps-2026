from copy import deepcopy
from backend.app.vision.live import advance


def detected(value=120,unit='mmHg',confidence=.98):
    return {'device_type':'blood_pressure','recognition':'visible_labels','tokens':[],
            'quality':{'sharpness':80,'brightness':150},
            'fields':[{'code':'systolic','value':value,'unit':unit,'confidence':confidence},
                      {'code':'diastolic','value':80,'unit':unit,'confidence':confidence}]}


def test_three_agreeing_frames_need_real_elapsed_time():
    state={}
    for now in [100,100.1,100.2]:
        state,response,save=advance(state,detected(),now,False)
        assert not save
    state,response,save=advance(state,detected(),104,False)
    assert save and response['status']=='recorded'


def test_repeated_screen_is_saved_once_and_changes_need_new_agreement():
    state={};saves=[]
    for now,value in [(100,120),(102,120),(104,120),(106,120),(108,125),(110,125),(112,125)]:
        state,response,save=advance(state,detected(value),now,False)
        if save:saves.append(value)
    assert saves==[120]  # Change was stable but is still in the 10-second cooldown.
    state,response,save=advance(state,detected(125),116,False)
    assert save
    state,response,save=advance(state,detected(125),118,False)
    assert not save and response['status']=='unchanged'


def test_uncertain_frames_and_memory_do_not_become_medical_records():
    for problem in ['unit','confidence','blur','memory','missing','unexpected']:
        state,_,_=advance({},detected(),100,False)
        result=deepcopy(detected())
        if problem=='unit':result['fields'][0]['unit']=None
        if problem=='confidence':result['fields'][0]['confidence']=.5
        if problem=='blur':result['quality']['sharpness']=2
        if problem=='memory':result['tokens']=[{'text':'MEMORY'}]
        if problem=='missing':result['fields']=result['fields'][:1]
        if problem=='unexpected':result['fields'].append({'code':'spo2','value':98,'unit':'%','confidence':.99})
        state,response,save=advance(state,result,102,False)
        assert response['status']=='searching' and not save
        state,response,save=advance(state,detected(),104,False)
        assert state['count']==1 and not save


def test_a_long_gap_resets_stability():
    state,_,_=advance({},detected(),100,False)
    state,_,_=advance(state,detected(),102,False)
    state,response,save=advance(state,detected(),130,False)
    assert state['count']==1 and not save


def test_small_pulse_fluctuations_keep_the_actual_latest_value_not_an_average():
    state={}
    for now,pulse in [(100,72),(102,73),(104,71)]:
        result={'device_type':'smartwatch','recognition':'visible_labels','tokens':[],
                'quality':{'sharpness':80,'brightness':150},
                'fields':[{'code':'pulse','value':pulse,'unit':'lpm','confidence':.99}]}
        state,response,save=advance(state,result,now,False)
    assert save and response['fields'][0]['value']==71
    result['fields'][0]['value']=73
    state,response,save=advance(state,result,106,False)
    assert not save and response['status']=='unchanged'
