import { User, Bot, Loader2 } from 'lucide-react';
import type { ChatMessage } from '../../types/ui';
import { AnswerContent } from './AnswerContent';

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser ? 'bg-brand-600' : 'bg-gray-200'
        }`}
      >
        {isUser ? (
          <User size={16} className="text-white" />
        ) : (
          <Bot size={16} className="text-gray-600" />
        )}
      </div>

      <div
        className={`max-w-[80%] rounded-xl px-4 py-3 ${
          isUser
            ? 'bg-brand-600 text-white'
            : 'bg-white border border-gray-200 text-gray-800'
        }`}
      >
        {isUser ? (
          <p className="text-sm">{message.content}</p>
        ) : (
          <>
            {message.content ? (
              <AnswerContent text={message.content} citations={message.citations} />
            ) : message.isStreaming ? (
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Loader2 size={14} className="animate-spin" />
                <span>Thinking...</span>
              </div>
            ) : null}

            {!message.isStreaming && message.usage && (
              <div className="mt-2 pt-2 border-t border-gray-100 text-xs text-gray-400">
                {message.model} | {message.usage.prompt_tokens} + {message.usage.completion_tokens} tokens
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
