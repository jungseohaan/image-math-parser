'use client';

import { InlineMath, BlockMath } from 'react-katex';
import 'katex/dist/katex.min.css';

interface RenderMathTextProps {
  text: string;
}

export default function RenderMathText({ text }: RenderMathTextProps) {
  if (!text) return null;

  const parts = text.split(/(\$\$[\s\S]*?\$\$|\$[^$]+?\$)/g);

  return (
    <>
      {parts.map((part, idx) => {
        if (part.startsWith('$$') && part.endsWith('$$')) {
          const math = part.slice(2, -2);
          try {
            return <BlockMath key={idx} math={math} />;
          } catch {
            return <code key={idx}>{part}</code>;
          }
        } else if (part.startsWith('$') && part.endsWith('$')) {
          const math = part.slice(1, -1);
          try {
            return <InlineMath key={idx} math={math} />;
          } catch {
            return <code key={idx}>{part}</code>;
          }
        }
        return <span key={idx}>{part}</span>;
      })}
    </>
  );
}
