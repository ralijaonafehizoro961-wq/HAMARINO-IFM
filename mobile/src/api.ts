import type {SelectedImage, Verification, HistoryItem, Source} from './types';

function root(url: string) {
  const base = url.trim().replace(/\/+$/, '');
  if (!/^https?:\/\/[^/]+/i.test(base)) {
    throw new Error('Adresse API invalide. Exemple : http://192.168.1.42:8000');
  }
  return base;
}

async function request<T>(base: string, path: string, init?: RequestInit): Promise<T> {
  const control = new AbortController();
  const timeout = setTimeout(() => control.abort(), 35000);
  try {
    const response = await fetch(`${root(base)}${path}`, {...init,signal:control.signal});
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = data?.detail;
      throw new Error(typeof detail === 'string' ? detail : `Erreur serveur ${response.status}`);
    }
    return data as T;
  } catch (error: any) {
    if (error?.name === 'AbortError') throw new Error('Connexion trop lente ou serveur inaccessible.');
    if (/Network request failed|Failed to fetch/i.test(String(error?.message))) {
      throw new Error('Serveur inaccessible. Vérifiez IP, Wi-Fi commun et pare-feu Fedora.');
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}
export async function testBackend(base: string) {
  return request<{ok:boolean;service:string;ocr:string}>(base,'/api/health');
}
export async function verifyText(base: string,text: string) {
  return request<Verification>(base,'/api/verify/text',{
    method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})
  });
}
export async function verifyLink(base: string,url: string) {
  return request<Verification>(base,'/api/verify/link',{
    method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})
  });
}
export async function verifyImage(base: string, asset:SelectedImage) {
  const data = new FormData();
  const name = asset.fileName || 'photo.jpg';
  data.append('file',{uri:asset.uri,name,type:asset.mimeType || 'image/jpeg'} as any);
  return request<Verification>(base,'/api/verify/media',{
    method:'POST',body:data
    // NE PAS définir Content-Type ici : RN ajoute automatiquement la frontière multipart.
  });
}
export async function getHistory(base:string) {
  return request<{items:HistoryItem[]}>(base,'/api/history');
}
export async function getVerification(base:string,id:string) {
  return request<Verification>(base,`/api/verifications/${encodeURIComponent(id)}`);
}
export async function getSources(base:string) {
  return request<{sources:Source[];documents_count:number}>(base,'/api/sources');
}
