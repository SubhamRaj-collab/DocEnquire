import type { AnswerSegment } from '../types/ui';

const CITATION_REGEX = /\[SOURCE_(\d+)\]/g;

export function parseAnswer(text: string): AnswerSegment[] {
  const segments: AnswerSegment[] = [];
  let lastIndex = 0;

  CITATION_REGEX.lastIndex = 0;

  let match: RegExpExecArray | null;
  while ((match = CITATION_REGEX.exec(text)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: 'text', value: text.slice(lastIndex, match.index) });
    }
    segments.push({
      type: 'citation',
      label: match[0],
      index: parseInt(match[1], 10) - 1,
    });
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    segments.push({ type: 'text', value: text.slice(lastIndex) });
  }

  return segments;
}
