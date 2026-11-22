import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useState } from 'react';
import { queryKeys } from '@/lib/queryKeys';
import { getResearchDelivery } from '../utils/api/companyResearch';
import { triggerFileDownload } from '../utils/api/files';

export default function CompanyResearchResult({ threadId, workspaceId }: { threadId: string; workspaceId: string }) {
  const { t } = useTranslation();
  const [feedback, setFeedback] = useState<{ threadId: string; status: 'checking' | 'done' | 'error' } | null>(null);
  const query = useQuery({
    queryKey: queryKeys.companyResearch.detail(threadId),
    queryFn: () => getResearchDelivery(threadId),
    enabled: Boolean(threadId && threadId !== '__default__'),
    refetchInterval: q => q.state.data?.state === 'pending' ? 10000 : false,
    retry: false,
  });
  const data = query.data;
  const status = feedback?.threadId === threadId ? feedback.status : null;
  const recheck = async () => {
    setFeedback({ threadId, status: 'checking' });
    const result = await query.refetch();
    setFeedback({ threadId, status: result.isError || !result.data ? 'error' : 'done' });
  };
  const button = <button type="button" disabled={query.isFetching || status === 'checking'} className="inline-flex items-center rounded-full bg-(--color-text-primary) px-3 py-1.5 text-xs font-medium text-(--color-bg-page) transition-opacity hover:opacity-80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50" onClick={() => { void recheck(); }}>{t(status === 'checking' ? 'companyResearch.checking' : 'companyResearch.refresh')}</button>;
  if (!data) return query.isError ? <div><p role="alert">{t('companyResearch.checkError')}</p>{button}</div> : null;
  return <section className="my-4 rounded-xl border bg-card p-4 space-y-2" aria-label={t('companyResearch.title')}>
    <p>CIK {data.spec.cik} · {data.spec.as_of} · {t(`companyResearch.${data.state}`)}</p>
    {(data.errors ?? []).map(error => <p role="alert" key={error}>{error.startsWith('scope_mismatch:') ? t('companyResearch.scopeMismatch') : error}</p>)}
    {(data.gaps ?? []).map(gap => <p key={gap}>{gap}</p>)}
    {(data.files ?? []).filter(name => ['report.html', 'research.xlsx', 'calculate.py', 'sources.json', 'observations.json', 'validation.json'].includes(name)).map(name => <button className="mx-1 underline" key={name} onClick={() => { void triggerFileDownload(workspaceId, `${data.root}/${name}`); }}>{name}</button>)}
    {button}
    <p role="status" aria-live="polite">{status === 'done' ? t('companyResearch.checked') : status === 'error' ? t('companyResearch.checkError') : ''}</p>
    {query.isError && status !== 'error' && <p role="alert">{t('companyResearch.checkError')}</p>}
  </section>;
}
