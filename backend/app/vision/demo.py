"""Synthetic display for testing the actual OCR, not a hardware validation dataset."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import io


def demo_image(kind='blood_pressure', values=None):
    image=Image.new('RGB',(1000,760),'#edf3f1')
    draw=ImageDraw.Draw(image)
    candidates=[Path('C:/Windows/Fonts/arial.ttf'),Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
    font_path=next((p for p in candidates if p.exists()),None)
    def font(size):
        return ImageFont.truetype(str(font_path),size) if font_path else ImageFont.load_default(size=size)
    draw.rounded_rectangle((65,50,935,690),radius=35,fill='#ffffff',outline='#567068',width=4)
    draw.rounded_rectangle((110,105,890,590),radius=14,fill='#d9e4d0')
    numbers=values or ([120,80,72] if kind=='blood_pressure' else [98,75])
    rows=[(150,'SYS',str(numbers[0])),(280,'DIA',str(numbers[1])),(410,'PUL',str(numbers[2]))] if kind=='blood_pressure' else [(180,'SpO2',str(numbers[0])),(360,'PR',str(numbers[1]))]
    for y,label,value in rows:
        draw.text((155,y+12),label,font=font(46),fill='#17251c')
        draw.text((455,y),value,font=font(86),fill='#17251c')
    draw.text((695,210),'mmHg' if kind=='blood_pressure' else '%',font=font(28),fill='#17251c')
    draw.text((170,620),'DEMO - DATOS FICTICIOS',font=font(30),fill='#876127')
    buf=io.BytesIO();image.save(buf,format='PNG')
    return buf.getvalue()
