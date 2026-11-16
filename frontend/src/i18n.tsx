import { createContext, useContext, useEffect, useState } from 'react';
import { Languages } from 'lucide-react';
import english from '../../shared/i18n/en.json';
import templates from '../../shared/i18n/templates.json';

export type Language = 'en' | 'es';
const storageKey = 'aura-language';
function initialLanguage():Language {
  try { return localStorage.getItem(storageKey)==='es'?'es':'en'; } catch { return 'en'; }
}
let activeLanguage = initialLanguage();
const dictionary:Record<string,string> = english;
const reverse = Object.fromEntries(Object.entries(dictionary).map(([es,en])=>[en,es]));
const escapeRegex = (value:string) => value.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
const patterns = templates.map(({es,en,...options})=>({
  es,en,
  translate:options.translate??[],
  match:new RegExp('^'+es.split(/(\{\d+\})/).map(part=>/^\{\d+\}$/.test(part)?'(.+?)':escapeRegex(part)).join('')+'$'),
}));
export const locale = () => activeLanguage==='en'?'en-US':'es-GT';
export const language = () => activeLanguage;
function translateCapture(value:string):string {
  const translated=t(value);
  if(translated!==value)return translated;
  return value.replace(/Presión sistólica|Presión diastólica|Saturación SpO2|Pulso|Temperatura|Glucosa|lpm|Dolor o presión intensa en el pecho|Dificultad importante para respirar|Desmayo o confusión nueva/g,part=>dictionary[part]??part);
}
export function t(source:string,...values:unknown[]):string {
  let translated=activeLanguage==='es'?(reverse[source]??source):(dictionary[source]??templates.find(item=>item.es===source)?.en??source);
  if(activeLanguage==='en'&&translated===source) {
    if(source.startsWith('Value error, '))return 'Invalid value: '+t(source.slice(13));
    for(const pattern of patterns){const match=source.match(pattern.match);if(match){translated=pattern.en.replace(/\{(\d+)\}/g,(_,index)=>{const value=match[Number(index)+1]??'';return pattern.translate.includes(Number(index))?translateCapture(value):value;});break;}}
  }
  return translated.replace(/\{(\d+)\}/g,(_,index)=>String(values[Number(index)]??`{${index}}`));
}
export const reportUrl = (id:string) => `/api/measurements/${encodeURIComponent(id)}/report.pdf?lang=${activeLanguage}`;
const LanguageContext=createContext({language:activeLanguage,setLanguage:(_:Language)=>{}});
export function LanguageProvider({children}:{children:React.ReactNode}) {
  const [selected,setSelected]=useState(activeLanguage);
  function setLanguage(value:Language){activeLanguage=value;setSelected(value);try{localStorage.setItem(storageKey,value);}catch{/* The language still works when storage is unavailable. */}}
  useEffect(()=>{
    document.documentElement.lang=selected;
    document.title=selected==='en'?'AURA Scan | Mission health':'AURA Scan | Salud de misión';
    document.querySelector('meta[name="description"]')?.setAttribute('content',selected==='en'?'Live device readings, health history and sourced guidance for space missions.':'Lecturas en vivo, historial y orientación con fuentes para misiones espaciales.');
  },[selected]);
  return <LanguageContext.Provider value={{language:selected,setLanguage}}>{children}</LanguageContext.Provider>;
}
export const useLanguage = () => useContext(LanguageContext);
export function LanguageSwitcher(){
  const {language:selected,setLanguage}=useLanguage();
  return <label className="language-switch"><Languages size={15} aria-hidden="true"/><select aria-label={t('Idioma')} value={selected} onChange={event=>setLanguage(event.target.value as Language)}><option value="en">English</option><option value="es">Español</option></select></label>;
}
