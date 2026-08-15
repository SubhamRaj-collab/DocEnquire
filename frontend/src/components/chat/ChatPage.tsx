import { useEffect, useRef } from 'react';
import { MessageSquare } from 'lucide-react';
import { useChatStore } from '../../store/chatStore';
import { useQueryStream } from '../../hooks/useQueryStream';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';

export function ChatPage() {
  const messages = useChatStore((s) => s.messages);
  const collection = useChatStore((s) => s.activeCollection);
  const { streamQuery } = useQueryStream();
  const bottomRef = useRef<HTMLDivElement>(null);

  const isStreaming = messages.some((m) => m.isStreaming);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (question: string) => {
    streamQuery({
      question,
      collection_name: collection,
      top_k: 5,
    });
  };

  return (
    <div className="flex flex-col h-screen">
      <div className="border-b border-gray-200 bg-white px-6 py-4">
        <h2 className="text-lg font-semibold text-gray-900">Document Q&A</h2>
        <p className="text-xs text-gray-500">
          Collection: <span className="font-medium">{collection}</span>
        </p>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-6">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <MessageSquare size={48} className="text-gray-300 mb-4" />
            <h3 className="text-lg font-medium text-gray-700">Ask a question</h3>
            <p className="text-sm text-gray-500 mt-1 max-w-md">
              Upload documents in the Documents tab, then ask questions here.
              Answers will include citations to source documents.
            </p>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto space-y-6">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      <ChatInput onSubmit={handleSubmit} disabled={isStreaming} />
    </div>
  );
}
