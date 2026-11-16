"""Experimental, label-based extraction. No exact-device classifier is trained."""
import io
import re
import threading
import warnings
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

Image.MAX_IMAGE_PIXELS = 12_000_000
_engine = None
_lock = threading.Lock()


class ImageRejected(ValueError):
    pass


def sanitize_image(content: bytes, max_dimension: int = 1600) -> bytes:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as original:
                if original.format not in {'PNG', 'JPEG', 'WEBP'}:
                    raise ImageRejected('Usa una imagen PNG, JPEG o WebP.')
                if original.width * original.height > 12_000_000 or min(original.size) < 64:
                    raise ImageRejected('La imagen debe tener al menos 64 px por lado y como máximo 12 megapíxeles.')
                image = ImageOps.exif_transpose(original).convert('RGB')
                image.thumbnail((max_dimension, max_dimension))
                output = io.BytesIO()
                image.save(output, format='PNG')
                return output.getvalue()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ImageRejected('La imagen no es válida o excede el tamaño permitido.') from exc


def _norm(s):
    return re.sub(r'[^A-Z0-9%°/]', '', s.upper()).replace('SPOZ', 'SPO2')


def parse_tokens(tokens: list[dict], selected_type: str = 'auto') -> dict:
    """Associate only explicit labels and units, never just digit order or appearance."""
    aliases = {'systolic': {'SYS', 'SYSTOLIC'}, 'diastolic': {'DIA', 'DIASTOLIC'},
               'pulse': {'PUL', 'PULSE', 'PR', 'BPM', 'PRBPM', 'HR', 'HEARTRATE'}, 'spo2': {'SPO2', 'SPO2%', '%SPO2', 'SP02', 'SP02%'}}
    fields = {}
    problems = []
    full = ' '.join(t['text'] for t in tokens)
    unit_pressure = bool(re.search(r'MM\s*HG', full, re.I))
    for code, names in aliases.items():
        anchors = [t for t in tokens if _norm(t['text']) in names]
        candidates = []
        for anchor in anchors:
            for number in tokens:
                if not re.fullmatch(r'\d{1,3}(?:[.,]\d{1,2})?', number['text'].strip()):
                    continue
                # A value must share the label's row and be to its right (or adjacent left).
                ah = max(anchor['h'], number['h'], 1)
                dy = abs(number['y'] - anchor['y'])
                dx = number['x'] - anchor['x']
                if dy <= ah * .65 and (0 < dx < 650 or -160 < dx < 0):
                    candidates.append((dy * 4 + abs(dx), number, anchor))
            # Combined OCR strings such as SYS 120.
            match = re.fullmatch(r'(?:SYS|DIA|PUL|PULSE|PR|BPM|SPO2)\s*[:%]?\s*(\d{1,3}(?:[.,]\d{1,2})?)', anchor['text'].upper())
            if match:
                candidates.append((0, {**anchor, 'text': match.group(1)}, anchor))
        # Accommodate combined label/value boxes without pretending they are exact models.
        for token in tokens:
            for name in names:
                match = re.fullmatch(re.escape(name)+r'\s*[:%]?\s*(\d{1,3}(?:[.,]\d{1,2})?)(?:\s*(?:MMHG|BPM|LPM|%))?', token['text'].upper())
                if match:
                    candidates.append((0, {**token, 'text': match.group(1)}, token))
        if candidates:
            candidates.sort(key=lambda x: x[0])
            values = {float(v[1]['text'].replace(',', '.')) for v in candidates}
            # Multiple competing readings are not resolved by a normal-value guess.
            best = candidates[0]
            if len(values) > 1 and len(candidates) > 1 and candidates[1][0] - best[0] < 45:
                problems.append(f'Hay varios valores posibles para {code}; revisa la imagen.')
                continue
            unit = 'mmHg' if code in {'systolic','diastolic'} and unit_pressure else 'lpm' if code == 'pulse' else '%' if code == 'spo2' and '%' in full else None
            fields[code] = {'code':code, 'value':float(best[1]['text'].replace(',', '.')), 'unit':unit,
                            'confidence':round(min(best[1]['confidence'], best[2]['confidence']), 3), 'evidence':best[1]['text']}
    # Temperature/glucose require visible units. Do not infer an absent decimal.
    patterns = [('temperature', r'(\d{1,3}[.,]\d{1,2})\s*°?\s*([CF])\b'),
                ('glucose', r'(\d{1,3}(?:[.,]\d{1,2})?)\s*(MG\s*/\s*DL|MMOL\s*/\s*L)\b')]
    ordered = sorted(tokens, key=lambda t: (round(t['y']/max(t['h'],15)), t['x']))
    for code, pattern in patterns:
        # Join only close boxes on the same row, not arbitrary text from separate rows.
        for token in ordered:
            neighbors = [t for t in ordered if abs(t['y']-token['y']) <= max(t['h'],token['h'])*.65 and -5 <= t['x']-token['x'] < 420]
            text = ' '.join(t['text'] for t in sorted(neighbors,key=lambda t:t['x']))
            match = re.search(pattern, text.upper())
            if match:
                u=match.group(2).replace(' ', '')
                unit=('°'+u) if code=='temperature' else 'mg/dL' if u=='MG/DL' else 'mmol/L'
                fields[code]={'code':code,'value':float(match.group(1).replace(',','.')),'unit':unit,
                              'confidence':round(min(t['confidence'] for t in neighbors),3),'evidence':match.group(0)}
                break
    inferred = ('blood_pressure' if {'systolic','diastolic'} & fields.keys() else
                'oximeter' if 'spo2' in fields else 'thermometer' if 'temperature' in fields else
                'glucometer' if 'glucose' in fields else 'unknown')
    compatible_watch = selected_type == 'smartwatch' and set(fields).issubset({'pulse','spo2'})
    if selected_type != 'auto' and inferred not in {'unknown', selected_type} and not compatible_watch:
        problems.append('La categoría seleccionada no coincide con las etiquetas detectadas. Revisa todos los campos.')
    device_type = inferred if selected_type == 'auto' else selected_type
    if re.search(r'\b(ERR(?:OR)?|E[- ]?\d|MEM(?:ORY)?|AVG)\b', full.upper()):
        problems.append('Posible pantalla de error, memoria o promedio; comprueba el modo y la fecha de medición.')
    if any(f['unit'] is None for f in fields.values()):
        problems.append('Falta una unidad visible: debes seleccionarla explícitamente antes de confirmar.')
    if not fields:
        problems.append('No se pudieron asociar lecturas con etiquetas o unidades. Repite o completa la revisión manualmente.')
    if selected_type == 'smartwatch':
        problems.append('Reloj declarado manualmente: el OCR no verifica su modelo ni precisión clínica. Confirma que son valores actuales, no objetivos o promedios.')
    return {'device_type':device_type, 'device_model':None, 'recognition':'visible_labels' if fields else 'unresolved',
            'fields':list(fields.values()), 'warnings':problems, 'tokens':tokens,
            'clinical_confidence':None, 'engine':'RapidOCR / ONNX', 'version':'0.1.0'}


def analyze_image(path: Path, selected_type: str = 'auto') -> dict:
    return analyze_bytes(path.read_bytes(), selected_type)


def analyze_bytes(content: bytes, selected_type: str = 'auto') -> dict:
    global _engine
    image=cv2.imdecode(np.frombuffer(content,dtype=np.uint8),cv2.IMREAD_COLOR)
    gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    def recognize(candidate):
        output,_=_engine(candidate)
        tokens=[]
        # Normalize geometry for the parser so higher resolution does not break label distances.
        scale=1000/max(candidate.shape[:2])
        for points,text,confidence in output or []:
            xy=np.array(points)
            tokens.append({'text':text,'confidence':float(confidence),'x':float(xy[:,0].mean())*scale,
                           'y':float(xy[:,1].mean())*scale,'h':float(xy[:,1].max()-xy[:,1].min())*scale,'box':xy.tolist()})
        return parse_tokens(tokens,selected_type)
    def score(candidate):
        return sum(1 for f in candidate['fields'] if f['unit'] is not None and f.get('confidence',0)>=.9)
    variant='original'
    with _lock:
        if _engine is None:
            from rapidocr_onnxruntime import RapidOCR
            _engine=RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1)
        result=recognize(image)
        # A second pass helps uneven lighting. It never fabricates obscured digits.
        from backend.app.devices.catalog import DEVICES
        required=DEVICES.get(result['device_type'],{}).get('required',[])
        usable={f['code'] for f in result['fields'] if f['unit'] is not None and f.get('confidence',0)>=.9}
        if not required or not set(required).issubset(usable):
            enhanced=cv2.createCLAHE(clipLimit=2.0,tileGridSize=(8,8)).apply(gray)
            if float(np.median(enhanced))<110:
                enhanced=cv2.bitwise_not(enhanced)
            enhanced=cv2.cvtColor(enhanced,cv2.COLOR_GRAY2BGR)
            alternative=recognize(enhanced)
            high_original={f['code']:f for f in result['fields'] if f.get('confidence',0)>=.9 and f['unit'] is not None}
            conflicts=any(f['code'] in high_original and f.get('confidence',0)>=.9 and f['unit']==high_original[f['code']]['unit']
                          and abs(f['value']-high_original[f['code']]['value'])>{'pulse':2,'spo2':1}.get(f['code'],0) for f in alternative['fields'])
            if score(alternative)>score(result):result=alternative;variant='local_contrast'
            if conflicts:
                result['recognition']='ambiguous'
                result['warnings'].append('Las dos versiones de la imagen dan valores distintos. Cambia el ángulo o el encuadre; no se guardará esta lectura.')
    result['quality']={'sharpness':round(float(cv2.Laplacian(gray,cv2.CV_64F).var()),1),
                       'brightness':round(float(gray.mean()),1),'width':image.shape[1],'height':image.shape[0],
                       'bright_fraction':round(float((gray>248).mean()),3),'contrast':round(float(np.percentile(gray,95)-np.percentile(gray,5)),1)}
    result['preprocessing']=variant
    if result['quality']['sharpness']<20:
        result['warnings'].append('La imagen puede estar desenfocada. El criterio es experimental.')
    if result['quality']['bright_fraction']>.15 and result['recognition']!='visible_labels':
        result['warnings'].append('Hay zonas muy brillantes: inclina ligeramente el dispositivo o la cámara para apartar el reflejo de los números.')
    return result
