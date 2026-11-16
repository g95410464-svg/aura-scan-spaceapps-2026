import { t, locale, reportUrl, LanguageProvider, LanguageSwitcher, useLanguage } from './i18n';
import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Activity, ArrowDownToLine, ArrowRight, Camera, Radio, Play, Check, CheckCircle2, ChevronRight, ClipboardList, FileText, History, Info, LoaderCircle, Orbit, Plus, MessageCircle, ScanLine, ShieldCheck, Upload, X } from 'lucide-react';
import { request, ensureSession, resetSession } from './services/api';
import type { Capture, Device, Measurement, LiveReading } from './services/api';
import './styles.css';
import './mission-theme.css';
import { Assistant } from './features/assessments/Assistant';
import { LiveMonitor, LiveReadings } from './features/capture/LiveMonitor';
import { SimulationCoach, SimulationReadings, SimulationReport } from './features/capture/Simulation';
import type { SimulationResult } from './features/capture/Simulation';

type Tab = 'capture' | 'history' | 'assistant';
const labels: Record<string, string> = { systolic: 'Presión sistólica', diastolic: 'Presión diastólica', pulse: 'Pulso', spo2: 'Saturación SpO₂', temperature: 'Temperatura', glucose: 'Glucosa' };
const date = (value: string) => new Date(value).toLocaleString(locale(), { dateStyle: 'medium', timeStyle: 'short' });
const message = (e: unknown) => e instanceof Error ? e.message : t("No se pudo completar la operación.");

function Brand({ light = false }: { light?: boolean }) {
  return <div className={`brand ${light ? 'light' : ''}`}><span className="brand-icon"><Orbit size={29} strokeWidth={1.4} /></span><span>AURA<span className="brand-scan">SCAN</span></span></div>;
}

function Report({ record, onNew, onAssistant }: { record: Measurement; onNew?: () => void; onAssistant?: () => void }) {
  return <section className="report-panel"><div className="panel-title"><div><span className="eyebrow">{record.readings.some(r=>r.provenance==='simulation_scripted')?t("SIMULACIÓN / REGISTRO GUIONADO"):t("REGISTRO CONFIRMADO")}</span><h2>{t("Lectura registrada")}</h2></div><CheckCircle2 className="success-icon" size={32} /></div>
    {record.is_demo && <div className="notice">{t("Demostración con datos ficticios. No corresponde a una medición real.")}</div>}
    <div className="record-meta"><span><small>{t("ASTRONAUTA / ALIAS")}</small><strong>{record.subject_alias}</strong></span><span><small>{t("MEDICIÓN")}</small><strong>{record.measured_at ? date(record.measured_at) : t("Hora no declarada")}</strong></span><span><small>{t("REGISTRO")}</small><strong>{date(record.created_at)}</strong></span></div>
    <div className="reading-grid">{record.readings.map(r => <div className="reading-card" key={r.code}><span>{t(labels[r.code])}</span><strong>{r.value}<small>{t(r.unit??'')}</small></strong><small>{r.provenance === 'ocr_confirmed' ? t("OCR revisado y confirmado") : r.provenance==='simulation_scripted'?t("Simulación guionada con OCR"):t("Introducido o corregido por el usuario")}</small></div>)}</div>
    <div className="report-section"><h3>{t("Lo que sabemos de este registro")}</h3><ul>{record.assessment.findings.map((finding, i) => <li key={i}>{t(finding)}</li>)}</ul></div>
    {record.assessment.trends.length > 0 && <div className="report-section"><h3>{t("Diferencia frente al registro anterior")}</h3><div className="trend-row">{record.assessment.trends.map(trend => <span key={trend.code}>{t(labels[trend.code])}: <b>{trend.delta > 0 ? '+' : ''}{trend.delta} {t(trend.unit)}</b></span>)}</div></div>}
    <div className="report-section"><h3>{t("Siguientes comprobaciones")}</h3><ul>{record.assessment.next_steps.map((s, i) => <li key={i}>{t(s)}</li>)}</ul></div>
    <p className="fine-print">{t(record.assessment.limitation)}</p><div className="actions"><a className="button primary" href={reportUrl(record.id)}><ArrowDownToLine size={17} /> {t("Descargar PDF")}</a>{onAssistant && <button className="button secondary" onClick={onAssistant}><MessageCircle size={17} /> {t("Ver acciones")}</button>}{onNew && <button className="button secondary" onClick={onNew}><Plus size={17} /> {t("Nueva captura")}</button>}</div>
  </section>;
}

function PhotoReview({ devices, onSaved, onFollowUp, initialCapture }: { devices: Device[]; onSaved: (m: Measurement) => void; onFollowUp: (m: Measurement) => void; initialCapture?: Capture | null }) {
  const [capture, setCapture] = useState<Capture | null>(null);
  const [record, setRecord] = useState<Measurement | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState('auto');
  const [drafts, setDrafts] = useState<Record<string, { value: string; unit: string }>>({});
  const fileInput = useRef<HTMLInputElement>(null);
  const [subject, setSubject] = useState('');
  const [symptoms, setSymptoms] = useState('');
  const [measuredAt, setMeasuredAt] = useState('');
  const [reviewed, setReviewed] = useState(false);
  const [declaredDemo, setDeclaredDemo] = useState(false);
  const device = devices.find(d => d.id === selected);
  useEffect(() => { if (initialCapture) applyCapture(initialCapture); }, [initialCapture]);
  function applyCapture(result: Capture) {
    setCapture(result); setReviewed(false); setRecord(null);
    setSelected(devices.some(d => d.id === result.device_type) ? result.device_type : selected);
    setDrafts(Object.fromEntries(result.fields.map(f => [f.code, { value: String(f.value), unit: f.unit ?? '' }])));
    if (result.subject_alias) setSubject(result.subject_alias);
    else if (result.is_demo && !subject) setSubject('DEMO-01');
  }
  async function analyze(file?: File) {
    if (file && file.size > 8 * 1024 * 1024) { setError(t("La imagen debe pesar como máximo 8 MB.")); return; }
    setBusy(true); setError('');
    try {
      if (!file) applyCapture(await request<Capture>('/captures/demo', { method: 'POST' }));
      else { const form = new FormData(); form.append('file', file); form.append('device_type', selected); form.append('is_demo', String(declaredDemo)); applyCapture(await request<Capture>('/captures', { method: 'POST', body: form })); }
    } catch (e) { setError(message(e)); } finally { setBusy(false); }
  }
  async function confirm(e: React.FormEvent) {
    e.preventDefault(); if (!capture || !device) return;
    setBusy(true); setError('');
    try {
      const readings = device.fields.filter(code => drafts[code]?.value.trim()).map(code => ({ code, value: Number(drafts[code].value), unit: drafts[code].unit }));
      const saved = await request<Measurement>(`/captures/${capture.id}/confirm`, { method: 'POST', body: JSON.stringify({ subject_alias: subject, device_type: selected, symptoms, readings, measured_at: measuredAt ? new Date(measuredAt).toISOString() : null, reviewed }) });
      setRecord(saved); onSaved(saved);
    } catch (e) { setError(message(e)); } finally { setBusy(false); }
  }
  function reset() { setCapture(null); setRecord(null); setReviewed(false); setDrafts({}); setError(''); }
  const phase = record ? 3 : capture ? 2 : 1;
  return <><div className="page-heading"><div><span className="eyebrow">{t("EVALUACIÓN / CAPTURA VISUAL")}</span><h1>{t("Revisa la evidencia.")}<br className="mobile-only" /> {t("Valida las lecturas.")}</h1><p>{t("Revisa una observación automática o carga una imagen como alternativa.")}</p></div><span className="tag"><ScanLine size={14} /> {t("OCR experimental")}</span></div>
    <div className="phase-bar">{[t("Captura del instrumento"), t("Revisión de lecturas"), t("Informe y seguimiento")].map((s, i) => <div className={phase === i + 1 ? 'active' : phase > i + 1 ? 'complete' : ''} key={s}><span>{phase > i + 1 ? <Check size={14} /> : `0${i + 1}`}</span>{t(s)}{i < 2 && <ChevronRight size={16} />}</div>)}</div>
    {error && <div className="notice error" role="alert"><Info size={17} />{t(error)}</div>}
    {record ? <Report record={record} onNew={reset} onAssistant={() => onFollowUp(record)} /> : <div className="capture-layout"><section className="capture-panel"><div className="panel-title compact"><div><h2>{capture ? t("Evidencia de la lectura") : t("Enfoca la pantalla")}</h2><p>{capture ? date(capture.created_at) : t("Buena luz, sin reflejos y con etiquetas visibles.")}</p></div><Camera size={20} /></div>
      <div className={`viewfinder ${capture ? 'has-image' : ''}`}>
        {capture ? <img src={capture.image_url} alt={t("Pantalla capturada del instrumento, para revisar los valores extraídos")} /> : <><div className="scan-corners"><ScanLine size={62} strokeWidth={1} /><span>{t("Coloca el instrumento")}<br />{t("dentro del encuadre")}</span></div><div className="viewfinder-bottom"><span className="status-dot" /> {t("CÁMARA EN ESPERA")}</div></>}
        {capture?.is_demo && <span className="demo-overlay">{t("DATOS FICTICIOS")}</span>}{busy && <div className="processing" role="status"><LoaderCircle className="spin" size={34} /><strong>{t("Procesando imagen")}</strong><span>{t("Buscando dígitos, etiquetas y unidades…")}</span></div>}
      </div>
      <div className="capture-controls"><button className="button secondary" disabled={busy} onClick={() => fileInput.current?.click()}><Upload size={17} /> {t("Cargar imagen alternativa")}</button></div>
      <input className="visually-hidden" ref={fileInput} type="file" accept="image/jpeg,image/png,image/webp" aria-label={t("Seleccionar imagen del instrumento")} onChange={e => { const file = e.target.files?.[0]; e.target.value = ''; if (file) void analyze(file); }} />
      <div className="capture-note"><ShieldCheck size={17} /><span>{t("PNG, JPG o WebP · Hasta 8 MB y 12 megapíxeles. La imagen queda vinculada al espacio de este navegador.")}</span></div>
      {!capture && <div className="demo-box"><div><strong>{t("Explora antes de capturar")}</strong><p>{t("Prueba el OCR con una pantalla generada y datos ficticios.")}</p></div><button className="text-button" disabled={busy} onClick={() => void analyze()}>{t("Usar demostración")} <ArrowRight size={16} /></button></div>}
    </section>
    <section className="review-panel"><div className="panel-title compact"><div><span className="eyebrow">{capture ? t("PASO 02") : t("PREPARACIÓN")}</span><h2>{capture ? t("Revisa antes de guardar") : t("¿Qué vas a registrar?")}</h2></div><ClipboardList size={22} /></div>
      <form onSubmit={confirm}><label>{t("Tipo de instrumento")}<select value={selected} disabled={busy} onChange={e => { setSelected(e.target.value); setReviewed(false); }}><option value="auto">{t("Identificar por etiquetas")}</option>{devices.map(d => <option value={d.id} key={d.id}>{t(d.label)}</option>)}</select></label>
      {!capture ? <><label className="checkbox"><input type="checkbox" checked={declaredDemo} onChange={e => setDeclaredDemo(e.target.checked)} /> {t("La imagen que cargaré contiene datos ficticios.")}</label><div className="empty-review"><Activity size={30} strokeWidth={1.2} /><h3>{t("Las lecturas aparecerán aquí")}</h3><p>{t("El reconocimiento usa etiquetas y unidades. Todavía no identifica modelos exactos ni utiliza un catálogo entrenado de dispositivos.")}</p></div><div className="supported"><span className="eyebrow">{t("CATEGORÍAS PARA EXPLORAR")}</span>{devices.map(d => <span key={d.id}><Check size={13} /> {t(d.label)}</span>)}</div></> : <>
        <div className="model-note"><Info size={15} /><span>{t("Modelo exacto:")} <b>{t("no identificado")}</b>. {capture.recognition === 'visible_labels' ? t("Categoría sugerida por etiquetas.") : t("Completa la revisión manual o repite la captura.")}</span></div>
        {capture.warnings.map((w, i) => <div className="notice small" key={i}>{t(w)}</div>)}
        {device ? <div className="field-list">{device.indicators.map(indicator => { const draft = drafts[indicator.code] ?? { value: '', unit: '' }; const candidate = capture.fields.find(f => f.code === indicator.code); return <div className="field-row" key={indicator.code}><label>{t(indicator.label)}{device.required.includes(indicator.code) && ' *'}<input aria-label={t(indicator.label)} type="number" step="any" min={-1000} max={10000} required={device.required.includes(indicator.code)} value={draft.value} placeholder={t("Sin lectura")} disabled={busy} onChange={e => { setDrafts({ ...drafts, [indicator.code]: { ...draft, value: e.target.value } }); setReviewed(false); }} /></label><label>{t("Unidad")}<select aria-label={t("Unidad de {0}",t(indicator.label))} value={draft.unit} required={!!draft.value || device.required.includes(indicator.code)} disabled={busy} onChange={e => { setDrafts({ ...drafts, [indicator.code]: { ...draft, unit: e.target.value } }); setReviewed(false); }}><option value="">{t("Selecciona")}</option>{indicator.units.map(u => <option key={u} value={u}>{t(u)}</option>)}</select></label><small>{candidate ? `Lectura propuesta por OCR · Revisar con la imagen` : t("Campo sin extraer · Introducción manual")}</small></div>; })}</div> : <div className="notice">{t("Selecciona un tipo de instrumento para completar los campos.")}</div>}
        <label>{t("Alias del astronauta")}<input value={subject} onChange={e => { setSubject(e.target.value); setReviewed(false); }} maxLength={80} placeholder={t("ej. ASTRO-01")} required disabled={busy} /></label>
        <label>{t("Hora de la medición")} <small>{t("(opcional, hora local)")}</small><input type="datetime-local" value={measuredAt} onChange={e => { setMeasuredAt(e.target.value); setReviewed(false); }} disabled={busy} /></label><p className="input-hint">{t("Déjala vacía si no conoces cuándo se realizó la medición.")}</p>
        <label>{t("Síntomas y contexto")} <small>{t("(opcional)")}</small><textarea value={symptoms} onChange={e => { setSymptoms(e.target.value); setReviewed(false); }} rows={3} maxLength={2000} placeholder={t("Cómo se siente, condiciones de la medición…")} disabled={busy} /></label>
        <label className="checkbox"><input type="checkbox" checked={reviewed} onChange={e => setReviewed(e.target.checked)} required disabled={busy} /><span>{t("Revisé los valores, las unidades y el modo de la pantalla. Confirmo a quién corresponde el registro.")}</span></label>
        <button className="button primary full" disabled={busy || !device || !reviewed}>{busy ? <LoaderCircle className="spin" size={17} /> : <CheckCircle2 size={17} />} {t("Confirmar y generar informe")}</button>
      </>}</form>
    </section></div>}
  </>;
}

function App() {
  useLanguage();
  const [loading, setLoading] = useState(true);
  const [simulation,setSimulation] = useState<SimulationResult|null>(null);
  const [simulationBusy,setSimulationBusy] = useState(false);
  const [simulationStep,setSimulationStep] = useState(0);
  const simulationGeneration = useRef(0);
  const simulationKey = useRef<string|null>(null);
  const [sessionGeneration, setSessionGeneration] = useState(0);
  const [bootError, setBootError] = useState('');
  const [tab, setTab] = useState<Tab>('capture');
  const [devices, setDevices] = useState<Device[]>([]);
  const [assistantSubject, setAssistantSubject] = useState('');
  const [assistantDemo, setAssistantDemo] = useState(false);
  const [records, setRecords] = useState<Measurement[]>([]);
  const [automatic, setAutomatic] = useState<LiveReading[]>([]);
  const [captureMode, setCaptureMode] = useState<'live' | 'review'>('live');
  const [reviewCapture, setReviewCapture] = useState<Capture | null>(null);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<Measurement | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    const expired = () => { resetSession(); setLoading(true); setRecords([]); setAutomatic([]); setReviewCapture(null); setCaptureMode('live'); setSelectedRecord(null); setTab('capture'); setSessionGeneration(g => g + 1); };
    window.addEventListener('aura-session-expired', expired);
    return () => window.removeEventListener('aura-session-expired', expired);
  }, []);
  useEffect(() => {
    let active = true;
    setBootError('');
    void ensureSession().then(async () => {
      if (!active) return;
      const [d, h, a] = await Promise.all([request<{ devices: Device[] }>('/devices'), request<{ items: Measurement[] }>('/measurements'), request<{ items: LiveReading[] }>('/live/readings')]);
      if (active) { setDevices(d.devices); setRecords(h.items); setAutomatic(a.items); }
    }).catch(e => { if (active) setBootError(message(e)); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [sessionGeneration]);
  async function startSimulation() {
    const generation=++simulationGeneration.current;
    setSimulationBusy(true);setSimulation(null);setSimulationStep(0);setTab('capture');setSelectedRecord(null);setError('');
    const run_key=simulationKey.current??crypto.randomUUID();simulationKey.current=run_key;
    try {
      const result=await request<SimulationResult>('/simulation/run',{method:'POST',body:JSON.stringify({run_key})});
      if(generation!==simulationGeneration.current)return;
      setSimulation(result);setAssistantSubject(result.subject_alias);setAssistantDemo(true);
      setRecords(previous=>[...result.records.slice().reverse(),...previous.filter(r=>!result.records.some(n=>n.id===r.id))]);
      simulationKey.current=null;
    }catch(e){if(generation===simulationGeneration.current)setError(message(e));}
    finally {if(generation===simulationGeneration.current)setSimulationBusy(false);}
  }
  function closeSimulation(){simulationGeneration.current+=1;setSimulation(null);setSimulationBusy(false);setSimulationStep(0);setTab('capture');setCaptureMode('live');setSelectedRecord(null);}
  function nextSimulation(){if(!simulation)return;if(simulationStep===3){closeSimulation();return;}const next=simulationStep+1;setSimulationStep(next);setSelectedRecord(null);setTab(next===1?'history':next===2?'assistant':'capture');}
  const displayRecords=simulation?records.filter(r=>r.subject_alias===simulation.subject_alias&&r.is_demo):records;
  const displayAutomatic=simulation?automatic.filter(r=>r.subject_alias===simulation.subject_alias&&r.is_demo):automatic;
  function followUp(record: Pick<Measurement, 'subject_alias' | 'is_demo'>) { setAssistantSubject(record.subject_alias); setAssistantDemo(record.is_demo); setTab('assistant'); }
  async function reviewAutomatic(item: LiveReading) {
    setTab('capture'); setCaptureMode('review'); setReviewLoading(true); setReviewCapture(null); setError('');
    try { setReviewCapture(await request<Capture>(`/captures/${item.capture_id}`)); }
    catch(e) { setError(message(e)); } finally { setReviewLoading(false); }
  }
  function saveMeasurement(record: Measurement) { setRecords(previous=>[record,...previous]); setAutomatic(previous=>previous.filter(r=>r.capture_id!==record.capture_id)); }
  if (loading) return <div className="loading-screen"><Orbit size={40} className="slow-spin" /><span>{t("Preparando el sistema…")}</span></div>;
  if (bootError) return <div className="loading-screen"><Info size={32} /><span>{t(bootError)}</span><button className="button primary" onClick={() => { setLoading(true); setSessionGeneration(g => g + 1); }}>{t("Reintentar")}</button></div>;
  return <div className="app-shell"><aside className="sidebar"><Brand light /><div className="mission-label"><span className="status-dot" /> {t("SALUD DE MISIÓN")}</div><nav aria-label={t("Navegación principal")}>{([{ id: 'capture', name: t("Cámara en vivo"), shortName: t("Cámara"), icon: Radio }, { id: 'history', name: t("Historial"), shortName: t("Historial"), icon: History }, { id: 'assistant', name: t("Asistente de salud"), shortName: t("Asistente"), icon: MessageCircle }] as const).map(item => <button key={item.id} className={tab === item.id ? 'active' : ''} aria-label={item.name} aria-current={tab === item.id ? 'page' : undefined} onClick={() => { setTab(item.id); if(simulation)setSimulationStep(item.id==='capture'?0:item.id==='history'?1:2); setError(''); }}><item.icon size={19} /><span className="nav-label">{item.name}</span><span className="nav-label-compact" aria-hidden="true">{item.shortName}</span>{tab === item.id && <span className="nav-dot" />}</button>)}</nav><div className="sidebar-note"><Orbit size={30} strokeWidth={1} /><strong>{t("Salud de misión")}</strong><p>{t("Lecturas con evidencia.")}</p><span>SPACE APPS / 2026</span></div><div className="workspace-status"><ShieldCheck size={19} /><div><strong>{t("Acceso directo")}</strong><small>{t("Espacio de este navegador")}</small></div></div></aside>
    <div className="main-shell"><header className="topbar"><div><span>{t("Centro de salud")}</span><ChevronRight size={14} /><strong>{tab === 'capture' ? t("Evaluación") : tab === 'history' ? t("Historial") : t("Asistente de salud")}</strong></div><div className="topbar-actions"><LanguageSwitcher/><button className="simulation-launch" disabled={simulationBusy} onClick={()=>void startSimulation()}><Play size={13}/> {t("Simulación")}</button><span className="topbar-status"><span className="status-dot" /> {t("Prototipo 0.5")}</span></div></header><main className="workspace">{error && <div className="notice error" role="alert">{t(error)}<button aria-label={t("Cerrar aviso")} onClick={() => setError('')}><X size={16} /></button></div>}
      {(simulationBusy||simulation)&&<SimulationCoach result={simulation} busy={simulationBusy} step={simulationStep} onNext={nextSimulation} onClose={closeSimulation}/>}
      {simulation&&!simulationBusy&&simulationStep===0?<SimulationReadings result={simulation}/>:simulation&&!simulationBusy&&simulationStep===3?<SimulationReport result={simulation} onAssistant={()=>{setSimulationStep(2);setTab('assistant');}}/>:null}
      {!simulationBusy&&!(simulation&&(simulationStep===0||simulationStep===3))&&tab === 'capture' && <><div className="capture-mode-tabs" aria-label={t("Modo de lectura")}><button className={captureMode==='live'?'active':''} onClick={()=>{setCaptureMode('live');setReviewCapture(null);}}><Radio size={15}/> {t("Cámara en vivo")}</button><button className={captureMode==='review'?'active':''} onClick={()=>setCaptureMode('review')}><ClipboardList size={15}/> {t("Revisión manual")}</button></div>{reviewLoading?<div className="assistant-loading"><LoaderCircle className="spin" size={22}/>{t("Abriendo evidencia…")}</div>:captureMode==='live'?<LiveMonitor devices={devices} pending={automatic} onSaved={item=>setAutomatic(previous=>previous.some(r=>r.id===item.id)?previous:[item,...previous])} onReview={item=>void reviewAutomatic(item)} onFollowUp={followUp}/>:<PhotoReview key={reviewCapture?.id??'file'} devices={devices} initialCapture={reviewCapture} onSaved={saveMeasurement} onFollowUp={followUp}/>}</>}
      {!simulationBusy&&tab === 'history' && <><div className="page-heading"><div><span className="eyebrow">{t("CONTINUIDAD / EVIDENCIA")}</span><h1>{t("Historial")}</h1><p>{displayRecords.length} {t("mediciones guardadas ·")} {displayAutomatic.length} {t("lecturas automáticas sin revisar en este navegador.")}</p></div><button className="button primary" onClick={() => setTab('capture')}><Plus size={17} /> {t("Nueva evaluación")}</button></div>{displayAutomatic.length>0&&<section className="history-automatic"><div className="section-heading"><h2><Radio size={18}/> {t("Lecturas automáticas guardadas")}</h2><span className="eyebrow">{t("SIN REVISAR")}</span></div><p className="input-hint">{t("El sistema las registró en vivo. Revisa la evidencia para incorporarlas a las mediciones confirmadas.")}</p><LiveReadings items={displayAutomatic} onReview={item=>void reviewAutomatic(item)} onFollowUp={followUp}/></section>}{displayRecords.length === 0 ? <div className="empty-state"><History size={40} strokeWidth={1} /><h2>{displayAutomatic.length?t("Las lecturas en vivo ya están guardadas."):t("Tu historial empieza con una lectura.")}</h2><p>{t("Revisa su evidencia para incorporarlas a las mediciones confirmadas y sus informes.")}</p><button className="button secondary" onClick={() => setTab('capture')}>{t("Ir a captura")} <ArrowRight size={16} /></button></div> : <><div className="history-list">{displayRecords.map(record => <button className={selectedRecord?.id === record.id ? 'history-row selected' : 'history-row'} onClick={() => setSelectedRecord(record)} key={record.id}><span className="history-icon"><FileText size={20} /></span><span><strong>{record.subject_alias}</strong><small>{t(devices.find(d => d.id === record.device_type)?.label ?? record.device_type)}</small></span><span className="history-values">{record.readings.map(r => `${r.value} ${t(r.unit??'')}`).join(' · ')}</span><span><small>{record.measured_at ? t("Medición: {0}",date(record.measured_at)) : t("Registro: {0}",date(record.created_at))}</small>{record.is_demo && <b className="demo-tag">{t("Ficticio")}</b>}</span><ChevronRight size={17} /></button>)}</div>{selectedRecord && <Report record={selectedRecord} onAssistant={() => followUp(selectedRecord)} />}</> }</>}
      {!simulationBusy&&tab === 'assistant' && <Assistant initialSubject={assistantSubject} initialDemo={assistantDemo} onCapture={() => { setCaptureMode('live'); setTab('capture'); }} onReview={item=>void reviewAutomatic(item)} />}
      <footer className="workspace-footer"><span>{t("AURA SCAN · CAPTURA, CONFIRMACIÓN Y SEGUIMIENTO")}</span><span>{t("Uso experimental · Sin validación clínica")}</span></footer>
    </main></div></div>;
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><LanguageProvider><App /></LanguageProvider></React.StrictMode>);
