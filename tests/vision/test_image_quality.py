from io import BytesIO
from PIL import Image
from backend.app.vision.demo import demo_image
from backend.app.vision.reader import analyze_bytes, sanitize_image
from backend.app.vision.live import advance


def box(text,x,y,width=100,height=40):
    return ([[x,y],[x+width,y],[x+width,y+height],[x,y+height]],text,.99)


def test_high_resolution_preserves_more_pixels_and_parser_geometry():
    image=Image.open(BytesIO(demo_image())).resize((2000,1520))
    buf=BytesIO();image.save(buf,format='PNG')
    live=sanitize_image(buf.getvalue(),max_dimension=2048)
    assert Image.open(BytesIO(live)).size==(2000,1520)
    assert Image.open(BytesIO(sanitize_image(buf.getvalue()))).width==1600
    result=analyze_bytes(live,'blood_pressure')
    assert {r['code']:r['value'] for r in result['fields']}=={'systolic':120,'diastolic':80,'pulse':72}


def test_contrast_recovery_never_merges_contradictory_numbers(monkeypatch):
    outputs=[
        [box('SYS',100,150),box('120',450,150),box('mmHg',700,150)],
        [box('SYS',100,150),box('121',450,150),box('DIA',100,280),box('80',450,280),box('mmHg',700,150)],
    ]
    monkeypatch.setattr('backend.app.vision.reader._engine',lambda _: (outputs.pop(0),None))
    result=analyze_bytes(demo_image(),'blood_pressure')
    assert result['recognition']=='ambiguous'
    assert any('distintos' in warning for warning in result['warnings'])
    _,response,saved=advance({},result,100,True)
    assert not saved and response['status']=='searching'


def test_bright_unreadable_frame_gives_glare_guidance():
    result={'device_type':'unknown','recognition':'unresolved','fields':[],'tokens':[],
            'quality':{'sharpness':70,'brightness':240,'bright_fraction':.3}}
    _,response,saved=advance({},result,100,False)
    assert not saved and 'reflejo' in response['message']
