import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Activity, ArrowDownToLine, ArrowRight, Camera, Check, CheckCircle2, ChevronRight, ClipboardList, FileText, History, Info, LoaderCircle, Orbit, Plus, MessageCircle, ScanLine, ShieldCheck, Upload, X } from 'lucide-react';
import { request, ensureSession, resetSession } from './services/api';
import type { Capture, Device, Measurement } from './services/api';
import './styles.css';
import { Assistant } from './features/assessments/Assistant';

type Tab = 'capture' | 'history' | 'assistant';
const labels: Record<string, string> = { systolic: 'Presión sistólica', diastolic: 'Presión diastólica', pulse: 'Pulso', spo2: 'Saturación SpO₂', temperature: 'Temperatura', glucose: 'Glucosa' };
const date = (value: string) => new Date(value).toLocaleString('es-GT', { dateStyle: 'medium', timeStyle: 'short' });
const message = (e: unknown) => e instanceof Error ? e.message : 'No se pudo completar la operación.';

function Brand({ light = false }: { light?: boolean }) {
  return <div className={`brand ${light ? 'light' : ''}`}><span className="brand-icon"><Orbit size={29} strokeWidth={1.4} /></span><span>AURA<span className="brand-scan">SCAN</span></span></div>;
}

function Report({ record, onNew, onAssistant }: { record: Measurement; onNew?: () => void; onAssistant?: () => void }) {
  return <section className="report-panel"><div className="panel-title"><div><span className="eyebrow">REGISTRO CONFIRMADO</span><h2>Una lectura, con contexto.</h2></div><CheckCircle2 className="success-icon" size={32} /></div>
    {record.is_demo && <div className="notice">Demostración con datos ficticios. No corresponde a una medición real.</div>}
    <div className="record-meta"><span><small>ASTRONAUTA / ALIAS</small><strong>{record.subject_alias}</strong></span><span><small>CONFIRMACIÓN</small><strong>{date(record.created_at)}</strong></span></div>
    <div className="reading-grid">{record.readings.map(r => <div className="reading-card" key={r.code}><span>{labels[r.code]}</span><strong>{r.value}<small>{r.unit}</small></strong><small>{r.provenance === 'ocr_confirmed' ? 'OCR revisado y confirmado' : 'Introducido o corregido por el usuario'}</small></div>)}</div>
    <div className="report-section"><h3>Lo que sabemos de este registro</h3><ul>{record.assessment.findings.map((finding, i) => <li key={i}>{finding}</li>)}</ul></div>
    {record.assessment.trends.length > 0 && <div className="report-section"><h3>Diferencia frente al registro anterior</h3><div className="trend-row">{record.assessment.trends.map(t => <span key={t.code}>{labels[t.code]}: <b>{t.delta > 0 ? '+' : ''}{t.delta} {t.unit}</b></span>)}</div></div>}
    <div className="report-section"><h3>Siguientes comprobaciones</h3><ul>{record.assessment.next_steps.map((s, i) => <li key={i}>{s}</li>)}</ul></div>
    <p className="fine-print">{record.assessment.limitation}</p><div className="actions"><a className="button primary" href={`/api/measurements/${record.id}/report.pdf`}><ArrowDownToLine size={17} /> Descargar informe PDF</a>{onAssistant && <button className="button secondary" onClick={onAssistant}><MessageCircle size={17} /> Ver seguimiento y recomendaciones</button>}{onNew && <button className="button secondary" onClick={onNew}><Plus size={17} /> Nueva captura</button>}</div>
  </section>;
}

function CapturePage({ devices, onSaved, onFollowUp }: { devices: Device[]; onSaved: (m: Measurement) => void; onFollowUp: (m: Measurement) => void }) {
  const [capture, setCapture] = useState<Capture | null>(null);
  const [record, setRecord] = useState<Measurement | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState('auto');
  const [drafts, setDrafts] = useState<Record<string, { value: string; unit: string }>>({});
  const [live, setLive] = useState(false);
  const [cameraReady, setCameraReady] = useState(false);
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const [subject, setSubject] = useState('');
  const [symptoms, setSymptoms] = useState('');
  const [measuredAt, setMeasuredAt] = useState('');
  const [reviewed, setReviewed] = useState(false);
  const [declaredDemo, setDeclaredDemo] = useState(false);
  const device = devices.find(d => d.id === selected);
  useEffect(() => { if (live && video.current) video.current.srcObject = stream.current; }, [live]);
  useEffect(() => () => stream.current?.getTracks().forEach(t => t.stop()), []);
  function stopCamera() { stream.current?.getTracks().forEach(t => t.stop()); stream.current = null; setLive(false); setCameraReady(false); }
  async function startCamera() {
    setError('');
    if (!navigator.mediaDevices?.getUserMedia) { setError('La cámara necesita HTTPS o localhost y un navegador compatible. Puedes cargar una imagen.'); return; }
    try { stream.current = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' }, width: { ideal: 1600 } }, audio: false }); setLive(true); }
    catch { setError('No se pudo abrir la cámara. Revisa los permisos o carga una imagen.'); }
  }
  function applyCapture(result: Capture) {
    setCapture(result); setReviewed(false); setRecord(null);
    setSelected(devices.some(d => d.id === result.device_type) ? result.device_type : selected);
    setDrafts(Object.fromEntries(result.fields.map(f => [f.code, { value: String(f.value), unit: f.unit ?? '' }])));
    if (result.is_demo && !subject) setSubject('DEMO-01');
  }
  async function analyze(file?: File) {
    if (file && file.size > 8 * 1024 * 1024) { setError('La imagen debe pesar como máximo 8 MB.'); return; }
    setBusy(true); setError(''); stopCamera();
    try {
      if (!file) applyCapture(await request<Capture>('/captures/demo', { method: 'POST' }));
      else { const form = new FormData(); form.append('file', file); form.append('device_type', selected); form.append('is_demo', String(declaredDemo)); applyCapture(await request<Capture>('/captures', { method: 'POST', body: form })); }
    } catch (e) { setError(message(e)); } finally { setBusy(false); }
  }
  function takePhoto() {
    const v = video.current;
    if (!v?.videoWidth) return;
    const canvas = document.createElement('canvas'); const scale = Math.min(1, 1600 / Math.max(v.videoWidth, v.videoHeight));
    canvas.width = Math.round(v.videoWidth * scale); canvas.height = Math.round(v.videoHeight * scale);
    canvas.getContext('2d')!.drawImage(v, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(blob => { if (blob) void analyze(new File([blob], 'captura.jpg', { type: 'image/jpeg' })); }, 'image/jpeg', .92);
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
  function reset() { stopCamera(); setCapture(null); setRecord(null); setReviewed(false); setDrafts({}); setError(''); }
  const phase = record ? 3 : capture ? 2 : 1;
  return <><div className="page-heading"><div><span className="eyebrow">EVALUACIÓN / CAPTURA VISUAL</span><h1>Una captura.<br className="mobile-only" /> Un registro trazable.</h1><p>La cámara lee la pantalla. Tú confirmas qué se incorpora al historial.</p></div><span className="tag"><ScanLine size={14} /> OCR experimental</span></div>
    <div className="phase-bar">{['Captura del instrumento', 'Revisión de lecturas', 'Informe y seguimiento'].map((s, i) => <div className={phase === i + 1 ? 'active' : phase > i + 1 ? 'complete' : ''} key={s}><span>{phase > i + 1 ? <Check size={14} /> : `0${i + 1}`}</span>{s}{i < 2 && <ChevronRight size={16} />}</div>)}</div>
    {error && <div className="notice error" role="alert"><Info size={17} />{error}</div>}
    {record ? <Report record={record} onNew={reset} onAssistant={() => onFollowUp(record)} /> : <div className="capture-layout"><section className="capture-panel"><div className="panel-title compact"><div><h2>{capture ? 'Evidencia de la lectura' : 'Enfoca la pantalla'}</h2><p>{capture ? date(capture.created_at) : 'Buena luz, sin reflejos y con etiquetas visibles.'}</p></div><Camera size={20} /></div>
      <div className={`viewfinder ${capture ? 'has-image' : ''}`}>
        {live ? <video ref={video} autoPlay playsInline muted onLoadedMetadata={() => setCameraReady(true)} /> : capture ? <img src={capture.image_url} alt="Pantalla capturada del instrumento, para revisar los valores extraídos" /> : <><div className="scan-corners"><ScanLine size={62} strokeWidth={1} /><span>Coloca el instrumento<br />dentro del encuadre</span></div><div className="viewfinder-bottom"><span className="status-dot" /> CÁMARA EN ESPERA</div></>}
        {capture?.is_demo && <span className="demo-overlay">DATOS FICTICIOS</span>}{busy && <div className="processing" role="status"><LoaderCircle className="spin" size={34} /><strong>Procesando imagen</strong><span>Buscando dígitos, etiquetas y unidades…</span></div>}
      </div>
      <div className="capture-controls">{live ? <><button className="button primary" disabled={!cameraReady || busy} onClick={takePhoto}><Camera size={17} /> Tomar captura</button><button className="button secondary" onClick={stopCamera}>Cerrar cámara</button></> : <><button className="button primary" disabled={busy} onClick={startCamera}><Camera size={17} /> {capture ? 'Repetir con cámara' : 'Abrir cámara'}</button><button className="button secondary" disabled={busy} onClick={() => fileInput.current?.click()}><Upload size={17} /> Cargar imagen</button></>}</div>
      <input className="visually-hidden" ref={fileInput} type="file" accept="image/jpeg,image/png,image/webp" aria-label="Seleccionar imagen del instrumento" onChange={e => { const file = e.target.files?.[0]; e.target.value = ''; if (file) void analyze(file); }} />
      <div className="capture-note"><ShieldCheck size={17} /><span>PNG, JPG o WebP · Hasta 8 MB y 12 megapíxeles. La imagen queda vinculada al espacio de este navegador.</span></div>
      {!capture && <div className="demo-box"><div><strong>Explora antes de capturar</strong><p>Prueba el OCR con una pantalla generada y datos ficticios.</p></div><button className="text-button" disabled={busy} onClick={() => void analyze()}>Usar demostración <ArrowRight size={16} /></button></div>}
    </section>
    <section className="review-panel"><div className="panel-title compact"><div><span className="eyebrow">{capture ? 'PASO 02' : 'PREPARACIÓN'}</span><h2>{capture ? 'Revisa antes de guardar' : '¿Qué vas a registrar?'}</h2></div><ClipboardList size={22} /></div>
      <form onSubmit={confirm}><label>Tipo de instrumento<select value={selected} disabled={busy} onChange={e => { setSelected(e.target.value); setReviewed(false); }}><option value="auto">Identificar por etiquetas</option>{devices.map(d => <option value={d.id} key={d.id}>{d.label}</option>)}</select></label>
      {!capture ? <><label className="checkbox"><input type="checkbox" checked={declaredDemo} onChange={e => setDeclaredDemo(e.target.checked)} /> La imagen que cargaré contiene datos ficticios.</label><div className="empty-review"><Activity size={30} strokeWidth={1.2} /><h3>Las lecturas aparecerán aquí</h3><p>El reconocimiento usa etiquetas y unidades. Todavía no identifica modelos exactos ni utiliza un catálogo entrenado de dispositivos.</p></div><div className="supported"><span className="eyebrow">CATEGORÍAS PARA EXPLORAR</span>{devices.map(d => <span key={d.id}><Check size={13} /> {d.label}</span>)}</div></> : <>
        <div className="model-note"><Info size={15} /><span>Modelo exacto: <b>no identificado</b>. {capture.recognition === 'visible_labels' ? 'Categoría sugerida por etiquetas.' : 'Completa la revisión manual o repite la captura.'}</span></div>
        {capture.warnings.map((w, i) => <div className="notice small" key={i}>{w}</div>)}
        {device ? <div className="field-list">{device.indicators.map(indicator => { const draft = drafts[indicator.code] ?? { value: '', unit: '' }; const candidate = capture.fields.find(f => f.code === indicator.code); return <div className="field-row" key={indicator.code}><label>{indicator.label}{device.required.includes(indicator.code) && ' *'}<input aria-label={indicator.label} type="number" step="any" min={-1000} max={10000} required={device.required.includes(indicator.code)} value={draft.value} placeholder="Sin lectura" disabled={busy} onChange={e => { setDrafts({ ...drafts, [indicator.code]: { ...draft, value: e.target.value } }); setReviewed(false); }} /></label><label>Unidad<select aria-label={`Unidad de ${indicator.label}`} value={draft.unit} required={!!draft.value || device.required.includes(indicator.code)} disabled={busy} onChange={e => { setDrafts({ ...drafts, [indicator.code]: { ...draft, unit: e.target.value } }); setReviewed(false); }}><option value="">Selecciona</option>{indicator.units.map(u => <option key={u}>{u}</option>)}</select></label><small>{candidate ? `Lectura propuesta por OCR · Revisar con la imagen` : 'Campo sin extraer · Introducción manual'}</small></div>; })}</div> : <div className="notice">Selecciona un tipo de instrumento para completar los campos.</div>}
        <label>Alias del astronauta<input value={subject} onChange={e => { setSubject(e.target.value); setReviewed(false); }} maxLength={80} placeholder="ej. ASTRO-01" required disabled={busy} /></label>
        <label>Hora de la medición <small>(opcional, hora local)</small><input type="datetime-local" value={measuredAt} onChange={e => { setMeasuredAt(e.target.value); setReviewed(false); }} disabled={busy} /></label><p className="input-hint">Déjala vacía si solo conoces cuándo tomaste la fotografía.</p>
        <label>Síntomas y contexto <small>(opcional)</small><textarea value={symptoms} onChange={e => { setSymptoms(e.target.value); setReviewed(false); }} rows={3} maxLength={2000} placeholder="Cómo se siente, condiciones de la medición…" disabled={busy} /></label>
        <label className="checkbox"><input type="checkbox" checked={reviewed} onChange={e => setReviewed(e.target.checked)} required disabled={busy} /><span>Revisé los valores, las unidades y el modo de la pantalla. Confirmo a quién corresponde el registro.</span></label>
        <button className="button primary full" disabled={busy || !device || !reviewed}>{busy ? <LoaderCircle className="spin" size={17} /> : <CheckCircle2 size={17} />} Confirmar y generar informe</button>
      </>}</form>
    </section></div>}
  </>;
}

function App() {
  const [loading, setLoading] = useState(true);
  const [sessionGeneration, setSessionGeneration] = useState(0);
  const [bootError, setBootError] = useState('');
  const [tab, setTab] = useState<Tab>('capture');
  const [devices, setDevices] = useState<Device[]>([]);
  const [assistantSubject, setAssistantSubject] = useState('');
  const [assistantDemo, setAssistantDemo] = useState(false);
  const [records, setRecords] = useState<Measurement[]>([]);
  const [selectedRecord, setSelectedRecord] = useState<Measurement | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    const expired = () => { resetSession(); setLoading(true); setRecords([]); setSelectedRecord(null); setTab('capture'); setSessionGeneration(g => g + 1); };
    window.addEventListener('aura-session-expired', expired);
    return () => window.removeEventListener('aura-session-expired', expired);
  }, []);
  useEffect(() => {
    let active = true;
    setBootError('');
    void ensureSession().then(async () => {
      if (!active) return;
      const [d, h] = await Promise.all([request<{ devices: Device[] }>('/devices'), request<{ items: Measurement[] }>('/measurements')]);
      if (active) { setDevices(d.devices); setRecords(h.items); }
    }).catch(e => { if (active) setBootError(message(e)); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [sessionGeneration]);
  function followUp(record: Measurement) { setAssistantSubject(record.subject_alias); setAssistantDemo(record.is_demo); setTab('assistant'); }
  if (loading) return <div className="loading-screen"><Orbit size={40} className="slow-spin" /><span>Preparando el sistema…</span></div>;
  if (bootError) return <div className="loading-screen"><Info size={32} /><span>{bootError}</span><button className="button primary" onClick={() => { setLoading(true); setSessionGeneration(g => g + 1); }}>Reintentar</button></div>;
  return <div className="app-shell"><aside className="sidebar"><Brand light /><div className="mission-label"><span className="status-dot" /> SALUD DE MISIÓN</div><nav aria-label="Navegación principal">{([{ id: 'capture', name: 'Nueva evaluación', icon: ScanLine }, { id: 'history', name: 'Historial', icon: History }, { id: 'assistant', name: 'Asistente de salud', icon: MessageCircle }] as const).map(item => <button key={item.id} className={tab === item.id ? 'active' : ''} onClick={() => { setTab(item.id); setError(''); }}><item.icon size={19} />{item.name}{tab === item.id && <span className="nav-dot" />}</button>)}</nav><div className="sidebar-note"><Orbit size={30} strokeWidth={1} /><strong>La evidencia primero.</strong><p>Cada lectura conserva su procedencia y requiere tu confirmación.</p><span>SPACE APPS / 2026</span></div><div className="workspace-status"><ShieldCheck size={19} /><div><strong>Acceso directo</strong><small>Espacio de este navegador</small></div></div></aside>
    <div className="main-shell"><header className="topbar"><div><span>Centro de salud</span><ChevronRight size={14} /><strong>{tab === 'capture' ? 'Evaluación' : tab === 'history' ? 'Historial' : 'Asistente de salud'}</strong></div><span className="topbar-status"><span className="status-dot" /> Prototipo 0.3</span></header><main className="workspace">{error && <div className="notice error" role="alert">{error}<button aria-label="Cerrar aviso" onClick={() => setError('')}><X size={16} /></button></div>}
      {tab === 'capture' && <CapturePage devices={devices} onSaved={record => setRecords(previous => [record, ...previous])} onFollowUp={followUp} />}
      {tab === 'history' && <><div className="page-heading"><div><span className="eyebrow">CONTINUIDAD / EVIDENCIA</span><h1>El contexto se construye<br />lectura a lectura.</h1><p>{records.length} registros confirmados en este navegador.</p></div><button className="button primary" onClick={() => setTab('capture')}><Plus size={17} /> Nueva evaluación</button></div>{records.length === 0 ? <div className="empty-state"><History size={40} strokeWidth={1} /><h2>Tu historial empieza con una lectura.</h2><p>Las capturas pendientes no se añaden al informe hasta que las confirmes.</p><button className="button secondary" onClick={() => setTab('capture')}>Ir a captura <ArrowRight size={16} /></button></div> : <><div className="history-list">{records.map(record => <button className={selectedRecord?.id === record.id ? 'history-row selected' : 'history-row'} onClick={() => setSelectedRecord(record)} key={record.id}><span className="history-icon"><FileText size={20} /></span><span><strong>{record.subject_alias}</strong><small>{devices.find(d => d.id === record.device_type)?.label ?? record.device_type}</small></span><span className="history-values">{record.readings.map(r => `${r.value} ${r.unit}`).join(' · ')}</span><span><small>{date(record.created_at)}</small>{record.is_demo && <b className="demo-tag">Ficticio</b>}</span><ChevronRight size={17} /></button>)}</div>{selectedRecord && <Report record={selectedRecord} onAssistant={() => followUp(selectedRecord)} />}</> }</>}
      {tab === 'assistant' && <Assistant initialSubject={assistantSubject} initialDemo={assistantDemo} onCapture={() => setTab('capture')} />}
      <footer className="workspace-footer"><span>AURA SCAN · CAPTURA, CONFIRMACIÓN Y SEGUIMIENTO</span><span>Uso experimental · Sin validación clínica</span></footer>
    </main></div></div>;
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
