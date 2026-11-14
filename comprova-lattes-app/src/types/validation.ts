export type MatchStatus = 'VALIDADO' | 'DIVERGENTE' | 'INCONCLUSIVO'
export type JobStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | 'DISPATCH_FAILED'
export type Json = null | boolean | number | string | Json[] | { [key: string]: Json }
export type MatcherConfig = {
  thresholds: { association: number; ambiguity_margin: number; holder_low: number; holder_high: number; title_low: number; title_high: number; institution_low: number; institution_high: number }
  mode: 'PROPOSED' | 'BASELINE_EXACT' | 'BASELINE_NORMALIZED'
  text_metric: 'LEVENSHTEIN_NORM' | 'JARO_WINKLER' | 'TOKEN_HYBRID'
  acronym_table: Record<string, string>; acronym_table_version: string; calibration_metadata: Record<string, Json>
}
export type DocumentInput = { document_id: string; filename: string; mime_type: string; content_base64: string }
export type CreateInput = { xml_content?: string; xml_base64?: string; documents: DocumentInput[]; matcher_config: MatcherConfig }
export type ReviewInput = { reviewer: string; status: MatchStatus; justification: string; matched_document_id: string | null; rejected_document_ids: string[] }
export type Review = ReviewInput & { reviewed_at: string; id?: number; record_index?: number }
export type FieldEvidence = { field_name: string; lattes_raw: string | number | null; document_raw: string | number | null; lattes_normalized: string | number | null; document_normalized: string | number | null; rule_applied: string; similarity_score: number | null; numeric_difference: string | number | null; outcome: string; justification_pt: string }
export type Verdict = { record_index: number; record_id: string | null; category: string; matched_document_id: string | null; association_score: number | null; status: MatchStatus; reason_code: string; diagnostics: string[]; field_evidences: FieldEvidence[]; ambiguity_candidates: { document_id: string; association_score: number; field_evidences: FieldEvidence[] }[]; review_required: boolean; human_review: Review | null }
export type ValidationListItem = { id: string; created_at: string; status: JobStatus; error_code: string | null }
export type ValidationDetail = ValidationListItem & {
  input: CreateInput
  parsed: { curriculum: Json; diagnostics: Json[]; declared_encoding: string | null; unverified_variants: string[]; unrecognized_elements: string[] } | null
  extractions: ({ document_id: string; extraction_status: string } & Record<string, Json>)[] | null
  automatic_result: { mode: string; record_verdicts: Verdict[]; orphan_documents: { document_id: string; reason_code: string; best_candidate_record_id: string | null; best_association_score: number | null }[]; association_pairs: Json[] } | null
  records: { record_index: number; automatic: Verdict; human_review: Review | null; review_required: boolean }[]
  reviews: Review[]; automatic_summary: Record<MatchStatus, number>; reviewed_summary: Record<MatchStatus, number>
}
export type Health = { status: string; version: string; environment: string; gemini_model: string }
