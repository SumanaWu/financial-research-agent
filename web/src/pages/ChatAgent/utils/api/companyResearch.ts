import { api } from '@/api/client';
export async function resolveResearchCompany(symbol: string, identity: string) {
  const { data } = await api.post<{ candidates: { cik: string; name: string; ticker: string }[] }>('/api/v1/company-research/resolve', { symbol, identity });
  return data.candidates;
}
export interface ResearchDelivery {
  state: 'pending' | 'partial' | 'blocked' | 'invalid';
  root: string;
  spec: { cik: string; as_of: string };
  gaps?: string[];
  errors?: string[];
  files?: string[];
}
export async function getResearchDelivery(threadId: string): Promise<ResearchDelivery | null> {
  try {
    const { data } = await api.get<ResearchDelivery>(`/api/v1/threads/${threadId}/company-research`);
    return data;
  } catch (error) {
    if (typeof error === 'object' && error !== null && 'response' in error && (error.response as { status?: number })?.status === 404) return null;
    throw error;
  }
}
