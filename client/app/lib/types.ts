// lib/types.ts - 공통 타입 정의

export interface Choice {
  number: string;
  text: string;
}

export interface AnalysisProcess {
  is_word_problem: boolean;
  objects_used: string[];
  step1_to_math: string;
  step2_solve: string;
  step3_to_context: string;
  mathematical_concept: string;
}

export interface QuestionData {
  question_number: string;
  question_text: string;
  topic_category?: string;
  has_passage: boolean;
  passage: string;
  choices: Choice[];
  has_figure: boolean;
  figure_description: string;
  graph_url?: string;
  graph_error?: string;
  has_table: boolean;
  table_data: string;
  math_expressions: string[];
  question_type: string;
  cropped_image_url?: string;
  analysis_process?: AnalysisProcess | null;
}

export interface AnalysisResult {
  questions: QuestionData[];
  error?: string;
}

export interface Session {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  question_count: number;
  image_filename: string;
  thumbnail_url: string;
}

export interface VariantRecord {
  json_filename: string;
  html_filename: string;
  timestamp: string;
  created: number;
  variant_count: number;
  json_url: string;
  html_url: string;
}

export interface VariantQuestion {
  difficulty: string;
  question_text: string;
  choices?: Choice[];
  answer?: string;
  explanation?: string;
  verification?: {
    is_correct: boolean;
    method: string;
  };
  error?: string;
}

export interface VariantsResult {
  original: {
    question_number: string;
    question_text: string;
    choices: Choice[];
    answer: string;
    explanation: string;
    key_concepts: string[];
  };
  variants: VariantQuestion[];
  generation_method: string;
  generated_code: string;
}

export interface LlmStats {
  total_requests: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost: number;
  by_model: Record<string, {
    requests: number;
    input_tokens: number;
    output_tokens: number;
    cost: number;
  }>;
  by_endpoint: Record<string, {
    requests: number;
    input_tokens: number;
    output_tokens: number;
    cost: number;
  }>;
}

export interface LlmStatsData {
  session_start: string;
  total_calls: number;
  successful_calls: number;
  failed_calls: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  total_cost_usd: number;
  total_cost_krw: number;
  by_model: Record<string, { calls: number; input_tokens: number; output_tokens: number; cost: number }>;
  by_operation: Record<string, { calls: number; input_tokens: number; output_tokens: number; cost: number }>;
  recent_calls: Array<{
    timestamp: string;
    model: string;
    operation: string;
    input_tokens: number;
    output_tokens: number;
    total_cost: number;
    latency_ms: number;
    success: boolean;
  }>;
}
