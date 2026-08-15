import { useCallback, useRef } from 'react';
import { getStreamUrl } from '../api/query';
import { useChatStore } from '../store/chatStore';
import type { Citation } from '../types/api';
import type { QueryRequest } from '../types/api';

export function useQueryStream() {
  const addMessage = useChatStore((s) => s.addMessage);
  const updateMessage = useChatStore((s) => s.updateMessage);
  const abortRef = useRef<AbortController | null>(null);

  const streamQuery = useCallback(async (request: QueryRequest) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    const userMsgId = crypto.randomUUID();
    addMessage({
      id: userMsgId,
      role: 'user',
      content: request.question,
      timestamp: new Date(),
    });

    const assistantId = crypto.randomUUID();
    addMessage({
      id: assistantId,
      role: 'assistant',
      content: '',
      isStreaming: true,
      timestamp: new Date(),
    });

    try {
      const response = await fetch(getStreamUrl(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let fullAnswer = '';
      let citations: Citation[] = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith('data:')) continue;
          const jsonStr = trimmed.slice(5).trim();
          if (!jsonStr) continue;

          try {
            const payload = JSON.parse(jsonStr);
            if (payload.type === 'token') {
              fullAnswer += payload.data;
              updateMessage(assistantId, { content: fullAnswer });
            } else if (payload.type === 'citations') {
              citations = payload.data;
            } else if (payload.type === 'done') {
              updateMessage(assistantId, {
                content: fullAnswer,
                citations,
                isStreaming: false,
              });
            }
          } catch {
            // skip unparseable lines
          }
        }
      }

      if (fullAnswer) {
        updateMessage(assistantId, {
          content: fullAnswer,
          citations,
          isStreaming: false,
        });
      }
    } catch (err) {
      if ((err as Error).name === 'AbortError') return;
      updateMessage(assistantId, {
        content: `Error: ${(err as Error).message}`,
        isStreaming: false,
      });
    }
  }, [addMessage, updateMessage]);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return { streamQuery, cancel };
}
