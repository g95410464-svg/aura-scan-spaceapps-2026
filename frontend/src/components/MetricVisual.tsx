import { Activity, Droplets, HeartPulse, Thermometer, Wind } from 'lucide-react';

export function MetricIcon({code}:{code:string}) {
  const Icon=code==='pulse'?HeartPulse:code==='spo2'?Wind:code==='temperature'?Thermometer:code==='glucose'?Droplets:Activity;
  return <Icon size={21} strokeWidth={1.7} aria-hidden="true"/>;
}

export function MetricPlot({values,label}:{values:number[];label:string}) {
  const samples=values.filter(Number.isFinite).slice(-12);
  if(samples.length<2)return null;
  const low=Math.min(0,...samples), high=Math.max(1,...samples)*1.1;
  const points=samples.map((value,index)=>[8+index*184/(samples.length-1),51-(value-low)/(high-low)*40]);
  const line=points.map(point=>point.join(',')).join(' ');
  return <div className="metric-plot"><svg viewBox="0 0 200 58" role="img" aria-label={`${label}: ${samples.join(', ')}`}>
    <path className="plot-grid" d="M8 16H192 M8 34H192 M8 51H192"/>
    <polygon className="plot-area" points={`8,51 ${line} 192,51`}/>
    <polyline className="plot-line" points={line}/>
    {points.map(([cx,cy],index)=><circle className="plot-point" key={index} cx={cx} cy={cy} r={index===points.length-1?3.5:2.5}/>)}
  </svg><div className="plot-values"><span>{samples[0]}</span><span>{samples[samples.length-1]}</span></div></div>;
}
