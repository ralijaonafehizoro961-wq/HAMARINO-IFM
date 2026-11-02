export type Verdict = 'a_verifier' | 'corrobore' | 'contredit';
export type Evidence = {
  document_id: string;
  title: string;
  source_name: string;
  url: string;
  published_at?: string | null;
  retrieved_at: string;
  passage: string;
  relevance: number;
  trusted: boolean;
};
export type Factcheck = {
  claim: string; publisher: string; url: string; rating: string;
  status: Verdict; review_date?: string | null;
};
export type Verification = {
  id: string; input_type: 'text' | 'link' | 'media'; input_url?: string | null;
  original_text: string; extracted_text?: string | null;
  ocr_method?: string; claim: string; extraction_method: string;
  verdict: Verdict; summary: string;
  evidence: Evidence[]; factchecks: Factcheck[];
  warning: string; next_steps: string[]; created_at: string;
};
export type HistoryItem = {
  id: string; input_type: string; verdict: Verdict;
  summary: string; excerpt: string; created_at: string;
};
export type Source = {
  id: string; name: string; website: string; rss_url: string | null;
  category: string; trusted: number;
};
export type SelectedImage = {uri: string; fileName?: string | null; mimeType?: string | null};
