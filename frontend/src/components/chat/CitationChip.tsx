interface CitationChipProps {
  label: string;
  isExpanded: boolean;
  onClick: () => void;
}

export function CitationChip({ label, isExpanded, onClick }: CitationChipProps) {
  const number = label.replace(/\[SOURCE_|\]/g, '');
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded text-xs font-semibold transition-colors cursor-pointer ${
        isExpanded
          ? 'bg-brand-600 text-white'
          : 'bg-brand-100 text-brand-700 hover:bg-brand-200'
      }`}
      title={`Source ${number}`}
    >
      {number}
    </button>
  );
}
