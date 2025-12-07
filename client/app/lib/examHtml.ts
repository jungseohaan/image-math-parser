import { VariantQuestion } from './types';

// 기본 템플릿 (템플릿 파일을 로드할 수 없을 때 사용)
const DEFAULT_TEMPLATE = `<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>{{title}}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>
<style>
@page { size: A4; margin: 15mm; }
@media print {
  body { margin: 0; padding: 15mm; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .no-print { display: none !important; }
  .answer-sheet { page-break-before: always; }
}
* { box-sizing: border-box; }
body { font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif; font-size: 11pt; line-height: 1.5; margin: 0; padding: 15mm; background: white; max-width: 210mm; margin: 0 auto; }
.print-btn { position: fixed; top: 20px; right: 20px; padding: 12px 24px; background: #007bff; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: bold; z-index: 1000; }
.print-btn:hover { background: #0056b3; }
.exam-header { text-align: center; border-bottom: 2px solid #333; padding-bottom: 15px; margin-bottom: 20px; }
.exam-header h1 { margin: 0 0 10px 0; font-size: 18pt; font-weight: bold; }
.exam-info { display: flex; justify-content: space-between; font-size: 10pt; color: #666; }
.questions-container { column-count: 2; column-gap: 30px; column-rule: 1px solid #333; }
.question { break-inside: avoid; page-break-inside: avoid; margin-bottom: 15px; padding: 10px; border: 1px solid #e0e0e0; border-radius: 4px; background: #fafafa; }
.question-header { display: flex; align-items: baseline; margin-bottom: 8px; }
.question-number { font-weight: bold; font-size: 12pt; min-width: 30px; color: #333; }
.question-text { margin-bottom: 10px; text-align: justify; }
.choices { margin-left: 5px; }
.choice { padding: 4px 0; display: flex; align-items: flex-start; }
.choice-number { min-width: 25px; font-weight: 500; }
.choice-text { flex: 1; }
.answer-sheet { margin-top: 30px; padding-top: 20px; border-top: 2px dashed #ccc; column-count: 1; }
.answer-sheet h2 { text-align: center; font-size: 14pt; margin-bottom: 15px; }
.answer-table { width: 100%; max-width: 500px; margin: 0 auto; border-collapse: collapse; }
.answer-table th, .answer-table td { border: 1px solid #ddd; padding: 8px 12px; text-align: center; }
.answer-table th { background: #f5f5f5; font-weight: bold; }
</style>
</head>
<body>
<button class="print-btn no-print" onclick="window.print()">인쇄</button>
<div class="exam-header">
  <h1>{{title}}</h1>
  <div class="exam-info">
    <span>이름: ________________</span>
    <span>날짜: ________________</span>
  </div>
</div>
<div class="questions-container">{{questions}}</div>
{{answerSheet}}
<script>
document.addEventListener("DOMContentLoaded", function() {
  renderMathInElement(document.body, {
    delimiters: [
      {left: "$$", right: "$$", display: true},
      {left: "$", right: "$", display: false},
      {left: "\\\\[", right: "\\\\]", display: true},
      {left: "\\\\(", right: "\\\\)", display: false}
    ],
    throwOnError: false
  });
});
</script>
</body>
</html>`;

// 템플릿 로드 함수
export async function loadTemplate(): Promise<string> {
  // localStorage에서 사용자 정의 템플릿 확인
  if (typeof window !== 'undefined') {
    const customTemplate = localStorage.getItem('exam-template');
    if (customTemplate) {
      return customTemplate;
    }
  }

  // 기본 템플릿 파일 로드 시도
  try {
    const response = await fetch('/templates/exam-default.html');
    if (response.ok) {
      return await response.text();
    }
  } catch (error) {
    console.warn('템플릿 로드 실패, 기본 템플릿 사용:', error);
  }

  return DEFAULT_TEMPLATE;
}

// 템플릿 저장 함수
export function saveTemplate(template: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem('exam-template', template);
  }
}

// 템플릿 초기화 함수
export function resetTemplate(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('exam-template');
  }
}

// 기본 템플릿 가져오기
export async function getDefaultTemplate(): Promise<string> {
  try {
    const response = await fetch('/templates/exam-default.html');
    if (response.ok) {
      return await response.text();
    }
  } catch (error) {
    console.warn('기본 템플릿 로드 실패:', error);
  }
  return DEFAULT_TEMPLATE;
}

// 문제 HTML 생성
function generateQuestionsHtml(questions: VariantQuestion[]): string {
  return questions.map((q, idx) => {
    const choicesHtml = q.choices?.map(c =>
      `<div class="choice">
        <span class="choice-number">${c.number}.</span>
        <span class="choice-text">${c.text}</span>
      </div>`
    ).join('') || '';

    return `
      <div class="question">
        <div class="question-header">
          <span class="question-number">${idx + 1}.</span>
        </div>
        <div class="question-text">${q.question_text}</div>
        <div class="choices">${choicesHtml}</div>
      </div>
    `;
  }).join('');
}

// 정답표 HTML 생성
function generateAnswerSheetHtml(questions: VariantQuestion[]): string {
  return `
    <div class="answer-sheet">
      <h2>정답표</h2>
      <table class="answer-table">
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
  `;
}

// 템플릿 기반 HTML 생성 (동기 버전 - localStorage 사용)
export function generateExamHtml(
  questions: VariantQuestion[],
  title: string,
  includeAnswerSheet: boolean
): string {
  const questionsHtml = generateQuestionsHtml(questions);
  const answerSheetHtml = includeAnswerSheet ? generateAnswerSheetHtml(questions) : '';

  // localStorage에서 템플릿 확인
  let template = DEFAULT_TEMPLATE;
  if (typeof window !== 'undefined') {
    const customTemplate = localStorage.getItem('exam-template');
    if (customTemplate) {
      template = customTemplate;
    }
  }

  return template
    .replace(/\{\{title\}\}/g, title)
    .replace(/\{\{questions\}\}/g, questionsHtml)
    .replace(/\{\{answerSheet\}\}/g, answerSheetHtml);
}

// 템플릿 기반 HTML 생성 (비동기 버전)
export async function generateExamHtmlAsync(
  questions: VariantQuestion[],
  title: string,
  includeAnswerSheet: boolean
): Promise<string> {
  const template = await loadTemplate();
  const questionsHtml = generateQuestionsHtml(questions);
  const answerSheetHtml = includeAnswerSheet ? generateAnswerSheetHtml(questions) : '';

  return template
    .replace(/\{\{title\}\}/g, title)
    .replace(/\{\{questions\}\}/g, questionsHtml)
    .replace(/\{\{answerSheet\}\}/g, answerSheetHtml);
}
