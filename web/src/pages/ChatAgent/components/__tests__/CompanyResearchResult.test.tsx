import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import CompanyResearchResult from '../CompanyResearchResult';
import { getResearchDelivery } from '../../utils/api/companyResearch';

vi.mock('../../utils/api/companyResearch', () => ({ getResearchDelivery: vi.fn() }));
vi.mock('../../utils/api/files', () => ({ triggerFileDownload: vi.fn() }));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key }) }));

const delivery = { state: 'partial' as const, root: 'research/test', spec: { cik: '0000320193', as_of: '2024-12-31' } };

beforeEach(() => vi.resetAllMocks());

it('shows progress and completion even when the result is unchanged', async () => {
  let finish!: (value: typeof delivery) => void;
  vi.mocked(getResearchDelivery).mockResolvedValueOnce(delivery).mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
  render(<QueryClientProvider client={new QueryClient()}><CompanyResearchResult threadId="test" workspaceId="ws" /></QueryClientProvider>);
  fireEvent.click(await screen.findByRole('button', { name: 'companyResearch.refresh' }));
  expect(screen.getByRole('button', { name: 'companyResearch.checking' })).toBeDisabled();
  finish(delivery);
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('companyResearch.checked'));
});

it('reports a failed recheck while retaining the previous result', async () => {
  vi.mocked(getResearchDelivery).mockResolvedValueOnce(delivery).mockRejectedValueOnce(new Error('offline'));
  render(<QueryClientProvider client={new QueryClient()}><CompanyResearchResult threadId="test" workspaceId="ws" /></QueryClientProvider>);
  fireEvent.click(await screen.findByRole('button', { name: 'companyResearch.refresh' }));
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('companyResearch.checkError'));
  expect(screen.getByText(/0000320193/)).toBeInTheDocument();
});
