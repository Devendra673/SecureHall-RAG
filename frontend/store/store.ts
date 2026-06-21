import { create } from 'zustand';

// ---------------------------------------------------------
// User Settings State
// ---------------------------------------------------------
interface UserSettings {
  theme: 'light' | 'dark' | 'system';
  responseLength: 'short' | 'medium' | 'detailed';
  showCitations: boolean;
  confidenceThreshold: number;
}

interface UserSettingsState {
  settings: UserSettings;
  updateSettings: (newSettings: Partial<UserSettings>) => void;
  isSettingsOpen: boolean;
  setSettingsOpen: (open: boolean) => void;
}

export const useSettingsStore = create<UserSettingsState>((set) => ({
  settings: {
    theme: 'dark',
    responseLength: 'medium',
    showCitations: true,
    confidenceThreshold: 0.75,
  },
  isSettingsOpen: false,
  setSettingsOpen: (open) => set({ isSettingsOpen: open }),
  updateSettings: (newSettings) =>
    set((state) => ({
      settings: { ...state.settings, ...newSettings },
    })),
}));

// ---------------------------------------------------------
// Chat State
// ---------------------------------------------------------
export interface Citation {
  citation_id: number;
  chunk_id: string;
  source_document: string;
  text_excerpt: string;
  relevance_score?: number;
  page_number?: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  confidence?: number;
  timestamp: Date;
}

interface ChatState {
  messages: ChatMessage[];
  isThinking: boolean;
  addMessage: (message: ChatMessage) => void;
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void;
  setThinking: (thinking: boolean) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isThinking: false,
  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),
  updateMessage: (id, updates) =>
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === id ? { ...msg, ...updates } : msg
      ),
    })),
  setThinking: (thinking) => set({ isThinking: thinking }),
  clearMessages: () => set({ messages: [] }),
}));

// ---------------------------------------------------------
// Document Management State
// ---------------------------------------------------------
export interface DocumentItem {
  doc_id: string;
  filename: string;
  file_size_bytes: number;
  status: 'processing' | 'ready' | 'error';
  upload_timestamp: string;
}

interface DocumentState {
  documents: DocumentItem[];
  setDocuments: (docs: DocumentItem[]) => void;
  addDocument: (doc: DocumentItem) => void;
  removeDocument: (doc_id: string) => void;
  updateDocumentStatus: (doc_id: string, status: DocumentItem['status']) => void;
}

export const useDocumentStore = create<DocumentState>((set) => ({
  documents: [],
  setDocuments: (docs) => set({ documents: docs }),
  addDocument: (doc) =>
    set((state) => ({ documents: [doc, ...state.documents] })),
  removeDocument: (doc_id) =>
    set((state) => ({
      documents: state.documents.filter((d) => d.doc_id !== doc_id),
    })),
  updateDocumentStatus: (doc_id, status) =>
    set((state) => ({
      documents: state.documents.map((d) =>
        d.doc_id === doc_id ? { ...d, status } : d
      ),
    })),
}));
