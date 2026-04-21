'use client';

import { useEffect, useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import { ActivityEventRow } from '@/components/molecules/ActivityEvent';
import { useFeed } from '@/lib/sse';
import type { ActivityEvent } from '@/types';
import { mockActivityEvents } from '@/lib/mock';
import { USE_MOCK } from '@/lib/constants';

export function ActivityFeed() {
  const [events, setEvents] = useState<ActivityEvent[]>(() => (USE_MOCK ? [...mockActivityEvents] : []));
  const [connected, setConnected] = useState(false);

  useFeed(
    (e) => {
      setEvents((prev) => {
        const next = [e, ...prev];
        return next.slice(0, 100);
      });
    },
    (c) => setConnected(c)
  );

  return (
    <div className="rounded-2xl border border-border bg-surface flex flex-col min-h-[400px]">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <h3 className="text-[11px] font-bold uppercase tracking-widest text-text-muted">Live feed</h3>
        {connected ? (
          <span className="text-[11px] flex items-center gap-1.5 text-success">
            <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse-slow" />
            live
          </span>
        ) : (
          <span className="text-[11px] text-warn">reconnecting…</span>
        )}
      </div>
      <div className="flex-1 overflow-y-auto max-h-[520px] p-1">
        {events.length === 0 ? (
          <div className="flex items-center justify-center h-40 text-sm text-text-muted">
            Waiting for agent activity
            <span className="cursor-blink ml-1">_</span>
          </div>
        ) : (
          <AnimatePresence mode="popLayout">
            {events.map((e) => (
              <ActivityEventRow key={e.id} event={e} />
            ))}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
