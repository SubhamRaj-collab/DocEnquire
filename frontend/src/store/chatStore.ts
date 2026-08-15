import { create } from 'zustand';
import type { ChatMessage } from '../types/ui';

interface ChatState {
  messages: ChatMessage[];
  activeCollection: string;
  addMessage: (msg: ChatMessage) => void;
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void;
  clearMessages: () => void;
  setActiveCollection: (name: string) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  activeCollection: localStorage.getItem('rag_collection') || 'default',

  addMessage: (msg) =>
    set((state) => ({ messages: [...state.messages, msg] })),

  updateMessage: (id, updates) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, ...updates } : m
      ),
    })),

  clearMessages: () => set({ messages: [] }),

  setActiveCollection: (name) => {
    localStorage.setItem('rag_collection', name);
    set({ activeCollection: name });
  },
}));
