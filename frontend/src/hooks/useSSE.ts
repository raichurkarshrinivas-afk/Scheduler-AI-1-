import { useEffect, useRef, useState, useCallback } from 'react';
import { api } from '../services/api';

export interface SSEMessage {
  id: number;
  event_type: string;
  payload: Record<string, any>;
  created_at: number;
}

export interface UseSSEOptions {
  enabled?: boolean;
  onEvent?: (event: SSEMessage) => void;
  onNotificationNew?: (payload: any) => void;
  onPublicationUpdated?: (payload: any) => void;
}

export function useSSE(options: UseSSEOptions = {}) {
  const { enabled = true, onEvent, onNotificationNew, onPublicationUpdated } = options;

  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [fallbackMode, setFallbackMode] = useState<boolean>(false);
  const [lastEvent, setLastEvent] = useState<SSEMessage | null>(null);
  const lastEventIdRef = useRef<number>(0);

  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;
  const onNotificationNewRef = useRef(onNotificationNew);
  onNotificationNewRef.current = onNotificationNew;
  const onPublicationUpdatedRef = useRef(onPublicationUpdated);
  onPublicationUpdatedRef.current = onPublicationUpdated;

  const handleIncomingEvent = useCallback((event: SSEMessage) => {
    if (event.id > lastEventIdRef.current) {
      lastEventIdRef.current = event.id;
    }
    setLastEvent(event);

    if (onEventRef.current) {
      onEventRef.current(event);
    }

    if (event.event_type === 'NOTIFICATION_NEW' && onNotificationNewRef.current) {
      onNotificationNewRef.current(event.payload);
    } else if (event.event_type === 'PUBLICATION_UPDATED' && onPublicationUpdatedRef.current) {
      onPublicationUpdatedRef.current(event.payload);
    }
  }, []);

  useEffect(() => {
    if (!enabled) {
      setIsConnected(false);
      setFallbackMode(false);
      return;
    }

    let eventSource: EventSource | null = null;
    let pollInterval: any = null;
    let reconnectTimeout: any = null;
    let failedAttempts = 0;

    const startPollingFallback = () => {
      setFallbackMode(true);
      setIsConnected(false);

      if (pollInterval) clearInterval(pollInterval);
      pollInterval = setInterval(async () => {
        try {
          const res = await api.communication.pollEvents(lastEventIdRef.current);
          if (res?.events && res.events.length > 0) {
            for (const ev of res.events) {
              handleIncomingEvent(ev);
            }
          }
        } catch {
          // ignore polling errors
        }
      }, 8000);
    };

    const connectSSE = () => {
      if (typeof window === 'undefined' || !window.EventSource) {
        startPollingFallback();
        return;
      }

      try {
        // Same-origin URL, ZERO tokens in query params!
        const url = `/api/v1/communication/events/stream`;
        eventSource = new EventSource(url, { withCredentials: true });

        eventSource.onopen = () => {
          setIsConnected(true);
          setFallbackMode(false);
          failedAttempts = 0;
          if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
          }
        };

        const handleMessage = (e: MessageEvent) => {
          try {
            const data: SSEMessage = JSON.parse(e.data);
            handleIncomingEvent(data);
          } catch {
            // Keepalive or unparseable comment
          }
        };

        // Listen for standard and custom events
        eventSource.addEventListener('NOTIFICATION_NEW', handleMessage as any);
        eventSource.addEventListener('PUBLICATION_UPDATED', handleMessage as any);
        eventSource.addEventListener('JOB_STATUS_UPDATED', handleMessage as any);
        eventSource.onmessage = handleMessage;

        eventSource.onerror = () => {
          setIsConnected(false);
          failedAttempts += 1;
          if (eventSource) {
            eventSource.close();
            eventSource = null;
          }

          if (failedAttempts >= 2) {
            // Fall back to polling
            startPollingFallback();
          } else {
            // Reconnect attempt in 3s
            reconnectTimeout = setTimeout(connectSSE, 3000);
          }
        };
      } catch {
        startPollingFallback();
      }
    };

    connectSSE();

    return () => {
      if (eventSource) {
        eventSource.close();
      }
      if (pollInterval) {
        clearInterval(pollInterval);
      }
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
    };
  }, [enabled, handleIncomingEvent]);

  return {
    isConnected,
    fallbackMode,
    lastEvent,
    lastEventId: lastEventIdRef.current,
  };
}
