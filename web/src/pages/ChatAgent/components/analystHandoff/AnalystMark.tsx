// Modified on 2026-11-17 for local study distribution; display names and nonessential project links adjusted. See MODIFICATIONS.md.
import { FinWorkbenchMark } from '@/components/brand/FinWorkbenchMark';
import { cn } from '@/lib/utils';
import { RunAvatar } from '../messageList/runCard';

const MARK = 'h-[15px] w-[15px]';

/**
 * A workspace analyst is a whole FinWorkbench agent, so it wears our mark: drawn
 * in the reading color on the round avatar a subagent's role glyph sits on,
 * and clear of the amber that means working. Which workspace it works in is
 * said in words beside it, never by the avatar. `quiet` dims it for a
 * hand-off that never happened.
 */
export function AnalystMark({ quiet = false }: { quiet?: boolean }) {
  return (
    <RunAvatar quiet={quiet} className={quiet ? undefined : 'text-(--color-text-primary)'}>
      <FinWorkbenchMark className={MARK} />
    </RunAvatar>
  );
}

/** The mark once, bare, heading a group of hand-offs (`RunGroup` centers it
 *  over its rows' glyphs): several of the same avatar stacked would only
 *  repeat it. */
export function AnalystGroupMark() {
  return <FinWorkbenchMark className={cn(MARK, 'text-(--color-text-primary)')} />;
}
