from typing import Literal
from pydantic import BaseModel, Field, HttpUrl

class TextRequest(BaseModel):
    text: str = Field(min_length=5,max_length=10000)

class LinkRequest(BaseModel):
    url: HttpUrl

class NewSource(BaseModel):
    name: str = Field(min_length=2,max_length=120)
    website: HttpUrl
    rss_url: HttpUrl | None = None
    category: Literal['media','institution','factcheck','other'] = 'other'
    trusted: bool = False

class DocumentImport(BaseModel):
    source_id: str
    url: HttpUrl
    title: str = Field(min_length=3,max_length=400)
    content: str = Field(min_length=80,max_length=80000)
    published_at: str | None = None

class UrlImport(BaseModel):
    source_id: str
    url: HttpUrl
