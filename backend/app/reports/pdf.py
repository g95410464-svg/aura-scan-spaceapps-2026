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


def render_report(measurement,capture):
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
                               title='AURA Scan - Informe de mediciones',author='AURA Scan')
    story=[]
    def text(value,style='BodyText'):
        story.append(Paragraph(escape(str(value)),styles[style]));story.append(Spacer(1,8))
    text('AURA SCAN | Informe de mediciones','Title')
    text('DATOS FICTICIOS / DEMOSTRACIÓN' if measurement.is_demo else 'Datos aportados por el usuario; prototipo experimental.','Heading2')
    text(f'Astronauta (alias): {measurement.subject_alias}')
    text(f'Instrumento: {DEVICES[measurement.device_type]["label"]}. Modelo exacto: no identificado.')
    text(f'Captura: {capture.created_at}')
    text(f'Medición: {measurement.measured_at or "hora desconocida"}')
    text(f'Confirmación: {measurement.created_at}')
    rows=[['Indicador','Valor','Unidad','Procedencia']]
    for r in measurement.readings:
        rows.append([FIELDS[r['code']]['label'],str(r['value']),r['unit'],
                     'OCR confirmado' if r['provenance']=='ocr_confirmed' else 'Revisado / introducido'])
    wrapped=[[Paragraph(escape(v),styles['BodyText']) for v in row] for row in rows]
    table=Table(wrapped,colWidths=[175,70,70,192],repeatRows=1,hAlign='LEFT')
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dceee8')),
                              ('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),9),
                              ('TOPPADDING',(0,0),(-1,-1),9),('LINEBELOW',(0,0),(-1,-1),.5,colors.HexColor('#d7e4df'))]))
    story.extend([table,Spacer(1,18)])
    text('Contexto y observaciones','Heading2')
    text(measurement.symptoms or 'No se añadieron síntomas; no equivale a confirmar su ausencia.')
    for finding in measurement.assessment['findings']:
        text(finding)
    text('Siguientes comprobaciones','Heading2')
    for step in measurement.assessment['next_steps']:
        text(step)
    text(measurement.assessment['limitation'])
    text('Fuentes de contexto científico','Heading2')
    for source in SOURCES:
        story.append(Paragraph(f'<link href="{escape(source["url"])}" color="#087e86">{escape(source["organization"]+": "+source["title"])}</link>',styles['BodyText']))
        text(source['application'])
    text(f'Identificador: {measurement.id} | Reglas: {measurement.assessment["version"]}')
    def footer(canv,doc):
        canv.setFont('Helvetica',8);canv.setFillColor(colors.HexColor('#526777'))
        canv.drawString(44,27,'AURA Scan - Seguimiento experimental, sin diagnóstico validado')
        canv.drawRightString(551,27,f'{doc.page}')
    document.build(story,onFirstPage=footer,onLaterPages=footer)
    return output.getvalue()
