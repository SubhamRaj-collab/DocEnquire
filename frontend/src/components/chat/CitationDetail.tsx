import { FileText, BookOpen } from 'lucide-react';
import type { Citation } from '../../types/api';

interface CitationDetailProps {
  citation: Citation;
}

export function CitationDetail({ citation }: CitationDetailProps) {
  return (
    <div className="mt-3 p-3 bg-gray-50 border border-gray-200 rounded-lg text-sm">
      <div className="flex items-center gap-2 mb-2">
        <FileText size={14} className="text-brand-600" />
        <span className="font-medium text-gray-900">{citation.filename}</span>
        {citation.page_number && (
          <span className="text-xs text-gray-500 bg-gray-200 px-1.5 py-0.5 rounded">
            Page {citation.page_number}
          </span>
        )}
        {citation.slide_number && (
          <span className="text-xs text-gray-500 bg-gray-200 px-1.5 py-0.5 rounded">
            Slide {citation.slide_number}
          </span>
        )}
        {citation.sheet_name && (
          <span className="text-xs text-gray-500 bg-gray-200 px-1.5 py-0.5 rounded">
            Sheet: {citation.sheet_name}
          </span>
        )}
      </div>
      {citation.section_title && (
        <div className="flex items-center gap-1.5 mb-2 text-xs text-gray-500">
          <BookOpen size={12} />
          <span>{citation.section_title}</span>
        </div>
      )}
      <div className="border-l-2 border-brand-300 pl-3 text-gray-700 text-xs leading-relaxed whitespace-pre-wrap">
        {citation.chunk_text}
      </div>
      {citation.relevance_score !== null && (
        <div className="mt-2 text-xs text-gray-400">
          Relevance: {((1 - citation.relevance_score) * 100).toFixed(0)}%
        </div>
      )}
    </div>
  );
}
