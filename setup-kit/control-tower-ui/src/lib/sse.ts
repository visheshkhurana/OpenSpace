'use client';

import { useEffect, useRef, useCallback } from 'react';
import type { ActivityEvent } from '@/types';
import { USE_MOCK } from './constants';
import { mockActivityEvents } from './mock';

/**
 * Real SSE + mock replayer.
 * In mock mode, cycles through mockActivityEvents every 3–5s
 * and generates a new fake timestamp so the feed feels alive.
 */
export function useFeed(onEvent: (event: ActivityEvent) => void, onStatus?: (connected: boolean) => void) {
  const esRef = useRef<EventSource | null>(null);
  const retry = useRef(3000);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const cbRef = useRef(onEvent);
  cbRef.current = onEvent;

  const statusRef = useRef(onStatus);
  statusRef.current = onStatus;

  const connect = useCallback(() => {
    if (USE_MOCK) {
      // Replay mock events on a loop — fire one immediately and every 3.5s
      let idx = 0;
      statusRef.current?.(true);

      const fire = () => {
        const base = mockActivityEvents[idx % mockActivityEvents.length];
        const evt: ActivityEvent = {
          ...base,
          id: `${base.id}_${Date.now()}_${idx}`,
          timestamp: new Date().toISOString(),
        };
        cbRef.current(evt);
        idx += 1;
      };
      fire();
      timerRef.current = setInterval(fire, 3500);
      return;
    }

    const base = process.env.NEXT_PUBLIC_API_BASE ?? '';
    if (!base) {
      statusRef.current?.(false);
      return;
    }
    try {
      const es = new EventSource(`${base}/feed`, { withCredentials: false });
      esRef.current = es;

      es.onopen = () => {
        statusRef.current?.(true);
        retry.current = 3000;
      };
      es.onmessage = (e) => {
        try {
          const parsed: ActivityEvent = JSON.parse(e.data);
          cbRef.current(parsed);
        } catch {
          /* ignore malformed */
        }
      };
      es.onerror = () => {
        statusRef.current?.(false);
        es.close();
        setTimeout(() => {
          retry.current = Math.min(retry.current * 2, 30000);
          connect();
        }, retry.current);
      };
    } catch {
      statusRef.current?.(false);
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      esRef.current?.close();
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [connect]);
}
