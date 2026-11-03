from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from .news_db import get_news

COLORS={'Politique':'#1669A4','Économie':'#1D89BF','Sport':'#00A386','Santé':'#B66D22','Éducation':'#4A7BB9','Société':'#7B75BB','Transport':'#1D89BF','Faits divers':'#7B75BB'}

def cover(nid):
    article=get_news(nid)
    if article is None:return None
    color=COLORS.get(article['category'],'#1D89BF')
    im=Image.new('RGB',(800,480),'#F2F8FB')
    draw=ImageDraw.Draw(im)
    draw.rounded_rectangle((35,35,765,445),radius=38,fill='#FFFFFF')
    draw.ellipse((510,-90,930,330),fill='#D7EBF6')
    draw.ellipse((590,160,870,440),fill='#B7DCEB')
    draw.rounded_rectangle((70,75,310,119),radius=16,fill=color)
    draw.text((88,85),article['source_name'][:26],fill='white')
    draw.text((75,170),'HAMARINO',fill=color,stroke_width=0)
    words=article['title'].split()
    lines=[];line=''
    for word in words:
        if len(line)+len(word)>35:
            lines.append(line.strip());line=''
        line+=word+' '
        if len(lines)>2:break
    if line and len(lines)<3:lines.append(line.strip())
    for i,text in enumerate(lines):draw.text((75,225+i*35),text,fill='#173447')
    draw.text((75,401),'ILLUSTRATION • image de presse non disponible',fill='#718699')
    out=BytesIO();im.save(out,'PNG');return out.getvalue()
