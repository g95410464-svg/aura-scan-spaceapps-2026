from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from backend.app.devices.catalog import FIELDS, DEVICES
from backend.app.knowledge.sources import SOURCES
from backend.app.core.localization import translate


def render_report(measurement,capture,language='en'):
    tr=lambda value:translate(value,language)
    output=BytesIO()
    styles=getSampleStyleSheet()
    for candidate in ['C:/Windows/Fonts/segoeui.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
        if Path(candidate).exists():
            if 'AuraReport' not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont('AuraReport',candidate))
            for style in styles.byName.values():
                style.fontName='AuraReport'
            break
    for style in styles.byName.values():
        if hasattr(style,'fontSize'):
            style.leading=style.fontSize*1.45
    document=SimpleDocTemplate(output,pagesize=(595,842),rightMargin=44,leftMargin=44,topMargin=42,bottomMargin=48,
                               title=tr('AURA Scan - Informe de mediciones'),author='AURA Scan')
    story=[]
    def text(value,style='BodyText',localize=True):
        story.append(Paragraph(escape(tr(str(value)) if localize else str(value)),styles[style]));story.append(Spacer(1,8))
    text('AURA SCAN | Informe de mediciones','Title')
    text('DATOS FICTICIOS / DEMOSTRACIÓN' if measurement.is_demo else 'Datos aportados por el usuario; prototipo experimental.','Heading2')
    text(f'{tr("Astronauta (alias):")} {measurement.subject_alias}',localize=False)
    text(f'{tr("Instrumento:")} {tr(DEVICES[measurement.device_type]["label"])}. {tr("Modelo exacto: no identificado.")}',localize=False)
    text(f'{tr("Captura:")} {capture.created_at}',localize=False)
    text(f'{tr("Medición:")} {measurement.measured_at or tr("hora desconocida")}',localize=False)
    text(f'{tr("Confirmación:")} {measurement.created_at}',localize=False)
    rows=[[tr(v) for v in ['Indicador','Valor','Unidad','Procedencia']]]
    for r in measurement.readings:
        rows.append([tr(FIELDS[r['code']]['label']),str(r['value']),tr(r['unit']),
                     tr('OCR confirmado' if r['provenance']=='ocr_confirmed' else 'Simulación guionada' if r['provenance']=='simulation_scripted' else 'Revisado / introducido')])
    wrapped=[[Paragraph(escape(v),styles['BodyText']) for v in row] for row in rows]
    table=Table(wrapped,colWidths=[175,70,70,192],repeatRows=1,hAlign='LEFT')
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dceee8')),
                              ('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),9),
                              ('TOPPADDING',(0,0),(-1,-1),9),('LINEBELOW',(0,0),(-1,-1),.5,colors.HexColor('#d7e4df'))]))
    story.extend([table,Spacer(1,18)])
    text('Contexto y observaciones','Heading2')
    if measurement.symptoms:
        text(measurement.symptoms,localize=False)
    else:
        text('No se añadieron síntomas; no equivale a confirmar su ausencia.')
    for finding in measurement.assessment['findings']:
        text(finding)
    text('Siguientes comprobaciones','Heading2')
    for step in measurement.assessment['next_steps']:
        text(step)
    text(measurement.assessment['limitation'])
    text('Fuentes de contexto científico','Heading2')
    for source in SOURCES:
        story.append(Paragraph(f'<link href="{escape(source["url"])}" color="#087e86">{escape(source["organization"]+": "+tr(source["title"]))}</link>',styles['BodyText']))
        text(source['application'])
    text(f'{tr("Identificador:")} {measurement.id} | {tr("Reglas:")} {measurement.assessment["version"]}',localize=False)
    def footer(canv,doc):
        canv.setFont('Helvetica',8);canv.setFillColor(colors.HexColor('#526777'))
        canv.drawString(44,27,tr('AURA Scan - Seguimiento experimental, sin diagnóstico validado'))
        canv.drawRightString(551,27,f'{doc.page}')
    document.build(story,onFirstPage=footer,onLaterPages=footer)
    return output.getvalue()
