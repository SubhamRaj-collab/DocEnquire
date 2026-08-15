import { useMemo, useState } from 'react';
import { parseAnswer } from '../../lib/citationParser';
import { CitationChip } from './CitationChip';
import { CitationDetail } from './CitationDetail';
import type { Citation } from '../../types/api';

interface AnswerContentProps {
  text: string;
  citations?: Citation[];
}

export function AnswerContent({ text, citations }: AnswerContentProps) {
  const segments = useMemo(() => parseAnswer(text), [text]);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  return (
    <div>
      <div className="prose prose-sm max-w-none text-gray-800 leading-relaxed">
        {segments.map((seg, i) =>
          seg.type === 'text' ? (
            <span key={i}>{seg.value}</span>
          ) : (
            <CitationChip
              key={i}
              label={seg.label}
              isExpanded={expandedIndex === seg.index}
              onClick={() =>
                setExpandedIndex(expandedIndex === seg.index ? null : seg.index)
              }
            />
          )
        )}
      </div>
      {expandedIndex !== null && citations?.[expandedIndex] && (
        <CitationDetail citation={citations[expandedIndex]} />
      )}
    </div>
  );
}
