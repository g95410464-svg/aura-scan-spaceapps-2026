import secrets
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, select, delete, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from backend.app.core.settings import Settings
from backend.app.core.security import get_workspace, get_db, limit_attempts, digest
from backend.app.storage.models import Base, Workspace, BrowserSession, Capture, Measurement, AuditEvent
from backend.app.measurements.schemas import Confirmation
from backend.app.devices.catalog import catalog, DEVICES
from backend.app.vision.reader import sanitize_image, analyze_image, ImageRejected
from backend.app.vision.demo import demo_image
from backend.app.assessments.evaluate import evaluate
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
    app=FastAPI(title='AURA Scan',version='0.2.0',lifespan=lifespan,docs_url=None,redoc_url=None,
                description='Captura visual experimental de instrumentos. Sin diagnóstico clínico validado.')
    app.state.db_session=sessionmaker(engine,expire_on_commit=False)
    app.state.settings=config

    @app.middleware('http')
    async def protection(request,call_next):
        if request.method not in {'GET','HEAD','OPTIONS'}:
            origin=request.headers.get('origin')
            allowed={str(request.base_url).rstrip('/')}
            if config.public_origin:
                allowed.add(config.public_origin.rstrip('/'))
            if origin and origin not in allowed:
                return JSONResponse({'detail':'Origen no permitido.'},status_code=403)
        length=request.headers.get('content-length')
        try:
            if length and (int(length)<0 or int(length)>config.max_upload_bytes+512*1024):
                return JSONResponse({'detail':'El archivo excede el límite de 8 MB.'},status_code=413)
        except ValueError:
            return JSONResponse({'detail':'Tamaño de solicitud inválido.'},status_code=400)
        if request.url.path=='/api/captures' and request.method=='POST' and length is None:
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
        return {'status':'ok','version':'0.2.0','clinical_validation':False,'dataset_integrated':False}

    @app.get('/api/session')
    def browser_session(request: Request,response: Response,db=Depends(get_db)):
        """Create an anonymous browser workspace automatically, without accounts."""
        token=request.cookies.get('aura_browser','')
        current=db.get(BrowserSession,digest(token)) if token else None
        if current is not None and current.expires_at>int(time.time()):
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
