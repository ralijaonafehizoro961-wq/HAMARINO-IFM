from io import BytesIO
from fastapi import HTTPException
from PIL import Image,ImageOps,ImageEnhance,UnidentifiedImageError
from pypdf import PdfReader
import pytesseract

ALLOWED={'image/jpeg','image/png','image/webp','application/pdf'}


def read_media(data: bytes, media_type: str):
    if media_type not in ALLOWED:
        raise HTTPException(415,'Formats acceptés : JPG, PNG, WEBP ou PDF texte.')
    if media_type=='application/pdf':
        try:
            pdf=PdfReader(BytesIO(data))
            text='\n'.join((p.extract_text() or '') for p in pdf.pages[:10]).strip()
        except Exception as exc:
            raise HTTPException(422,'PDF illisible.') from exc
        if not text:
            raise HTTPException(422,'PDF scanné sans texte. Convertissez sa page en image JPG/PNG pour OCR.')
        return text[:10000],'pdf_text'
    try:
        im=Image.open(BytesIO(data))
        im.verify()
        im=Image.open(BytesIO(data))
        im=ImageOps.exif_transpose(im).convert('L')
        if im.width*im.height>25_000_000:
            raise HTTPException(413,'Image trop grande (limite 25 MP).')
        im=ImageEnhance.Contrast(im).enhance(1.65)
        if im.width<1100:
            im=im.resize((max(1100,im.width*2),int(im.height*max(1100,im.width*2)/im.width)))
    except (UnidentifiedImageError,OSError,ValueError,ZeroDivisionError) as exc:
        raise HTTPException(422,'Image illisible.') from exc
    try:
        installed=set(pytesseract.get_languages(config=''))
        langs='+'.join(lang for lang in ('fra','eng','mlg') if lang in installed)
        if not langs:
            raise HTTPException(503,'Tesseract : aucun pack de langue installé.')
        text=pytesseract.image_to_string(im,lang=langs,config='--psm 3',timeout=20).strip()
    except (pytesseract.TesseractNotFoundError,RuntimeError) as exc:
        raise HTTPException(503,'Tesseract indisponible ou OCR trop long. Vérifiez son installation.') from exc
    if len(text)<5:
        raise HTTPException(422,'Aucun texte suffisamment lisible trouvé dans l’image.')
    return text[:10000],'ocr_tesseract'
