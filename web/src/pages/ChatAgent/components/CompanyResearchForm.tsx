import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { useState } from 'react';
import { useNavigate } from 'react-router';
import { useTranslation } from 'react-i18next';
import { createThreadWithTitle } from '../utils/api/threads';
import { resolveResearchCompany } from '../utils/api/companyResearch';

export default function CompanyResearchForm({ workspaceId }: { workspaceId: string }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [symbol, setSymbol] = useState('AAPL');
  const [asOf, setAsOf] = useState(() => new Intl.DateTimeFormat('en-CA', { timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date()));
  const [focus, setFocus] = useState('');
  const [identity, setIdentity] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [candidate, setCandidate] = useState<{ cik: string; name: string; ticker: string } | null>(null);
  return <Dialog><DialogTrigger asChild><button type="button" className="inline-flex items-center rounded-full bg-(--color-bg-tag) px-3 py-1 text-xs text-(--color-text-tertiary) transition-colors hover:bg-(--color-bg-elevated) hover:text-(--color-text-secondary) focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">{t('companyResearch.title')}</button></DialogTrigger><DialogContent className="max-h-[85dvh] overflow-y-auto"><DialogHeader><DialogTitle>{t('companyResearch.title')}</DialogTitle></DialogHeader><form className="grid gap-2 p-3" onSubmit={async e => {
    e.preventDefault(); setBusy(true); setError('');
    try {
      if (!candidate) {
        const found = await resolveResearchCompany(symbol, identity);
        if (found.length !== 1) throw new Error(t('companyResearch.ambiguous'));
        setCandidate(found[0]);
      } else {
        const spec = { cik: candidate.cik, as_of: asOf, focus };
        const thread = await createThreadWithTitle({ workspaceId, firstQuery: '', title: `${candidate.ticker} · ${asOf}`, companyResearch: spec });
        navigate(`/chat/t/${thread.thread_id}`, { state: { workspaceId, skills: ['company-research'], initialMessage: `Run company-research-v1 for ${JSON.stringify(spec)}. SEC access identity: ${identity}. Output root: research/${thread.thread_id}. Use only eligible evidence, list gaps, and produce report.html and research.xlsx.` } });
      }
    } catch (err) { setError(err instanceof Error ? err.message : String(err)); }
    finally { setBusy(false); }
  }}>
    <label>{t('companyResearch.symbol')}<Input required value={symbol} onChange={e => { setSymbol(e.target.value); setCandidate(null); }} /></label>
    <label>{t('companyResearch.date')}<Input type="date" required value={asOf} onChange={e => setAsOf(e.target.value)} /></label>
    <label>{t('companyResearch.identity')}<Input required value={identity} onChange={e => { setIdentity(e.target.value); setCandidate(null); }} /></label>
    <label>{t('companyResearch.focus')}<Input value={focus} maxLength={2000} onChange={e => setFocus(e.target.value)} /></label>
    {candidate && <p>{candidate.name} — CIK {candidate.cik}</p>}
    <button className="rounded border p-2" type="submit" disabled={busy}>{candidate ? t('companyResearch.start') : t('companyResearch.resolve')}</button>
    {error && <p role="alert">{error}</p>}
  </form></DialogContent></Dialog>;
}
