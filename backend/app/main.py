import secrets
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Request, Response, Depends, HTTPException, UploadFile, File, Form, Query
from typing import Literal
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, select, delete, event, update
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from backend.app.core.settings import Settings
from backend.app.core.security import get_workspace, get_db, limit_attempts, digest, origin_key
from backend.app.storage.models import Base, Workspace, BrowserSession, Capture, Measurement, AuditEvent, HealthContext, LiveSession, LiveReading, SimulationRun, now_iso
from backend.app.measurements.schemas import Confirmation
from backend.app.devices.catalog import catalog, DEVICES
from backend.app.vision.reader import sanitize_image, analyze_image, analyze_bytes, ImageRejected
from backend.app.vision.live import LiveStart, advance, serialize_live, INTERVAL_MS, MIN_FRAMES
from backend.app.vision.demo import demo_image
from backend.app.assessments.evaluate import evaluate
from backend.app.assessments.assistant import build_assistant
from backend.app.assessments.schemas import ContextInput
from backend.app.assessments.simulation import SimulationRequest, SCENARIOS
from backend.app.knowledge.sources import SOURCES
from backend.app.reports.pdf import render_report


def create_app(settings: Settings | None = None):
    config=settings or Settings()
    config.prepare()
    engine=create_engine(config.database_url,connect_args={'check_same_thread':False} if config.database_url.startswith('sqlite') else {},pool_pre_ping=True)
    if config.database_url.startswith('sqlite'):
        @event.listens_for(engine,'connect')
        def foreign_keys(connection,_):
            connection.execute('PRAGMA foreign_keys=ON')
    @asynccontextmanager
    async def lifespan(app):
        Base.metadata.create_all(engine)
        yield
        engine.dispose()
    app=FastAPI(title='AURA Scan',version='0.5.0',lifespan=lifespan,docs_url=None,redoc_url=None,
                description='Captura visual experimental de instrumentos. Sin diagnóstico clínico validado.')
    app.state.db_session=sessionmaker(engine,expire_on_commit=False)
    app.state.settings=config

    @app.middleware('http')
    async def protection(request,call_next):
        if request.method not in {'GET','HEAD','OPTIONS'}:
            origin=request.headers.get('origin')
            allowed={origin_key(str(request.base_url))}
            if config.public_origin:
                allowed.add(origin_key(config.public_origin))
            if origin and (origin_key(origin) is None or origin_key(origin) not in allowed):
                return JSONResponse({'detail':'Origen no permitido.'},status_code=403)
        length=request.headers.get('content-length')
        try:
            if length and (int(length)<0 or int(length)>config.max_upload_bytes+512*1024):
                return JSONResponse({'detail':'El archivo excede el límite de 8 MB.'},status_code=413)
        except ValueError:
            return JSONResponse({'detail':'Tamaño de solicitud inválido.'},status_code=400)
        if (request.url.path=='/api/captures' or request.url.path.endswith('/frames')) and request.method=='POST' and length is None:
            return JSONResponse({'detail':'La carga requiere Content-Length.'},status_code=411)
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='same-origin'
        response.headers['Permissions-Policy']='camera=(self), microphone=(), geolocation=()'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control']='no-store'
        return response

    @app.get('/api/health')
    def health():
        return {'status':'ok','version':'0.5.0','clinical_validation':False,'dataset_integrated':False}

    @app.get('/api/session')
    def browser_session(request: Request,response: Response,db=Depends(get_db)):
        """Create an anonymous browser workspace automatically, without accounts."""
        token=request.cookies.get('aura_browser','')
        current=db.get(BrowserSession,digest(token)) if token else None
        if current is not None and current.expires_at>int(time.time()):
            # Renew active browser spaces without creating accounts or moving evidence.
            lifetime=config.session_hours*3600
            if current.expires_at-int(time.time())<lifetime//2:
                current.expires_at=int(time.time())+lifetime
                db.commit()
                response.set_cookie('aura_browser',token,httponly=True,secure=config.secure_cookies,samesite='lax',max_age=lifetime,path='/')
            return {'csrf':current.csrf,'expires_at':current.expires_at}
        limit_attempts(request,'browser_session',60,3600)
        token=secrets.token_urlsafe(32)
        csrf=secrets.token_hex(32)
        db.execute(delete(BrowserSession).where(BrowserSession.expires_at<=int(time.time())))
        workspace=Workspace()
        db.add(workspace);db.flush()
        expires_at=int(time.time())+config.session_hours*3600
        db.add(BrowserSession(token_hash=digest(token),workspace_id=workspace.id,csrf=csrf,expires_at=expires_at))
        db.commit()
        response.set_cookie('aura_browser',token,httponly=True,secure=config.secure_cookies,samesite='lax',max_age=config.session_hours*3600,path='/')
        response.delete_cookie('aura_session',path='/')
        return {'csrf':csrf,'expires_at':expires_at}

    @app.get('/api/knowledge')
    def knowledge():
        return {'sources':SOURCES,'protocols':[], 'clinical_review':'pending'}

    @app.get('/api/devices')
    def devices():
        return {'devices':catalog(),'exact_models':[], 'dataset_status':'not_integrated'}

    def owner_capture(capture_id,workspace,db):
        item=db.scalar(select(Capture).where(Capture.id==capture_id,Capture.owner_id==workspace.id))
        if not item: raise HTTPException(404,'Captura no encontrada.')
        return item

    def store_capture(content,device_type,is_demo,workspace,db):
        if device_type not in {'auto',*DEVICES}:
            raise HTTPException(422,'Categoría no admitida.')
        try:
            normalized=sanitize_image(content)
        except ImageRejected as exc:
            raise HTTPException(422,str(exc))
        capture=Capture(owner_id=workspace.id,device_type=device_type,result={},is_demo=is_demo)
        db.add(capture);db.flush()
        path=config.storage_dir/f'{capture.id}.png'
        path.write_bytes(normalized)
        try:
            result=analyze_image(path,device_type)
        except Exception:
            # Do not leak engine paths, contents, or stack traces to the public API.
            result={'device_type':device_type if device_type!='auto' else 'unknown','device_model':None,
                    'fields':[],'tokens':[],'recognition':'unavailable','engine':'RapidOCR / ONNX',
                    'warnings':['El análisis no está disponible. Puedes repetirlo más tarde o registrar una transcripción manual confirmada.']}
        text=' '.join(t.get('text','') for t in result.get('tokens',[])).upper()
        capture.is_demo=is_demo or 'FICTICIO' in text or 'DEMO' in text
        capture.result=result
        capture.device_type=result['device_type']
        db.commit()
        return {'id':capture.id,'created_at':capture.created_at,'is_demo':capture.is_demo,'status':capture.status,
                'image_url':f'/api/captures/{capture.id}/image',**result}

    @app.post('/api/captures',status_code=201)
    def upload(request: Request,file: UploadFile=File(...),device_type: str=Form('auto'),is_demo: bool=Form(False),workspace=Depends(get_workspace),db=Depends(get_db)):
        limit_attempts(request,'capture',40,3600)
        content=file.file.read(config.max_upload_bytes+1)
        if len(content)>config.max_upload_bytes: raise HTTPException(413,'La imagen excede el límite de 8 MB.')
        return store_capture(content,device_type,is_demo,workspace,db)

    @app.post('/api/captures/demo',status_code=201)
    def demo(request: Request,workspace=Depends(get_workspace),db=Depends(get_db)):
        limit_attempts(request,'capture',40,3600)
        return store_capture(demo_image(),'auto',True,workspace,db)

    @app.get('/api/captures/{capture_id}/image')
    def capture_image(capture_id: str,workspace=Depends(get_workspace),db=Depends(get_db)):
        item=owner_capture(capture_id,workspace,db)
        return FileResponse(config.storage_dir/f'{item.id}.png',media_type='image/png')

    @app.get('/api/captures/{capture_id}')
    def capture_detail(capture_id: str,workspace=Depends(get_workspace),db=Depends(get_db)):
        item=owner_capture(capture_id,workspace,db)
        automatic=db.scalar(select(LiveReading).where(LiveReading.capture_id==item.id,LiveReading.owner_id==workspace.id))
        return {'id':item.id,'created_at':item.created_at,'is_demo':item.is_demo,'status':item.status,
                'image_url':f'/api/captures/{item.id}/image','subject_alias':automatic.subject_alias if automatic else None,**item.result}

    def own_live(session_id,workspace,db):
        item=db.scalar(select(LiveSession).where(LiveSession.id==session_id,LiveSession.owner_id==workspace.id))
        if not item: raise HTTPException(404,'Sesión de lectura no encontrada.')
        return item

    @app.post('/api/live/sessions',status_code=201)
    def start_live(data: LiveStart,request: Request,workspace=Depends(get_workspace),db=Depends(get_db)):
        limit_attempts(request,'live_start',30,3600)
        item=LiveSession(owner_id=workspace.id,subject_alias=data.subject_alias,device_type=data.device_type,
                         is_demo=data.is_demo,expires_at=int(time.time())+7200)
        db.add(item);db.commit()
        return {'id':item.id,'interval_ms':INTERVAL_MS,'stable_frames':MIN_FRAMES,'expires_at':item.expires_at}

    @app.get('/api/live/demo-screen')
    def live_demo_screen(workspace=Depends(get_workspace)):
        return Response(demo_image(),media_type='image/png')

    @app.post('/api/live/{session_id}/stop')
    def stop_live(session_id: str,workspace=Depends(get_workspace),db=Depends(get_db)):
        item=own_live(session_id,workspace,db)
        if not item.stopped_at:
            item.stopped_at=now_iso();db.commit()
        return {'status':'stopped'}

    @app.post('/api/live/{session_id}/frames')
    def live_frame(session_id: str,request: Request,file: UploadFile=File(...),sequence: int=Form(...,ge=1,le=1000000),
                   workspace=Depends(get_workspace),db=Depends(get_db)):
        item=own_live(session_id,workspace,db)
        if item.stopped_at or item.expires_at<=int(time.time()):
            raise HTTPException(409,'La lectura en vivo terminó. Inicia una nueva sesión.')
        if sequence==item.sequence and item.state.get('response'):
            return item.state['response']
        if sequence<item.sequence: raise HTTPException(409,'Fotograma anterior al último procesado.')
        if item.state.get('received_at',0)>time.time()-1:
            raise HTTPException(429,'Espera antes del siguiente fotograma.')
        limit_attempts(request,'live_frame',60,60)
        content=file.file.read(2*1024*1024+1)
        if len(content)>2*1024*1024: raise HTTPException(413,'El fotograma excede 2 MB.')
        try:
            normalized=sanitize_image(content,max_dimension=2048)
        except ImageRejected as exc:
            raise HTTPException(422,str(exc))
        try:
            result=analyze_bytes(normalized,item.device_type)
        except Exception:
            raise HTTPException(503,'No se pudo analizar el fotograma. La lectura se ha pausado; vuelve a iniciarla.')
        detected_demo=item.is_demo or any('FICTICIO' in t['text'].upper() or 'DEMO' in t['text'].upper() for t in result.get('tokens',[]))
        now=time.time()
        state,response,should_save=advance(item.state,result,now,detected_demo)
        response.update(sequence=sequence,recording=None,is_demo=detected_demo)
        state['received_at']=now
        expected=item.sequence
        # Conditional update makes retries and simultaneous requests safe across workers.
        claimed=db.execute(update(LiveSession).where(LiveSession.id==item.id,LiveSession.sequence==expected,
                            LiveSession.stopped_at.is_(None)).values(sequence=sequence,state=state),execution_options={'synchronize_session':False})
        if claimed.rowcount!=1:
            db.rollback();raise HTTPException(409,'Otro fotograma ya fue procesado; continúa con el siguiente.')
        path=None
        try:
            if should_save:
                readings=[{'code':r['code'],'value':r['value'],'unit':r['unit'],'provenance':'live_ocr_unreviewed'} for r in response['fields']]
                capture=Capture(owner_id=workspace.id,device_type=result['device_type'],result={**result,'origin':'live_camera'},is_demo=detected_demo)
                db.add(capture);db.flush()
                path=config.storage_dir/f'{capture.id}.png'
                path.write_bytes(normalized)
                observation=LiveReading(owner_id=workspace.id,session_id=item.id,capture_id=capture.id,sequence=sequence,
                                        subject_alias=item.subject_alias,device_type=result['device_type'],is_demo=detected_demo,readings=readings)
                db.add(observation)
                db.add(AuditEvent(owner_id=workspace.id,capture_id=capture.id,action='live_auto_saved',detail={
                    'session_id':item.id,'sequence':sequence,'agreement_frames':response['count'],'human_reviewed':False,'readings':readings}))
                db.flush()
                response['recording']=serialize_live(observation)
            state['response']=response
            db.execute(update(LiveSession).where(LiveSession.id==item.id).values(state=state),execution_options={'synchronize_session':False})
            db.commit()
        except Exception:
            db.rollback()
            if path and path.exists(): path.unlink()
            raise
        return response

    @app.get('/api/live/readings')
    def live_readings(workspace=Depends(get_workspace),db=Depends(get_db)):
        rows=db.scalars(select(LiveReading).where(LiveReading.owner_id==workspace.id,LiveReading.status=='pending')
                        .order_by(LiveReading.created_at.desc()).limit(100)).all()
        return {'items':[serialize_live(row) for row in rows]}

    @app.post('/api/captures/{capture_id}/confirm',status_code=201)
    def confirm(capture_id: str,data: Confirmation,workspace=Depends(get_workspace),db=Depends(get_db)):
        capture=owner_capture(capture_id,workspace,db)
        if capture.status!='pending':raise HTTPException(409,'Esta captura ya fue confirmada.')
        candidates={r['code']:r for r in capture.result.get('fields',[])}
        readings=[]
        for reading in data.readings:
            r=reading.model_dump(); old=candidates.get(r['code'])
            r['provenance']='ocr_confirmed' if old and old['value']==r['value'] and old['unit']==r['unit'] else 'user_reviewed'
            readings.append(r)
        previous=db.scalar(select(Measurement).where(Measurement.owner_id==workspace.id,Measurement.subject_alias==data.subject_alias,
                           Measurement.device_type==data.device_type,Measurement.is_demo==capture.is_demo).order_by(Measurement.created_at.desc()).limit(1))
        measured_at=data.measured_at.isoformat() if data.measured_at else None
        assessment=evaluate(readings,data.symptoms,measured_at,previous)
        record=Measurement(owner_id=workspace.id,capture_id=capture.id,subject_alias=data.subject_alias,
                           device_type=data.device_type,is_demo=capture.is_demo,measured_at=measured_at,
                           readings=readings,symptoms=data.symptoms,assessment=assessment)
        db.add(record)
        capture.status='confirmed'
        automatic=db.scalar(select(LiveReading).where(LiveReading.capture_id==capture.id,LiveReading.owner_id==workspace.id))
        if automatic: automatic.status='confirmed'
        db.add(AuditEvent(owner_id=workspace.id,capture_id=capture.id,action='confirmed',
                          detail={'candidates':capture.result.get('fields',[]),'confirmed':readings,'device_type':data.device_type}))
        try:
            db.commit()
        except IntegrityError:
            db.rollback();raise HTTPException(409,'La captura ya fue confirmada en otra solicitud.')
        return serialize(record)

    def serialize(record):
        return {key:getattr(record,key) for key in ['id','capture_id','created_at','measured_at','subject_alias','device_type','is_demo','readings','symptoms','assessment']}

    @app.get('/api/measurements')
    def history(workspace=Depends(get_workspace),db=Depends(get_db)):
        records=db.scalars(select(Measurement).where(Measurement.owner_id==workspace.id).order_by(Measurement.created_at.desc()).limit(100)).all()
        return {'items':[serialize(r) for r in records]}

    @app.post('/api/simulation/run')
    def run_simulation(data: SimulationRequest,request: Request,workspace=Depends(get_workspace),db=Depends(get_db)):
        existing=db.scalar(select(SimulationRun).where(SimulationRun.owner_id==workspace.id,SimulationRun.run_key==str(data.run_key)))
        if existing:return existing.result
        limit_attempts(request,'simulation',20,3600)
        run=SimulationRun(owner_id=workspace.id,run_key=str(data.run_key))
        db.add(run)
        try: db.flush()
        except IntegrityError:
            db.rollback()
            existing=db.scalar(select(SimulationRun).where(SimulationRun.owner_id==workspace.id,SimulationRun.run_key==str(data.run_key)))
            if existing:return existing.result
            raise HTTPException(409,'La simulación ya se está preparando. Vuelve a intentar.')
        alias=f'DEMO-AURA-{run.id[:6].upper()}'
        records=[];screens=[];paths=[]
        try:
            for scenario in SCENARIOS:
                image=demo_image(scenario['device_type'],scenario['values'])
                recognized=analyze_bytes(image,scenario['device_type'])
                actual={f['code']:f['value'] for f in recognized['fields'] if f.get('unit') is not None}
                if actual!=scenario['expected'] or recognized['recognition']!='visible_labels':
                    raise HTTPException(503,'La pantalla de prueba no se pudo leer con consistencia. Vuelve a intentar la simulación.')
                capture=Capture(owner_id=workspace.id,device_type=scenario['device_type'],is_demo=True,status='simulated',result={**recognized,'origin':'guided_simulation'})
                db.add(capture);db.flush()
                path=config.storage_dir/f'{capture.id}.png';paths.append(path);path.write_bytes(image)
                readings=[{'code':f['code'],'value':f['value'],'unit':f['unit'],'provenance':'simulation_scripted'} for f in recognized['fields']]
                measured_at=(datetime.now(timezone.utc)-timedelta(minutes=scenario['minutes_ago'])).isoformat()
                previous=next((r for r in reversed(records) if r.device_type==scenario['device_type']),None)
                symptoms='FICTITIOUS DEMO: exercise simulation and tiredness. Values and times are scripted, not patient data.'
                assessment=evaluate(readings,symptoms,measured_at,previous)
                assessment['findings'].insert(0,'Registro guionado de simulación con OCR real sobre pantalla sintética; sin revisión clínica ni medición física.')
                record=Measurement(owner_id=workspace.id,capture_id=capture.id,subject_alias=alias,device_type=scenario['device_type'],is_demo=True,
                                   measured_at=measured_at,readings=readings,symptoms=symptoms,assessment=assessment)
                db.add(record);db.flush();records.append(record)
                db.add(AuditEvent(owner_id=workspace.id,capture_id=capture.id,action='simulation_created',detail={'run_id':run.id,'human_reviewed':False,'is_demo':True}))
                screens.append({'title':scenario['title'],'image_url':f'/api/captures/{capture.id}/image','readings':readings,'record_id':record.id})
            context=HealthContext(owner_id=workspace.id,subject_alias=alias,is_demo=True,environment='station',sleep_hours=6,mood='strained',
                                  symptoms='Fictional training scenario: tiredness after simulated activity.',medical_notes='FICTITIOUS SCENARIO. No real diagnosis or treatment.',red_flags=[])
            db.add(context)
            run.result={'id':run.id,'subject_alias':alias,'is_demo':True,'screens':screens,'records':[serialize(r) for r in records],
                        'report_id':records[1].id,'notice':'Escenario guionado con OCR real de pantallas sintéticas. No representa pacientes ni valida precisión clínica.'}
            db.commit()
            return run.result
        except Exception:
            db.rollback()
            for path in paths:
                if path.exists():path.unlink()
            raise

    @app.get('/api/assistant/subjects')
    def subjects(workspace=Depends(get_workspace),db=Depends(get_db)):
        rows = db.execute(select(Measurement.subject_alias, Measurement.is_demo).where(Measurement.owner_id==workspace.id).distinct()).all()
        rows += db.execute(select(HealthContext.subject_alias, HealthContext.is_demo).where(HealthContext.owner_id==workspace.id).distinct()).all()
        rows += db.execute(select(LiveReading.subject_alias, LiveReading.is_demo).where(LiveReading.owner_id==workspace.id).distinct()).all()
        return {'items':[{'subject_alias':alias,'is_demo':demo} for alias,demo in sorted(set(rows))]}

    @app.get('/api/assistant')
    def assistant(subject_alias: str=Query(min_length=1,max_length=80),is_demo: bool=False,
                  intent: Literal['overview','changes','next','mission','radiation']='overview',
                  workspace=Depends(get_workspace),db=Depends(get_db)):
        alias=subject_alias.strip()
        if not alias: raise HTTPException(422,'Introduce el alias del astronauta.')
        records=db.scalars(select(Measurement).where(Measurement.owner_id==workspace.id,Measurement.subject_alias==alias,
                           Measurement.is_demo==is_demo).order_by(Measurement.created_at.desc()).limit(500)).all()
        contexts=db.scalars(select(HealthContext).where(HealthContext.owner_id==workspace.id,HealthContext.subject_alias==alias,
                            HealthContext.is_demo==is_demo).order_by(HealthContext.created_at.desc()).limit(50)).all()
        data=build_assistant(records,contexts,alias,is_demo,intent)
        automatic=db.scalars(select(LiveReading).where(LiveReading.owner_id==workspace.id,LiveReading.subject_alias==alias,
                            LiveReading.is_demo==is_demo,LiveReading.status=='pending').order_by(LiveReading.created_at.desc()).limit(100)).all()
        data['automatic_readings']=[serialize_live(row) for row in automatic]
        if automatic:
            data['observations'].append(f'Hay {len(automatic)} lecturas automáticas guardadas sin revisión; se muestran por separado y no alimentan las comparaciones confirmadas.')
            data['recommendations'].insert(0,{'id':'review_live','title':'Revisa las lecturas automáticas',
                'action':'Contrasta las lecturas guardadas con su evidencia antes de validarlas para el seguimiento médico.',
                'reason':'La coincidencia de OCR entre fotogramas no demuestra precisión del instrumento ni de la medición.',
                'source_ids':['nasa-research'],'priority':'follow_up'})
            data['recommendations'].sort(key=lambda recommendation:recommendation['priority']!='urgent')
        return data

    @app.post('/api/assistant/context',status_code=201)
    def save_context(data: ContextInput,request: Request,workspace=Depends(get_workspace),db=Depends(get_db)):
        limit_attempts(request,'context',60,3600)
        item=HealthContext(owner_id=workspace.id,**data.model_dump())
        db.add(item);db.commit()
        return {'id':item.id,'created_at':item.created_at}

    @app.get('/api/measurements/{record_id}/report.pdf')
    def report(record_id: str,workspace=Depends(get_workspace),db=Depends(get_db)):
        record=db.scalar(select(Measurement).where(Measurement.id==record_id,Measurement.owner_id==workspace.id))
        if not record:raise HTTPException(404,'Informe no encontrado.')
        capture=db.get(Capture,record.capture_id)
        return Response(render_report(record,capture),media_type='application/pdf',
                        headers={'Content-Disposition':f'attachment; filename="aura-informe-{record.id[:8]}.pdf"'})

    if (config.frontend_dir/'assets').exists():
        app.mount('/assets',StaticFiles(directory=config.frontend_dir/'assets'),name='assets')

    @app.get('/{path:path}',include_in_schema=False)
    def frontend(path: str):
        if path=='api' or path.startswith('api/'):
            raise HTTPException(404,'Ruta de API no encontrada.')
        if not (config.frontend_dir/'index.html').exists():
            return JSONResponse({'detail':'Frontend pendiente de compilar. Ejecuta npm run build en frontend.'},status_code=503)
        return FileResponse(config.frontend_dir/'index.html')
    return app


app=create_app()
