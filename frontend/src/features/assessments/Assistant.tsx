import { useEffect, useState } from 'react';
import { Activity, ArrowRight, ArrowUpRight, Check, ClipboardList, HeartPulse, History, Info, LoaderCircle, MessageCircle, Orbit, Plus, Send, X } from 'lucide-react';
import { request } from '../../services/api';
import { LiveReadings } from '../capture/LiveMonitor';
import type { AssistantSnapshot, HealthContext, Source, LiveReading } from '../../services/api';

const formatDate = (value: string) => new Date(value).toLocaleString('es-GT', { dateStyle:'medium', timeStyle:'short' });
const environments: Record<string,string> = { unknown:'Sin especificar', station:'Estación espacial', spacecraft:'Nave espacial', moon:'Superficie lunar', mars:'Superficie de Marte', earth:'Tierra / simulación' };
const moods: Record<string,string> = { unknown:'Sin especificar', steady:'Estable', strained:'Con tensión o estrés', low:'Ánimo bajo' };
const flags: Record<string,string> = { chest_pain:'Dolor o presión intensa en el pecho', breathing:'Dificultad importante para respirar', consciousness:'Desmayo o confusión nueva' };
const prompts = [ ['overview','Resumen'], ['changes','Cambios'], ['next','Faltantes'], ['mission','Misión'], ['radiation','Radiación'] ] as const;
const blankContext = (alias: string, demo: boolean): HealthContext => ({ subject_alias:alias, is_demo:demo, environment:'unknown', sleep_hours:null, mood:'unknown', symptoms:'', medical_notes:'', red_flags:[] });

function Sources({ ids, sources }: { ids: string[]; sources: Source[] }) {
  return <div className="evidence-sources">{ids.map(id => { const source=sources.find(s=>s.id===id); return source ? <a key={id} href={source.url} target="_blank" rel="noreferrer">{source.organization} · {source.title}<ArrowUpRight size={11}/></a> : null; })}</div>;
}

const actionCopy: Record<string,string> = {
  repeat:'Repite según el plan de misión. Usa el mismo equipo y condiciones.',
  first:'Inicia la cámara. Después revisa la lectura guardada.',
  oxygen:'Sigue el manual del oxímetro. Si la lectura o los síntomas preocupan, avisa al médico.',
  circulation:'Registra actividad y síntomas. Comparte los cambios con el médico.',
  glucose:'Anota la última comida. Sigue tus objetivos médicos individuales.',
  temperature:'Anota dónde mediste y con qué termómetro.',
  rest:'Compara tu descanso con el horario de misión. Registra somnolencia.',
  wellbeing:'Si el malestar persiste, contacta al apoyo médico o psicológico.',
  symptoms:'Comunica tus síntomas y su evolución al responsable médico.',
  autonomy:'Prepara lecturas y síntomas para la consulta. Sigue el plan de comunicación.',
  habitat:'Si hay síntomas, registra las alertas del hábitat. No ajustes el soporte vital desde esta web.',
  routine:'Registra descanso, actividad y ánimo.',
  radiation:'Consulta el dosímetro y el protocolo de misión con la tripulación.',
};
function Recommendation({ item, sources }: {item:AssistantSnapshot['recommendations'][number];sources:Source[]}) {
  return <article className={`recommendation ${item.priority==='urgent'?'urgent':''}`}><div><h3>{item.title}</h3><p>{item.priority==='urgent'?item.action:actionCopy[item.id]??item.action}</p><details className="compact-details"><summary>Por qué y fuentes</summary><p>{item.action}</p><div className="recommendation-reason">{item.reason}</div><Sources ids={item.source_ids} sources={sources}/></details></div></article>;
}
function briefAnswer(snapshot:AssistantSnapshot, intent:string) {
  if(snapshot.status==='urgent')return 'Activa el protocolo de emergencia. Avisa al responsable médico ahora.';
  if(intent==='changes')return snapshot.metrics.filter(m=>m.delta!==null).map(m=>`${m.label}: ${m.delta!>0?'+':''}${m.delta} ${m.unit}`).join(' · ')||'Falta otra lectura comparable.';
  if(intent==='next')return 'Completa los datos pendientes.';
  if(intent==='mission')return environments[snapshot.context?.environment??'unknown'];
  if(intent==='radiation')return 'Consulta el dosímetro. Los signos vitales no miden radiación.';
  return snapshot.record_count?'Revisión médica pendiente.':'Añade tu primera lectura.';
}

export function Assistant({ initialSubject, initialDemo, onCapture, onReview }: { initialSubject: string; initialDemo: boolean; onCapture: () => void; onReview:(item:LiveReading)=>void }) {
  const [subjects,setSubjects] = useState<{ subject_alias:string; is_demo:boolean }[]>([]);
  const [alias,setAlias] = useState(initialSubject);
  const [draftAlias,setDraftAlias] = useState(initialSubject || 'ASTRO-01');
  const [demo,setDemo] = useState(initialDemo);
  const [intent,setIntent] = useState('overview');
  const [snapshot,setSnapshot] = useState<AssistantSnapshot | null>(null);
  const [loading,setLoading] = useState(false);
  const [error,setError] = useState('');
  const [generation,setGeneration] = useState(0);
  const [contextOpen,setContextOpen] = useState(false);
  const [context,setContext] = useState<HealthContext>(blankContext(initialSubject,initialDemo));
  const [saving,setSaving] = useState(false);
  const [saved,setSaved] = useState(false);
  useEffect(()=>{ let active=true; void request<{items:typeof subjects}>('/assistant/subjects').then(result=>{
    if (!active) return;
    setSubjects(result.items);
    if (!initialSubject && result.items.length) { const first=result.items.find(s=>!s.is_demo) ?? result.items[0]; setAlias(first.subject_alias); setDraftAlias(first.subject_alias); setDemo(first.is_demo); }
  }).catch(e=>{if(active)setError(e.message);}); return ()=>{active=false;}; },[initialSubject]);
  useEffect(()=>{
    if (!alias.trim()) return;
    let active=true; setLoading(true); setError(''); setSnapshot(null);
    const query=new URLSearchParams({subject_alias:alias,is_demo:String(demo),intent});
    void request<AssistantSnapshot>(`/assistant?${query}`).then(data=>{
      if (!active) return;
      setSnapshot(data); setContext(data.context ?? blankContext(alias,demo));
    }).catch(e=>{if(active)setError(e.message);}).finally(()=>{if(active)setLoading(false);});
    return ()=>{active=false;};
  },[alias,demo,intent,generation]);
  async function saveContext(event: React.FormEvent) {
    event.preventDefault(); setSaving(true); setError('');
    try {
      const {created_at:_, ...body} = context;
      // Send only editable fields; existing context IDs/timestamps are server-owned.
      await request('/assistant/context',{ method:'POST',body:JSON.stringify({subject_alias:alias,is_demo:demo,environment:body.environment,sleep_hours:body.sleep_hours,mood:body.mood,symptoms:body.symptoms,medical_notes:body.medical_notes,red_flags:body.red_flags}) });
      setContextOpen(false); setGeneration(g=>g+1); setSaved(true);
      if (!subjects.some(s=>s.subject_alias===alias && s.is_demo===demo)) setSubjects(s=>[...s,{subject_alias:alias,is_demo:demo}]);
    } catch(e) {setError(e instanceof Error ? e.message:'No se pudo guardar.');} finally {setSaving(false);}
  }
  const redFlagsSelected = context.red_flags.length>0;
  return <>
    <div className="page-heading"><div><span className="eyebrow">SALUD DE MISIÓN</span><h1>Tu seguimiento</h1></div><a className="button secondary" href="#mission-context" onClick={()=>setContextOpen(true)}><Plus size={15}/> Cómo me siento</a></div>
    <section className="subject-strip" aria-label="Seleccionar historial del astronauta">
      <div className="subject-icon"><HeartPulse size={22}/></div>
      <form onSubmit={e=>{e.preventDefault(); if(draftAlias.trim()){setAlias(draftAlias.trim());setContextOpen(false);}}}><label>Alias del astronauta<input list="astronaut-aliases" value={draftAlias} maxLength={80} onChange={e=>setDraftAlias(e.target.value)} placeholder="ASTRO-01" required/></label><datalist id="astronaut-aliases">{subjects.filter(s=>s.is_demo===demo).map(s=><option key={s.subject_alias} value={s.subject_alias}/>)}</datalist><button className="button secondary" type="submit">Ver <ArrowRight size={15}/></button></form>
      <label className="checkbox"><input type="checkbox" checked={demo} onChange={e=>{setDemo(e.target.checked);setContextOpen(false);}}/> Datos ficticios</label>
    </section>
    {error && <div role="alert" className="notice error"><Info size={17}/>{error}<button className="text-button" onClick={()=>setGeneration(g=>g+1)}>Reintentar</button></div>}
    {demo && <div className="notice small"><Info size={16}/>Simulación · Datos ficticios</div>}
    {!alias && <div className="assistant-welcome"><MessageCircle size={40} strokeWidth={1.2}/><h2>Empecemos por el astronauta.</h2><p>Escribe el alias usado al confirmar las capturas. No necesitas crear una cuenta.</p><button className="button primary" onClick={onCapture}><Plus size={16}/> Capturar una lectura</button></div>}
    {loading && <div className="assistant-loading" role="status"><LoaderCircle className="spin" size={24}/>Reuniendo lecturas y contexto…</div>}
    {snapshot && !loading && <>
      <div className="assistant-layout"><div className="assistant-main">
        <section className={`assistant-response ${snapshot.status==='urgent'?'urgent':''}`} aria-live="polite">
          <div className="response-heading"><span className="response-icon"><MessageCircle size={21}/></span><div><span className="eyebrow">SIGUIENTE PASO</span><strong>{snapshot.status_label}</strong></div><span className="response-count">{snapshot.record_count} {snapshot.record_count===1?'registro':'registros'}</span></div>
          <p className="response-answer">{briefAnswer(snapshot,intent)}</p>
          <div className="assistant-prompts" aria-label="Consultas del asistente">{prompts.map(([id,label])=><button key={id} className={intent===id?'active':''} onClick={()=>setIntent(id)}><Send size={12}/>{label}</button>)}</div>
          <details className="assistant-observations compact-details"><summary>Ver evidencia y explicación</summary><p>{snapshot.answer}</p>{snapshot.observations.length ? <ul>{snapshot.observations.map(o=><li key={o}>{o}</li>)}</ul> : <p>Añade una lectura.</p>}</details>
          <p className="assistant-boundary">Orientación · Sin diagnóstico</p>
        </section>
        {snapshot.automatic_readings?.length>0&&<section className="assistant-evidence"><div className="section-heading"><h2><Activity size={18}/> Lecturas en vivo guardadas</h2><span className="eyebrow">SIN REVISIÓN</span></div><p className="input-hint">Pendientes de revisión</p><LiveReadings items={snapshot.automatic_readings} onReview={onReview}/></section>}
        <section className="assistant-evidence"><div className="section-heading"><h2><Activity size={18}/> Tus lecturas</h2><button className="text-button" onClick={onCapture}>Añadir captura <Plus size={14}/></button></div>
          {snapshot.metrics.length ? <><div className="assistant-metrics">{snapshot.metrics.map(m=><article className="assistant-metric" key={m.code}><span>{m.label}</span><strong>{m.value}<small>{m.unit}</small></strong><div className="metric-comparison">{m.delta===null?'Sin lectura anterior':`${m.delta>0?'+':''}${m.delta} ${m.unit} vs. anterior`}</div><small>Medición: {m.measured_at?formatDate(m.measured_at):'hora no documentada'}</small><details className="compact-details metric-detail"><summary>Detalle</summary><small>Registrado: {formatDate(m.confirmed_at)}</small><div className="metric-series" aria-label={`Últimas ${m.series.length} confirmaciones de ${m.label}`}>{m.series.map((p,i)=><span key={i} title={formatDate(p.confirmed_at)}>{p.value}{i<m.series.length-1 && <ArrowRight size={10}/>}</span>)}</div><a href={`/api/measurements/${m.record_id}/report.pdf`}>PDF <ArrowUpRight size={12}/></a></details></article>)}</div><p className="input-hint">Cambios numéricos · Revisa tiempos y condiciones.</p></> : <div className="inline-empty"><ClipboardList size={24}/><p>Sin lecturas revisadas.</p></div>}
        </section>
        <section className="action-section"><div className="section-heading"><h2><MessageCircle size={18}/> Acciones</h2></div><div className="recommendation-list">{snapshot.recommendations.slice(0,3).map(r=><Recommendation key={r.id} item={r} sources={snapshot.sources}/>)}</div>{snapshot.recommendations.length>3&&<details className="compact-details more-actions"><summary>Más acciones ({snapshot.recommendations.length-3})</summary><div className="recommendation-list">{snapshot.recommendations.slice(3).map(r=><Recommendation key={r.id} item={r} sources={snapshot.sources}/>)}</div></details>}</section>
      </div><aside className="assistant-side">
        <section className="context-card" id="mission-context"><div className="section-heading"><h2><Orbit size={18}/> Contexto de misión</h2></div><dl><div><dt>Entorno</dt><dd>{environments[snapshot.context?.environment??'unknown']}</dd></div><div><dt>Sueño declarado</dt><dd>{snapshot.context?.sleep_hours==null?'Sin registrar':`${snapshot.context.sleep_hours} horas`}</dd></div><div><dt>Estado de ánimo</dt><dd>{moods[snapshot.context?.mood??'unknown']}</dd></div></dl>{snapshot.context?.created_at && <p className="input-hint">Declarado el {formatDate(snapshot.context.created_at)}</p>}<button className="button secondary full" onClick={()=>{setContextOpen(!contextOpen);setSaved(false);}}><Plus size={15}/>{contextOpen?'Cerrar formulario':'Actualizar contexto'}</button>{saved&&<p className="input-hint"><Check size={12}/>Contexto guardado.</p>}
          {contextOpen && <form className="context-form" onSubmit={saveContext}><div className="form-heading"><strong>Cómo te encuentras ahora</strong><button type="button" aria-label="Cerrar contexto" onClick={()=>setContextOpen(false)}><X size={15}/></button></div><label>Entorno<select value={context.environment} onChange={e=>setContext({...context,environment:e.target.value})}>{Object.entries(environments).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label><label>Horas de sueño (último descanso)<input type="number" min="0" max="24" step="0.1" value={context.sleep_hours??''} onChange={e=>setContext({...context,sleep_hours:e.target.value===''?null:Number(e.target.value)})}/></label><label>Estado de ánimo<select value={context.mood} onChange={e=>setContext({...context,mood:e.target.value})}>{Object.entries(moods).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label><label>Síntomas y contexto<textarea rows={3} maxLength={2000} value={context.symptoms} onChange={e=>setContext({...context,symptoms:e.target.value})} placeholder="Qué notas, desde cuándo, actividad reciente…"/></label><label>Antecedentes, alergias o tratamientos declarados<textarea rows={3} maxLength={2000} value={context.medical_notes} onChange={e=>setContext({...context,medical_notes:e.target.value})} placeholder="Información para el responsable médico; no modifica tratamientos."/></label><fieldset className="red-flags"><legend>¿Hay alguna señal de alarma ahora?</legend>{Object.entries(flags).map(([key,label])=><label className="checkbox" key={key}><input type="checkbox" checked={context.red_flags.includes(key)} onChange={e=>setContext({...context,red_flags:e.target.checked?[...context.red_flags,key]:context.red_flags.filter(f=>f!==key)})}/>{label}</label>)}</fieldset>{redFlagsSelected&&<div role="alert" className="notice error">Activa el protocolo de emergencia y avisa al responsable médico. No esperes a guardar ni a tomar otra fotografía.</div>}<p className="input-hint">El texto libre se conserva para revisión; no se analiza clínicamente. Si hay alarma, comunícala de inmediato.</p><button className="button primary full" disabled={saving}>{saving?<LoaderCircle className="spin" size={16}/>:<Check size={16}/>}Guardar y actualizar seguimiento</button></form>}
        </section>
        <details className="gaps-card compact-details"><summary>Datos pendientes ({snapshot.missing_data.length})</summary><ul>{snapshot.missing_data.map(g=><li key={g}>{g}</li>)}</ul></details>

      </aside></div>
      <details className="assistant-timeline compact-details"><summary>Historial de salud ({snapshot.timeline.length})</summary><div className="timeline-content"><div className="section-heading"><h2><History size={18}/> Historial de salud</h2><span className="eyebrow">{alias} / {demo?'FICTICIO':'DATOS DECLARADOS'}</span></div><p className="input-hint">Últimos 50 eventos por confirmación o declaración. El historial depende del espacio de este navegador; descarga los informes para conservar una copia.</p>{snapshot.timeline.length ? <div className="timeline-events">{snapshot.timeline.map(item=><article className="timeline-event" key={item.id}><span className={`timeline-dot ${item.kind==='context'?'context':''}`}/><div><small>{formatDate(item.created_at)}</small><h3>{item.title}</h3>{item.readings&&<p>{item.readings.map(r=>`${r.value} ${r.unit}`).join(' · ')}</p>}{item.kind==='context'&&<p>{item.environment} · Sueño: {item.sleep_hours==null?'sin registrar':`${item.sleep_hours} h`} · {moods[item.mood??'unknown']}</p>}{item.notes&&<p className="timeline-note">Declarado: {item.notes}</p>}{item.medical_notes&&<p className="timeline-note">Antecedentes / tratamientos declarados: {item.medical_notes}</p>}{item.red_flags?.length ? <p className="timeline-alarm">Señales declaradas: {item.red_flags.map(f=>flags[f]).join(', ')}</p>:null}</div>{item.kind==='measurement'&&<a href={`/api/measurements/${item.id}/report.pdf`} className="text-button">PDF <ArrowUpRight size={12}/></a>}</article>)}</div>:<div className="inline-empty"><History size={24}/><p>Sin eventos.</p></div>}</div></details>
      <details className="assistant-library"><summary>Fuentes y límites ({snapshot.sources.length})</summary><p>{snapshot.limitation}</p><p>NASA y CSA aportan contexto espacial. FDA y MedlinePlus complementan la calidad de las mediciones y las señales de alarma. Las recomendaciones son reglas del prototipo, no protocolos aprobados por estas agencias.</p><div>{snapshot.sources.map(s=><a href={s.url} target="_blank" rel="noreferrer" key={s.id}>{s.organization} · {s.title}<ArrowUpRight size={12}/></a>)}</div></details>
    </>}
  </>;
}
