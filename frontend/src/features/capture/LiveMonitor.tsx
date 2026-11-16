import { useCallback, useEffect, useRef, useState } from 'react';
import { Activity, ArrowRight, Camera, Check, ClipboardList, Info, LoaderCircle, MessageCircle, Pause, Play, Radio, ScanLine, ShieldCheck } from 'lucide-react';
import { request } from '../../services/api';
import type { Device, LiveReading, LiveFrame } from '../../services/api';

type Subject = { subject_alias:string; is_demo:boolean };
type StartResult = { id:string; interval_ms:number; stable_frames:number; expires_at:number };
const date = (s:string) => new Date(s).toLocaleTimeString('es-GT',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
const fieldNames: Record<string,string> = { systolic:'Presión sistólica',diastolic:'Presión diastólica',pulse:'Pulso',spo2:'Saturación SpO₂',temperature:'Temperatura',glucose:'Glucosa' };

export function LiveReadings({ items, onReview, onFollowUp }: { items:LiveReading[]; onReview:(item:LiveReading)=>void; onFollowUp?:(s:Subject)=>void }) {
  return <div className="live-observations">{items.map(item=><article className="live-observation" key={item.id}><div className="live-observation-title"><span><Radio size={13}/> {item.subject_alias}</span><small>{date(item.created_at)}</small></div><div className="live-observation-values">{item.readings.map(r=><span key={r.code}><small>{fieldNames[r.code]??r.code}</small><b>{r.value} {r.unit}</b></span>)}</div><p>Guardada automáticamente · Sin revisar{item.is_demo?' · Ficticia':''}</p><div><button className="text-button" onClick={()=>onReview(item)}>Revisar evidencia <ArrowRight size={13}/></button>{onFollowUp&&<button className="text-button" onClick={()=>onFollowUp(item)}><MessageCircle size={13}/> Asistente</button>}</div></article>)}</div>;
}

export function LiveMonitor({ devices, pending, onSaved, onReview, onFollowUp }: { devices:Device[]; pending:LiveReading[]; onSaved:(r:LiveReading)=>void; onReview:(r:LiveReading)=>void; onFollowUp:(s:Subject)=>void }) {
  const [subject,setSubject] = useState('');
  const [category,setCategory] = useState('auto');
  const [declaredDemo,setDeclaredDemo] = useState(false);
  const [mode,setMode] = useState<'idle'|'camera'|'demo'>('idle');
  const [starting,setStarting] = useState(false);
  const [analyzing,setAnalyzing] = useState(false);
  const [error,setError] = useState('');
  const [notice,setNotice] = useState('');
  const [frame,setFrame] = useState<LiveFrame | null>(null);
  const [saved,setSaved] = useState<LiveReading[]>([]);
  const [zoom,setZoom] = useState(1);
  const zoomRef=useRef(1);
  const [resolution,setResolution] = useState({width:0,height:0});
  const video = useRef<HTMLVideoElement>(null);
  const media = useRef<MediaStream | null>(null);
  const demoImage = useRef<HTMLImageElement | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const controller = useRef<AbortController | null>(null);
  const generation = useRef(0);
  const session = useRef<StartResult | null>(null);
  const sequence = useRef(0);
  const polling = useRef(false);
  const savedCallback = useRef(onSaved);
  savedCallback.current=onSaved;

  const halt = useCallback((reason='', updateUi=true)=>{
    generation.current+=1;
    if(timer.current) clearTimeout(timer.current);
    timer.current=null;controller.current?.abort();controller.current=null;
    media.current?.getTracks().forEach(track=>track.stop());media.current=null;
    if(video.current)video.current.srcObject=null;
    demoImage.current=null;polling.current=false;
    const old=session.current;session.current=null;
    if(old)void request(`/live/${old.id}/stop`,{method:'POST',keepalive:true}).catch(()=>{});
    if(updateUi){setMode('idle');setStarting(false);setAnalyzing(false);if(reason)setNotice(reason);}
  },[]);
  useEffect(()=>{
    const visibility=()=>{if(document.hidden)halt('Lectura detenida al ocultar la web. Puedes volver a iniciarla.');};
    document.addEventListener('visibilitychange',visibility);
    return ()=>{document.removeEventListener('visibilitychange',visibility);halt('',false);};
  },[halt]);
  useEffect(()=>{if(mode==='camera'&&video.current&&media.current)video.current.srcObject=media.current;},[mode]);

  async function tick(run:number, source:'camera'|'demo') {
    const current=session.current;
    if(run!==generation.current||!current)return;
    const image=source==='demo'?demoImage.current:video.current;
    const width=source==='demo'?demoImage.current?.naturalWidth:video.current?.videoWidth;
    const height=source==='demo'?demoImage.current?.naturalHeight:video.current?.videoHeight;
    if(!image||!width||!height){halt('No se pudo recibir imagen de la cámara. Revisa el dispositivo e inicia de nuevo.');return;}
    const magnification=source==='camera'?zoomRef.current:1;
    const cropWidth=width/magnification,cropHeight=height/magnification;
    const canvas=document.createElement('canvas');const scale=Math.min(1,2048/Math.max(cropWidth,cropHeight));
    canvas.width=Math.round(cropWidth*scale);canvas.height=Math.round(cropHeight*scale);
    canvas.getContext('2d')!.drawImage(image,(width-cropWidth)/2,(height-cropHeight)/2,cropWidth,cropHeight,0,0,canvas.width,canvas.height);
    let blob=await new Promise<Blob | null>(resolve=>canvas.toBlob(resolve,'image/jpeg',.94));
    if(blob&&blob.size>1.9*1024*1024)blob=await new Promise<Blob | null>(resolve=>canvas.toBlob(resolve,'image/jpeg',.8));
    if(run!==generation.current)return;
    if(!blob){halt('No se pudo leer el fotograma. Inicia de nuevo la cámara.');return;}
    const abort=new AbortController();controller.current=abort;
    setAnalyzing(true);
    try {
      const form=new FormData();form.append('file',blob,'fotograma.jpg');form.append('sequence',String(++sequence.current));
      const result=await request<LiveFrame>(`/live/${current.id}/frames`,{method:'POST',body:form,signal:abort.signal});
      if(run!==generation.current)return;
      setFrame(result);
      if(result.recording){const record=result.recording;setSaved(items=>items.some(r=>r.id===record.id)?items:[record,...items].slice(0,20));savedCallback.current(record);}
      timer.current=setTimeout(()=>void tick(run,source),current.interval_ms);
    } catch(e) {
      if(run!==generation.current||abort.signal.aborted)return;
      halt('Lectura detenida; los registros guardados se conservan.');
      setError(e instanceof Error?e.message:'No se pudo continuar la lectura.');
    } finally {if(run===generation.current)setAnalyzing(false);}
  }
  function beginPolling(source:'camera'|'demo') {
    if(polling.current||!session.current)return;
    polling.current=true;void tick(generation.current,source);
  }
  async function start(source:'camera'|'demo') {
    if(starting||mode!=='idle')return;
    if(!subject.trim()&&source!=='demo'){setError('Indica el alias del astronauta antes de abrir la cámara.');return;}
    halt();const run=generation.current;
    setStarting(true);setError('');setNotice('');setFrame(null);setSaved([]);
    let acquired:MediaStream | null=null;
    try {
      if(source==='camera'){
        if(!navigator.mediaDevices?.getUserMedia)throw new Error('La cámara necesita HTTPS y un navegador compatible.');
        acquired=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},width:{ideal:2560},height:{ideal:1440},frameRate:{ideal:15,max:30}},audio:false});
        if(run!==generation.current){acquired.getTracks().forEach(t=>t.stop());return;}
        media.current=acquired;
        const track=acquired.getVideoTracks()[0];
        const capabilities=track.getCapabilities?.() as MediaTrackCapabilities & {focusMode?:string[];exposureMode?:string[];whiteBalanceMode?:string[]};
        const tuning:Record<string,string>={};
        for(const key of ['focusMode','exposureMode','whiteBalanceMode'] as const)if(capabilities?.[key]?.includes('continuous'))tuning[key]='continuous';
        if(Object.keys(tuning).length)await track.applyConstraints({advanced:[tuning as MediaTrackConstraintSet]}).catch(()=>{});
        acquired.getVideoTracks().forEach(t=>t.addEventListener('ended',()=>halt('El navegador o el dispositivo cerró la cámara.')));
      }else{
        const image=new Image();image.src='/api/live/demo-screen';await image.decode();
        if(run!==generation.current)return;
        demoImage.current=image;
      }
      const alias=subject.trim()||(source==='demo'?'DEMO-LIVE':'');
      const result=await request<StartResult>('/live/sessions',{method:'POST',body:JSON.stringify({subject_alias:alias,device_type:category,is_demo:source==='demo'||declaredDemo})});
      if(run!==generation.current){void request(`/live/${result.id}/stop`,{method:'POST',keepalive:true}).catch(()=>{});acquired?.getTracks().forEach(t=>t.stop());return;}
      setSubject(alias);session.current=result;sequence.current=0;setMode(source);
      if(source==='demo')beginPolling('demo');
    }catch(e){
      if(run!==generation.current)return;
      halt();
      const name=e instanceof Error?e.name:'';
      setError(name==='NotAllowedError'?'El navegador no permitió la cámara. Habilita el permiso para esta web y vuelve a iniciar.':name==='NotFoundError'?'No se encontró una cámara disponible. Conecta una o abre la web desde tu teléfono.':name==='NotReadableError'?'La cámara está ocupada o no pudo iniciarse. Cierra otras aplicaciones que la usen.':e instanceof Error?e.message:'No se pudo abrir la cámara.');
    }finally{if(run===generation.current)setStarting(false);}
  }
  const active=mode!=='idle';
  const visibleSaved=saved.length?saved:pending.filter(r=>r.subject_alias===subject&&r.is_demo===declaredDemo).slice(0,8);
  return <>
    <div className="page-heading"><div><span className="eyebrow">LECTURA CONTINUA / CÁMARA EN VIVO</span><h1>Enfoca. Lee.<br/>Registra automáticamente.</h1><p>Mantén la pantalla a la vista. El sistema guarda las lecturas estables sin tomar una foto manual.</p></div><span className="tag"><Radio size={14}/> Monitoreo visual</span></div>
    {error&&<div role="alert" className="notice error"><Info size={17}/>{error}</div>}
    {notice&&<div className="notice small"><Info size={16}/>{notice}</div>}
    <div className="live-layout"><section className="capture-panel live-camera-panel"><div className="panel-title compact"><div><h2>{mode==='demo'?'Señal de prueba simulada':active?'Cámara en vivo':'Enfoca la pantalla del instrumento'}</h2><p>{active?'Lectura periódica · Sin audio · Puedes detenerla en cualquier momento.':'Buena luz, números y unidades visibles; evita reflejos y modo memoria.'}</p></div><span className={`live-indicator ${active?'active':''}`}><span/>{active?'EN VIVO':'EN ESPERA'}</span></div>
      <div className="viewfinder live-viewfinder" style={mode==='camera'&&resolution.width?{aspectRatio:`${resolution.width}/${resolution.height}`}:undefined}>{mode==='camera'?<><video ref={video} autoPlay playsInline muted onLoadedMetadata={()=>setResolution({width:video.current?.videoWidth??0,height:video.current?.videoHeight??0})} onLoadedData={()=>beginPolling('camera')}/><div className="reading-roi" style={{inset:`${(1-1/zoom)*50}%`}} aria-hidden="true"/></>:mode==='demo'?<img src="/api/live/demo-screen" alt="Pantalla sintética repetida para demostrar la lectura automática; no es una cámara real"/>:<div className="scan-corners"><ScanLine size={58} strokeWidth={1}/><span>Reloj, oxímetro, tensiómetro<br/>o instrumento compatible</span></div>}{active&&<span className="live-overlay"><span className={analyzing?'status-dot pulse-dot':'status-dot'}/>{mode==='demo'?'DATOS FICTICIOS / SEÑAL SIMULADA':analyzing?'ANALIZANDO PANTALLA':'ESPERANDO SIGUIENTE LECTURA'}</span>}</div>
      <div className="camera-quality-controls"><label>Área de lectura <strong>{zoom.toFixed(1)}×</strong><input type="range" aria-label="Acercar área de lectura" min="1" max="3" step="0.1" value={zoom} disabled={mode==='demo'} onChange={e=>{const value=Number(e.target.value);setZoom(value);zoomRef.current=value;}}/></label><p>{resolution.width&&mode==='camera'?`${resolution.width} × ${resolution.height} px recibidos. `:''}Centra toda la pantalla, incluidas las etiquetas y unidades, en el marco. Si hay reflejo, cambia ligeramente el ángulo; no uses flash directo.</p></div>
      <div className="capture-controls">{active?<button className="button primary" onClick={()=>halt('Lectura detenida. Las observaciones guardadas siguen en el historial.')}><Pause size={17}/> Detener lectura</button>:starting?<button className="button secondary" onClick={()=>halt('Inicio cancelado.')}><LoaderCircle className="spin" size={17}/> Cancelar inicio</button>:<button className="button primary" onClick={()=>void start('camera')}><Camera size={17}/> Iniciar cámara en vivo</button>}</div>
      <div className="capture-note"><ShieldCheck size={17}/><span>La cámara permanece activa. Se analizan fotogramas espaciados; solo se conserva la evidencia de las lecturas guardadas. No se graba un video.</span></div>
      <div className="live-status" role="status"><div><Activity size={18}/><strong>{frame?.message??'Al iniciar, busca una lectura y espera a que sea consistente en al menos tres fotogramas.'}</strong></div><div className="stability-progress" aria-label={`Comprobaciones consistentes: ${frame?.count??0} de ${frame?.target??3}`}>{[0,1,2].map(i=><span className={(frame?.count??0)>i?'complete':''} key={i}/>)}</div><small>{frame?.count??0} / {frame?.target??3} comprobaciones · La estabilidad no certifica precisión médica.</small></div>
      {frame?.warnings?.length? <div className="camera-hints">{frame.warnings.slice(0,2).map(w=><p key={w}><Info size={13}/>{w}</p>)}</div>:null}
      <details className="live-demo"><summary>Probar el flujo continuo sin usar una cámara</summary><p>Repite una pantalla generada por el mismo circuito de OCR, estabilidad y registro. Los datos se guardan como ficticios.</p><button className="button secondary" disabled={active||starting} onClick={()=>void start('demo')}><Play size={15}/> Iniciar señal simulada</button></details>
    </section><section className="live-side"><div className="review-panel"><div className="panel-title compact"><div><span className="eyebrow">ANTES DE INICIAR</span><h2>¿A quién corresponden las lecturas?</h2></div><ClipboardList size={21}/></div><div className="live-settings"><label>Alias del astronauta<input value={subject} onChange={e=>setSubject(e.target.value)} maxLength={80} placeholder="ej. ASTRO-01" disabled={active||starting}/></label><label>Tipo de instrumento<select value={category} onChange={e=>setCategory(e.target.value)} disabled={active||starting}><option value="auto">Identificar por etiquetas</option>{devices.map(d=><option key={d.id} value={d.id}>{d.label}</option>)}</select></label><label className="checkbox"><input type="checkbox" checked={declaredDemo} onChange={e=>setDeclaredDemo(e.target.checked)} disabled={active||starting}/> Estoy usando datos ficticios.</label>{mode==='demo'&&<p className="input-hint">La señal simulada se guarda siempre como ficticia.</p>}</div><div className="live-current"><span className="eyebrow">LECTURA EN PANTALLA / SIN VALIDAR</span>{frame?.fields.length?<div className="live-values">{frame.fields.map(f=><div key={f.code}><span>{fieldNames[f.code]??f.code}</span><strong>{f.value}<small>{f.unit??'unidad sin leer'}</small></strong></div>)}</div>:<div className="inline-empty"><Activity size={22}/><p>Los valores aparecerán mientras enfoques la pantalla, sin pulsar un botón de captura.</p></div>}</div></div>
      <div className="live-saved"><div className="section-heading"><h2><Check size={17}/> Guardadas automáticamente</h2><span className="eyebrow">{saved.length} EN ESTA SESIÓN</span></div><p className="input-hint">Sin duplicar valores iguales o prácticamente iguales mientras continúen en pantalla. Se guardan como observaciones pendientes de revisión.</p>{visibleSaved.length?<LiveReadings items={visibleSaved} onReview={r=>{halt();onReview(r);}} onFollowUp={s=>{halt();onFollowUp(s);}}/>:<div className="live-empty">El registro aparece aquí cuando los valores y las unidades se mantienen estables.</div>}</div>
    </section></div>
  </>;
}
