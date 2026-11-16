import { ArrowDownToLine, ArrowRight, CheckCircle2, LoaderCircle, Play, X } from 'lucide-react';
import type { Measurement, Field } from '../../services/api';

export type SimulationResult = { id:string; subject_alias:string; is_demo:true; screens:{title:string;image_url:string;readings:Field[];record_id:string}[]; records:Measurement[]; report_id:string; notice:string };
const steps=[['Lecturas','3 lecturas listas.'],['Historial','Compara tus registros.'],['Asistente','Revisa el siguiente paso.'],['Informe','Descarga tu informe.']];

export function SimulationCoach({ result, step, busy, onNext, onClose }: {result:SimulationResult|null;step:number;busy:boolean;onNext:()=>void;onClose:()=>void}) {
  return <section className="simulation-coach" aria-label="Recorrido guiado de simulación"><div className="simulation-coach-top"><span><Play size={14}/> SIMULACIÓN · DATOS FICTICIOS</span><button aria-label="Cerrar simulación guiada" onClick={onClose}><X size={17}/></button></div>{busy?<div className="simulation-wait" role="status"><LoaderCircle className="spin" size={23}/><div><strong>Preparando simulación…</strong></div></div>:result&&<><div className="simulation-step-track">{steps.map((s,i)=><span className={i===step?'active':i<step?'done':''} key={s[0]}><b>{i<step?'✓':i+1}</b>{s[0]}</span>)}</div><div className="simulation-instructions"><div><h2>{steps[step][0]}</h2><p>{steps[step][1]}</p><small>{result.subject_alias}</small></div><button className="button primary" onClick={onNext}>{step===3?'Volver a cámara':`Siguiente: ${['Historial','Asistente','Informe'][step]}`}<ArrowRight size={15}/></button></div></>}</section>;
}

export function SimulationReadings({ result }: {result:SimulationResult}) {
  const labels:Record<string,string>={systolic:'Sistólica',diastolic:'Diastólica',pulse:'Pulso',spo2:'SpO₂'};
  return <section className="simulation-stage"><div className="page-heading"><div><span className="eyebrow">LECTURAS DE PRUEBA</span><h1>Lecturas listas</h1></div></div><div className="simulation-screen-grid">{result.screens.map((s,i)=><article key={s.record_id}><div className="simulation-screen-title"><span>0{i+1}</span><h2>{s.title}</h2><CheckCircle2 size={17}/></div><img src={s.image_url} alt={`Pantalla ficticia de ${s.title}`}/><dl>{s.readings.map(r=><div key={r.code}><dt>{labels[r.code]??r.code}</dt><dd>{r.value}<small>{r.unit}</small></dd></div>)}</dl></article>)}</div><details className="compact-details simulation-disclosure"><summary>Sobre esta simulación</summary><p>{result.notice} OCR real sobre pantallas sintéticas. Los registros son guionados; no hay revisión clínica.</p></details></section>;
}

export function SimulationReport({ result, onAssistant }: {result:SimulationResult;onAssistant:()=>void}) {
  return <section className="simulation-report"><CheckCircle2 size={40}/><h1>Informe listo</h1><p>Segunda lectura de presión y sus fuentes.</p><div className="actions"><a className="button primary" href={`/api/measurements/${result.report_id}/report.pdf`}><ArrowDownToLine size={17}/> Descargar PDF</a><button className="button secondary" onClick={onAssistant}>Ver acciones <ArrowRight size={16}/></button></div><small>Simulación · Datos ficticios</small></section>;
}
