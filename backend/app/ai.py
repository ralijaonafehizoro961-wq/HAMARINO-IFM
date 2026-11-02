"""OpenAI OPTIONNEL uniquement pour identifier une affirmation, jamais pour inventer des sources."""
import re
from .config import settings


def heuristic_claim(text):
    sentences=re.split(r'(?<=[.!?])\s+|\n+',text.strip())
    viable=[s.strip() for s in sentences if len(s.strip())>=20]
    return (viable[0] if viable else text.strip())[:550]


async def extract_claim(text):
    if not settings().openai_api_key:
        return heuristic_claim(text),'heuristic_local'
    try:
        from openai import AsyncOpenAI
        client=AsyncOpenAI(api_key=settings().openai_api_key,timeout=10,max_retries=0)
        response=await client.responses.create(model=settings().openai_model,
          instructions=('Extrais UNE seule affirmation factuelle et vérifiable depuis le texte. '
             'N’ajoute aucune information. Ignore les opinions. Réponds seulement avec la phrase extraite, '
             'ou INDETERMINABLE si aucune affirmation.'),
          input=text[:4500],max_output_tokens=160)
        result=response.output_text.strip()[:550]
        if result and result.upper()!='INDETERMINABLE':return result,'openai_claim_extraction'
    except Exception:
        pass
    return heuristic_claim(text),'heuristic_local_fallback'
