import { VariantQuestion } from './types';

export function generateExamHtml(questions: VariantQuestion[], title: string, includeAnswerSheet: boolean): string {
  const questionsHtml = questions.map((q, idx) => {
    const choicesHtml = q.choices?.map(c =>
      `<div class="choice">${c.number}. ${c.text}</div>`
    ).join('') || '';

    return `
      <div class="question">
        <div class="question-header">${idx + 1}.</div>
        <div class="question-content">
          <div class="question-text">${q.question_text}</div>
          <div class="choices">${choicesHtml}</div>
        </div>
      </div>
    `;
  }).join('');

  const answersHtml = includeAnswerSheet ? `
    <div class="answer-sheet">
      <h2>정답표</h2>
      <table>
        <tr>
          <th>문항</th>
          <th>정답</th>
        </tr>
        ${questions.map((q, idx) => `
          <tr>
            <td>${idx + 1}</td>
            <td>${q.answer || '-'}</td>
          </tr>
        `).join('')}
      </table>
    </div>
  ` : '';

  return `
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>${title}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
  onload="renderMathInElement(document.body, {delimiters: [{left: '$$', right: '$$', display: true}, {left: '$', right: '$', display: false}]});"></script>
<style>
  @media print {
    body { margin: 0; padding: 20px; }
    .no-print { display: none !important; }
    .answer-sheet { page-break-before: always; }
  }
  body {
    font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
    max-width: 800px;
    margin: 0 auto;
    padding: 40px 20px;
    line-height: 1.6;
  }
  h1 {
    text-align: center;
    border-bottom: 2px solid #333;
    padding-bottom: 20px;
    margin-bottom: 30px;
  }
  .print-btn {
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 12px 24px;
    background: #007bff;
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
    font-weight: bold;
  }
  .print-btn:hover { background: #0056b3; }
  .question {
    display: flex;
    margin-bottom: 30px;
    padding: 20px;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    background: #fafafa;
  }
  .question-header {
    font-weight: bold;
    font-size: 1.2em;
    min-width: 40px;
    color: #333;
  }
  .question-content { flex: 1; }
  .question-text {
    margin-bottom: 16px;
    font-size: 1em;
  }
  .choices { margin-left: 10px; }
  .choice {
    padding: 8px 0;
    color: #444;
  }
  .answer-sheet {
    margin-top: 40px;
    padding-top: 40px;
    border-top: 2px dashed #ccc;
  }
  .answer-sheet h2 {
    text-align: center;
    margin-bottom: 20px;
  }
  .answer-sheet table {
    width: 100%;
    max-width: 400px;
    margin: 0 auto;
    border-collapse: collapse;
  }
  .answer-sheet th, .answer-sheet td {
    border: 1px solid #ddd;
    padding: 10px;
    text-align: center;
  }
  .answer-sheet th { background: #f5f5f5; }
</style>
</head>
<body>
<button class="print-btn no-print" onclick="window.print()">인쇄</button>
<h1>${title}</h1>
<div class="questions">${questionsHtml}</div>
${answersHtml}
</body>
</html>
  `;
}
