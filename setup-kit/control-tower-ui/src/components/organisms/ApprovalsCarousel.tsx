'use client';

import Link from 'next/link';
import type { ApprovalFull } from '@/types';
import { RiskBadge } from '@/components/atoms/RiskBadge';
import { cn, formatINRShort } from '@/lib/utils';
import { CheckCircle2, XCircle } from 'lucide-react';

export function ApprovalsCarousel({
  approvals,
  onApprove,
  onDeny,
}: {
  approvals: ApprovalFull[];
  onApprove: (id: string) => void;
  onDeny: (id: string) => void;
}) {
  return (
    <div className="rounded-2xl border border-border bg-surface">
      <div className="flex items-center justify-between px-5 py-3 border-b border-border">
        <h3 className="text-[11px] font-bold uppercase tracking-widest text-text-muted">
          Pending approvals ({approvals.length})
        </h3>
        <Link href="/approvals" className="text-xs text-accent hover:underline">
          View all →
        </Link>
      </div>
      {approvals.length === 0 ? (
        <div className="p-6 text-sm text-text-muted flex items-center gap-2">
          <CheckCircle2 size={14} className="text-success" />
          No pending approvals. Agents are running clean.
        </div>
      ) : (
        <div className="overflow-x-auto flex gap-3 p-4 snap-x">
          {approvals.map((a) => (
            <div
              key={a.id}
              className={cn(
                'snap-start flex-shrink-0 w-[340px] rounded-xl border p-4 bg-bg',
                a.risk === 'HIGH' ? 'border-danger/40' : 'border-border'
              )}
            >
              <div className="flex items-center gap-2 mb-2">
                <RiskBadge risk={a.risk} />
                <span className="text-sm font-medium text-text">{a.agent_name}</span>
              </div>
              <p className="text-sm text-text min-h-[40px] leading-snug line-clamp-2">{a.what}</p>
              {a.cost_inr !== null && (
                <div className="mt-2 text-xs text-warn font-semibold">{formatINRShort(a.cost_inr)}</div>
              )}
              <div className="mt-3 flex items-center gap-2">
                <button
                  onClick={() => onApprove(a.id)}
                  className="flex items-center gap-1 flex-1 justify-center px-2.5 py-1.5 rounded-md bg-success/15 text-success border border-success/20 text-xs font-medium hover:bg-success/25"
                >
                  <CheckCircle2 size={12} />
                  Approve
                </button>
                <button
                  onClick={() => onDeny(a.id)}
                  className="flex items-center gap-1 flex-1 justify-center px-2.5 py-1.5 rounded-md bg-danger/15 text-danger border border-danger/20 text-xs font-medium hover:bg-danger/25"
                >
                  <XCircle size={12} />
                  Deny
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
