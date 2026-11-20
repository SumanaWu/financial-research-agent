// Modified on 2026-11-17 for local study distribution; display names and nonessential project links adjusted. See MODIFICATIONS.md.
import { ZERO_USAGE } from '../../utils/tokenUsage';
import type { AgentInfo } from './types';

// Static main agent object — never changes, so defined once at module level
export const MAIN_AGENT: AgentInfo = {
  id: 'main',
  name: 'Lead Agent',
  displayName: 'FinWorkbench',
  taskId: '',
  description: '',
  type: 'main',
  status: 'active',
  toolCalls: 0,
  tokenUsage: ZERO_USAGE,
  currentTool: '',
  messages: [],
  isActive: true,
  isMainAgent: true,
};
