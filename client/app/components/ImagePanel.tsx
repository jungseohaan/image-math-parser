'use client';

import { QuestionData } from '../lib/types';

interface ImagePanelProps {
  imageUrl: string;
  questions: QuestionData[];
}

export default function ImagePanel({ imageUrl, questions }: ImagePanelProps) {
  const croppedQuestions = questions.filter(q => q.cropped_image_url);

  return (
    <div style={{ flex: '0 0 350px', maxWidth: '350px' }}>
      <div style={{
        position: 'sticky',
        top: '20px'
      }}>
        {/* 원본 이미지 */}
        <div style={{
          border: '1px solid #e0e0e0',
          borderRadius: '8px',
          overflow: 'hidden',
          marginBottom: '16px'
        }}>
          <div style={{
            padding: '12px',
            backgroundColor: '#f5f5f5',
            borderBottom: '1px solid #e0e0e0',
            fontWeight: 'bold',
            fontSize: '0.9em'
          }}>
            Original Image
          </div>
          <img
            src={imageUrl}
            alt="Uploaded exam"
            style={{ width: '100%', display: 'block' }}
          />
        </div>

        {/* 크롭된 이미지들 */}
        {croppedQuestions.length > 0 && (
          <div style={{
            border: '1px solid #ce93d8',
            borderRadius: '8px',
            overflow: 'hidden',
            backgroundColor: '#faf4fc'
          }}>
            <div style={{
              padding: '12px',
              backgroundColor: '#f3e5f5',
              borderBottom: '1px solid #ce93d8',
              fontWeight: 'bold',
              fontSize: '0.9em',
              color: '#7b1fa2'
            }}>
              Cropped Images by Question
            </div>
            <div style={{ padding: '12px' }}>
              {croppedQuestions.map((question, idx) => (
                <div key={idx} style={{ marginBottom: idx < croppedQuestions.length - 1 ? '12px' : 0 }}>
                  <div style={{
                    fontSize: '0.85em',
                    color: '#7b1fa2',
                    marginBottom: '6px',
                    fontWeight: '500'
                  }}>
                    Question {question.question_number}
                  </div>
                  <img
                    src={question.cropped_image_url}
                    alt={`Question ${question.question_number} cropped`}
                    style={{
                      width: '100%',
                      display: 'block',
                      borderRadius: '4px',
                      border: '1px solid #e1bee7'
                    }}
                  />
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
