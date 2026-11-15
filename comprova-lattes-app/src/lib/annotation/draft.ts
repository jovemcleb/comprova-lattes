import { canonicalSha256 } from './canonical'
import {
  DOCUMENT_MIME_TYPES,
  expectExactKeys,
  expectNullableString,
  expectSha256,
  expectString,
  fail,
  isPlainObject,
  scanForbiddenKeys,
  type AnnotationPackage,
  type DocumentMime,
  type PackageCase,
} from './package'
import {
  parseOcrParams,
  parseOcrRegexFields,
  type OcrParamsRecord,
  type VerifiedOcrResponse,
} from './ocr'

export const EXPORT_VERSION_V1 = 'annotation-export-v1'
export const EXPORT_VERSION_V2 = 'annotation-export-v2'
export const EXPORT_VERSION = EXPORT_VERSION_V2

const STORAGE_PREFIX_V1 = 'comprova-lattes:annotation-draft:v1'
const STORAGE_PREFIX_V2 = 'comprova-lattes:annotation-draft:v2'
const MAX_VALUE_LENGTH = 500
const MAX_NOTE_LENGTH = 2000
const MAX_OCR_TEXT_LENGTH = 200_000
const MAX_COPY_EVENTS = 200
const MIN_CONTEXT_NOTE = 10

export const OBSERVABILITY_LIMIT_NOTE =
  'Registra apenas acionamentos explícitos dos botões do painel OCR; não detecta digitação manual, seleção livre de texto nem atalhos de teclado.'

export const METHODOLOGY_UNASSISTED_NOTE =
  'Revisão humana manual sem acionamento de OCR (condição não assistida).'

export const METHODOLOGY_OCR_ASSISTED_NOTE =
  'Revisão humana assistida por OCR local (TesseractOCR + OCRRegex). Não equivale a anotação humana independente sem auxílio e apresenta potencial viés pró-baseline clássico.'

export type ReviewMode = 'unassisted' | 'ocr_assisted'
export type EvaluationCondition = 'independent_unassisted_human_review' | 'ocr_assisted_human_review'

export const FIELD_DEFS = [
  { key: 'holder_name', label: 'Titular', kind: 'text' },
  { key: 'issuer_institution', label: 'Instituição emissora (nome)', kind: 'text' },
  { key: 'issuer_acronym', label: 'Sigla da instituição', kind: 'text' },
  { key: 'issuer_name_acronym_evidence', label: 'Evidência literal (trecho que liga nome e sigla)', kind: 'text' },
  { key: 'activity_title', label: 'Título ou atividade', kind: 'text' },
  { key: 'event_name', label: 'Evento', kind: 'text' },
  { key: 'participation_role_raw', label: 'Papel (como escrito)', kind: 'text' },
  { key: 'workload_hours', label: 'Carga horária', kind: 'text' },
  { key: 'start_year', label: 'Ano de início', kind: 'year' },
  { key: 'end_year', label: 'Ano de conclusão', kind: 'year' },
  { key: 'activity_year', label: 'Ano da atividade', kind: 'year' },
] as const

export type FieldKey = (typeof FIELD_DEFS)[number]['key']
export const FIELD_KEYS: readonly FieldKey[] = FIELD_DEFS.map(def => def.key)
export const FIELD_LABEL: Record<FieldKey, string> = Object.fromEntries(
  FIELD_DEFS.map(def => [def.key, def.label]),
) as Record<FieldKey, string>

export const FIELD_STATES = [
  { value: 'present', label: 'Presente' },
  { value: 'absent', label: 'Ausente' },
  { value: 'illegible', label: 'Ilegível' },
] as const
export type FieldState = (typeof FIELD_STATES)[number]['value']

export const ASSOCIATIONS = [
  { value: 'sim', label: 'Sim' },
  { value: 'nao', label: 'Não' },
  { value: 'incerto', label: 'Incerto' },
] as const
export type Association = (typeof ASSOCIATIONS)[number]['value']

export const VERDICTS = [
  { value: 'VALIDADO', label: 'Validado' },
  { value: 'DIVERGENTE', label: 'Divergente' },
  { value: 'INCONCLUSIVO', label: 'Inconclusivo' },
] as const
export type Verdict = (typeof VERDICTS)[number]['value']

/** Motivos objetivos do rascunho do guia operacional; devem acompanhar `guide_version`. */
export const REASONS = [
  { code: 'CAMPOS_COMPATIVEIS', verdicts: ['VALIDADO'], label: 'Campos comparáveis compatíveis nos dois lados' },
  { code: 'EQUIVALENCIA_EXPLICITA', verdicts: ['VALIDADO'], label: 'Variação de forma prevista no guia (caixa, espaçamento, sigla com expansão)' },
  { code: 'VALOR_FACTUAL_DIFERENTE', verdicts: ['DIVERGENTE'], label: 'Valor factual presente nos dois lados e diferente (indique os campos)' },
  { code: 'DOCUMENTO_AUSENTE', verdicts: ['INCONCLUSIVO'], label: 'Não há documento para comparar' },
  { code: 'CAMPO_ESSENCIAL_AUSENTE', verdicts: ['INCONCLUSIVO'], label: 'Campo essencial ausente em um dos lados' },
  { code: 'CAMPO_ILEGIVEL', verdicts: ['INCONCLUSIVO'], label: 'Campo essencial ilegível no documento' },
  { code: 'EVIDENCIA_INSUFICIENTE', verdicts: ['INCONCLUSIVO'], label: 'Evidência insuficiente para decidir' },
  { code: 'ANALISE_CONTEXTUAL', verdicts: ['VALIDADO', 'DIVERGENTE', 'INCONCLUSIVO'], label: 'Análise contextual (nota com trecho documental obrigatória)' },
] as const
export type ReasonCode = (typeof REASONS)[number]['code']

export interface FieldAnnotation {
  state: FieldState | null
  value: string
}

export interface Phase1 {
  status: 'in_progress' | 'saved'
  absence_acknowledged: boolean
  fields: Record<FieldKey, FieldAnnotation>
  saved_at: string | null
}

export interface Phase2 {
  status: 'in_progress' | 'saved'
  association: Association | null
  verdict: Verdict | null
  reason_code: ReasonCode | null
  basis_fields: FieldKey[]
  note: string
  saved_at: string | null
}

export interface OcrCopyActionRecord {
  target: 'raw_text' | FieldKey
  source: 'ocr_raw_text' | 'ocr_regex_field'
  applied_to_field: boolean
  copied_value: string
  copied_at: string
  phase: 'phase1' | 'phase2'
}

export type OcrAssistanceStatus = 'not_requested' | 'displayed' | 'failed'

export interface CaseOcrAssistance {
  status: OcrAssistanceStatus
  assisted_before_completion: boolean
  requested_count: number
  first_requested_at: string | null
  last_accessed_at: string | null
  last_error: string | null
  document_id: string | null
  document_mime_type: DocumentMime | null
  document_sha256: string | null
  provider: string | null
  tesseract_version: string | null
  params: OcrParamsRecord | null
  ocr_raw_text: string | null
  regex_fields: Record<FieldKey, string | null> | null
  observable_copied_raw_text: boolean
  observable_copied_fields: FieldKey[]
  observable_copy_events: OcrCopyActionRecord[]
  observability_limit_note: string
}

export interface CaseAnnotation {
  case_id: string
  document_sha256: string | null
  xml_sha256: string
  phase1: Phase1
  phase2: Phase2 | null
  phase1_reopen_count: number
  ocr_assistance: CaseOcrAssistance
}

export interface ReviewDraft {
  package_version: string
  guide_version: string
  package_sha256: string
  reviewer: string
  review_mode: ReviewMode
  evaluation_condition: EvaluationCondition
  mode_opted_in_at: string | null
  migrated_from_export_version: typeof EXPORT_VERSION_V1 | null
  created_at: string
  updated_at: string
  cases: Record<string, CaseAnnotation>
}

export interface ReviewExport {
  export_version: typeof EXPORT_VERSION_V2
  kind: 'draft' | 'final'
  package_version: string
  guide_version: string
  package_sha256: string
  reviewer: string
  review_mode: ReviewMode
  evaluation_condition: EvaluationCondition
  mode_opted_in_at: string | null
  migrated_from_export_version: typeof EXPORT_VERSION_V1 | null
  methodology_note: string
  exported_at: string
  cases: CaseAnnotation[]
  annotation_sha256: string
}

export type CaseStage = 'not_started' | 'phase1' | 'phase2' | 'complete'

const STATES: readonly string[] = FIELD_STATES.map(item => item.value)
const ASSOCIATION_VALUES: readonly string[] = ASSOCIATIONS.map(item => item.value)
const VERDICT_VALUES: readonly string[] = VERDICTS.map(item => item.value)
const OCR_STATUS_VALUES: readonly OcrAssistanceStatus[] = ['not_requested', 'displayed', 'failed']

export function emptyPhase1(): Phase1 {
  const fields = Object.fromEntries(FIELD_KEYS.map(key => [key, { state: null, value: '' }])) as Record<FieldKey, FieldAnnotation>
  return { status: 'in_progress', absence_acknowledged: false, fields, saved_at: null }
}

export function emptyPhase2(): Phase2 {
  return { status: 'in_progress', association: null, verdict: null, reason_code: null, basis_fields: [], note: '', saved_at: null }
}

export function emptyOcrAssistance(): CaseOcrAssistance {
  return {
    status: 'not_requested',
    assisted_before_completion: false,
    requested_count: 0,
    first_requested_at: null,
    last_accessed_at: null,
    last_error: null,
    document_id: null,
    document_mime_type: null,
    document_sha256: null,
    provider: null,
    tesseract_version: null,
    params: null,
    ocr_raw_text: null,
    regex_fields: null,
    observable_copied_raw_text: false,
    observable_copied_fields: [],
    observable_copy_events: [],
    observability_limit_note: OBSERVABILITY_LIMIT_NOTE,
  }
}

export function emptyCase(pkgCase: PackageCase): CaseAnnotation {
  return {
    case_id: pkgCase.case_id,
    document_sha256: pkgCase.document?.sha256 ?? null,
    xml_sha256: pkgCase.xml.sha256,
    phase1: emptyPhase1(),
    phase2: null,
    phase1_reopen_count: 0,
    ocr_assistance: emptyOcrAssistance(),
  }
}

export function isCaseOcrAssisted(ocr: CaseOcrAssistance): boolean {
  return (
    ocr.status !== 'not_requested' ||
    ocr.assisted_before_completion ||
    ocr.requested_count > 0 ||
    ocr.observable_copied_raw_text ||
    ocr.observable_copied_fields.length > 0 ||
    ocr.observable_copy_events.length > 0
  )
}

export function hasAnyOcrAssistance(cases: Record<string, CaseAnnotation> | readonly CaseAnnotation[]): boolean {
  const list = Array.isArray(cases) ? cases : Object.values(cases)
  return list.some(item => isCaseOcrAssisted(item.ocr_assistance))
}

export function evaluationConditionFor(
  reviewMode: ReviewMode,
  cases: Record<string, CaseAnnotation> | readonly CaseAnnotation[],
): EvaluationCondition {
  return reviewMode === 'ocr_assisted' || hasAnyOcrAssistance(cases)
    ? 'ocr_assisted_human_review'
    : 'independent_unassisted_human_review'
}

export function methodologyNoteFor(condition: EvaluationCondition): string {
  return condition === 'ocr_assisted_human_review' ? METHODOLOGY_OCR_ASSISTED_NOTE : METHODOLOGY_UNASSISTED_NOTE
}

export function newDraft(
  pkg: AnnotationPackage,
  reviewer: string,
  now = new Date(),
  reviewMode: ReviewMode = 'unassisted',
): ReviewDraft {
  const stamp = now.toISOString()
  const cases = Object.fromEntries(pkg.cases.map(item => [item.case_id, emptyCase(item)]))
  return {
    package_version: pkg.package_version,
    guide_version: pkg.guide_version,
    package_sha256: pkg.package_sha256,
    reviewer: normalizeReviewer(reviewer),
    review_mode: reviewMode,
    evaluation_condition: evaluationConditionFor(reviewMode, cases),
    mode_opted_in_at: reviewMode === 'ocr_assisted' ? stamp : null,
    migrated_from_export_version: null,
    created_at: stamp,
    updated_at: stamp,
    cases,
  }
}

export function normalizeReviewer(name: string): string {
  return name.normalize('NFC').replace(/\s+/g, ' ').trim()
}

export function reviewerProblem(name: string): string | null {
  const normalized = normalizeReviewer(name)
  if (normalized.length < 2) return 'Informe o nome ou identificador do revisor (mínimo 2 caracteres).'
  if (normalized.length > 80) return 'Identificador do revisor: máximo de 80 caracteres.'
  return null
}

export function sameReviewer(a: string, b: string): boolean {
  return normalizeReviewer(a).toLowerCase() === normalizeReviewer(b).toLowerCase()
}

export function validatePhase1(phase: Phase1, hasDocument: boolean): string[] {
  const problems: string[] = []
  if (!hasDocument) {
    if (!phase.absence_acknowledged) problems.push('Confirme explicitamente que o caso não possui documento.')
    for (const def of FIELD_DEFS) {
      const field = phase.fields[def.key]
      if (field.state !== null || field.value !== '') problems.push(`${def.label}: sem documento não há transcrição.`)
    }
    return problems
  }
  for (const def of FIELD_DEFS) {
    const { state, value } = phase.fields[def.key]
    if (state === null) {
      problems.push(`${def.label}: escolha presente, ausente ou ilegível.`)
    } else if (state !== 'present') {
      if (value !== '') problems.push(`${def.label}: campo ${state === 'absent' ? 'ausente' : 'ilegível'} não pode ter valor transcrito.`)
    } else if (value.trim() === '') {
      problems.push(`${def.label}: transcreva o valor ou marque ausente/ilegível.`)
    } else if (value.length > MAX_VALUE_LENGTH) {
      problems.push(`${def.label}: máximo de ${MAX_VALUE_LENGTH} caracteres.`)
    } else if (def.kind === 'year' && !/^\d{4}$/.test(value.trim())) {
      problems.push(`${def.label}: informe o ano com quatro dígitos.`)
    }
  }
  return problems
}

export function reasonAllows(code: ReasonCode, verdict: Verdict): boolean {
  const reason = REASONS.find(item => item.code === code)
  return !!reason && (reason.verdicts as readonly string[]).includes(verdict)
}

export function validatePhase2(phase: Phase2, hasDocument: boolean): string[] {
  const problems: string[] = []
  if (phase.association === null) problems.push('Associação: escolha sim, não ou incerto.')
  if (phase.association === 'sim' && !hasDocument) problems.push('Associação "sim" é impossível sem documento.')
  if (phase.verdict === null) problems.push('Classe: escolha validado, divergente ou inconclusivo.')
  if (phase.reason_code === null) {
    problems.push('Motivo objetivo: escolha um motivo.')
  } else if (phase.verdict !== null && !reasonAllows(phase.reason_code, phase.verdict)) {
    problems.push('Motivo objetivo incompatível com a classe escolhida.')
  }
  if (phase.reason_code === 'DOCUMENTO_AUSENTE' && hasDocument) problems.push('Motivo "documento ausente" contradiz um caso com documento.')
  if (phase.reason_code === 'VALOR_FACTUAL_DIFERENTE' && phase.basis_fields.length === 0) problems.push('Indique ao menos um campo que fundamenta a diferença factual.')
  if (phase.reason_code === 'ANALISE_CONTEXTUAL' && phase.note.trim().length < MIN_CONTEXT_NOTE) {
    problems.push(`Análise contextual exige nota com trecho documental (mínimo ${MIN_CONTEXT_NOTE} caracteres).`)
  }
  if (phase.note.length > MAX_NOTE_LENGTH) problems.push(`Nota: máximo de ${MAX_NOTE_LENGTH} caracteres.`)
  return problems
}

function isPristine(phase: Phase1): boolean {
  return !phase.absence_acknowledged && FIELD_KEYS.every(key => phase.fields[key].state === null && phase.fields[key].value === '')
}

export function caseStage(annotation: CaseAnnotation): CaseStage {
  if (annotation.phase1.status !== 'saved') return isPristine(annotation.phase1) ? 'not_started' : 'phase1'
  if (annotation.phase2?.status !== 'saved') return 'phase2'
  return 'complete'
}

export function progressOf(draft: ReviewDraft) {
  const list = Object.values(draft.cases)
  const stages = list.map(caseStage)
  return {
    total: stages.length,
    phase1Saved: stages.filter(stage => stage === 'phase2' || stage === 'complete').length,
    complete: stages.filter(stage => stage === 'complete').length,
    ocrAssistedCases: list.filter(item => isCaseOcrAssisted(item.ocr_assistance)).length,
  }
}

function hasDocument(annotation: CaseAnnotation): boolean {
  return annotation.document_sha256 !== null
}

function annotationProblems(annotation: CaseAnnotation, strict: boolean): string[] {
  const problems: string[] = []
  if (annotation.phase1.status === 'saved' || strict) problems.push(...validatePhase1(annotation.phase1, hasDocument(annotation)))
  if (annotation.phase2 && (annotation.phase2.status === 'saved' || strict)) problems.push(...validatePhase2(annotation.phase2, hasDocument(annotation)))
  if (!hasDocument(annotation) && isCaseOcrAssisted(annotation.ocr_assistance)) {
    problems.push('Caso sem documento não pode registrar leitura OCR.')
  }
  return problems
}

export function incompleteCases(draft: ReviewDraft, pkg: AnnotationPackage): string[] {
  return pkg.cases
    .filter(item => {
      const annotation = draft.cases[item.case_id]
      return !annotation || caseStage(annotation) !== 'complete' || annotationProblems(annotation, true).length > 0
    })
    .map(item => item.case_id)
}

/* ---------- Transições determinísticas de auxílio OCR (assíncrono e rastreável) ---------- */

/**
 * Promove um rascunho de `unassisted` para `ocr_assisted` apenas por opt-in explícito,
 * preservando intactos os hashes do pacote, XML, documento e as transcrições em andamento.
 */
export function enableOcrAssistedMode(draft: ReviewDraft, now = new Date()): ReviewDraft {
  const stamp = now.toISOString()
  return {
    ...draft,
    review_mode: 'ocr_assisted',
    evaluation_condition: 'ocr_assisted_human_review',
    mode_opted_in_at: draft.mode_opted_in_at ?? stamp,
    updated_at: stamp,
  }
}

/**
 * Aplica o resultado assíncrono do OCR ao caso correspondente sem jamais preencher automaticamente
 * `phase1.fields` nem ocultar/alterar `xml_sha256`, `document_sha256` ou `package_sha256`.
 */
export function applyAsyncOcrResult(
  draft: ReviewDraft,
  caseId: string,
  response: VerifiedOcrResponse,
  now = new Date(),
): ReviewDraft {
  const target = draft.cases[caseId]
  if (!target) fail(`Caso desconhecido para resposta OCR: ${caseId}`)
  if (target.document_sha256 === null) fail(`Caso ${caseId} não possui comprovante para receber OCR.`)
  if (response.document_id !== caseId) {
    fail(`Resposta OCR descartada: document_id ${response.document_id} difere do caso ${caseId}.`)
  }
  if (response.sha256 !== target.document_sha256) {
    fail(`Resposta OCR descartada: hash SHA-256 não confere com o comprovante do caso ${caseId}.`)
  }

  const stamp = now.toISOString()
  const prevOcr = target.ocr_assistance
  const beforeCompletion = prevOcr.assisted_before_completion || caseStage(target) !== 'complete'

  const updatedCase: CaseAnnotation = {
    ...target,
    case_id: target.case_id,
    document_sha256: target.document_sha256,
    xml_sha256: target.xml_sha256,
    phase1: target.phase1,
    phase2: target.phase2,
    ocr_assistance: {
      ...prevOcr,
      status: 'displayed',
      assisted_before_completion: beforeCompletion,
      requested_count: prevOcr.requested_count + 1,
      first_requested_at: prevOcr.first_requested_at ?? response.accessed_at,
      last_accessed_at: response.accessed_at,
      last_error: null,
      document_id: response.document_id,
      document_mime_type: response.mime_type,
      document_sha256: response.sha256,
      provider: response.provider,
      tesseract_version: response.tesseract_version,
      params: { ...response.params },
      ocr_raw_text: response.ocr_text,
      regex_fields: { ...response.regex_fields },
      observability_limit_note: OBSERVABILITY_LIMIT_NOTE,
    },
  }

  const nextCases = { ...draft.cases, [caseId]: updatedCase }
  return {
    ...draft,
    review_mode: 'ocr_assisted',
    evaluation_condition: 'ocr_assisted_human_review',
    mode_opted_in_at: draft.mode_opted_in_at ?? stamp,
    updated_at: stamp,
    cases: nextCases,
  }
}

export function applyAsyncOcrFailure(
  draft: ReviewDraft,
  caseId: string,
  errorMessage: string,
  now = new Date(),
): ReviewDraft {
  const target = draft.cases[caseId]
  if (!target) fail(`Caso desconhecido para falha OCR: ${caseId}`)
  if (target.document_sha256 === null) fail(`Caso ${caseId} não possui comprovante para OCR.`)

  const stamp = now.toISOString()
  const prevOcr = target.ocr_assistance
  const beforeCompletion = prevOcr.assisted_before_completion || caseStage(target) !== 'complete'

  const updatedCase: CaseAnnotation = {
    ...target,
    ocr_assistance: {
      ...prevOcr,
      status: prevOcr.status === 'displayed' ? 'displayed' : 'failed',
      assisted_before_completion: beforeCompletion,
      requested_count: prevOcr.requested_count + 1,
      first_requested_at: prevOcr.first_requested_at ?? stamp,
      last_accessed_at: stamp,
      last_error: errorMessage.slice(0, MAX_VALUE_LENGTH),
      document_id: prevOcr.document_id ?? caseId,
      document_sha256: prevOcr.document_sha256 ?? target.document_sha256,
      observability_limit_note: OBSERVABILITY_LIMIT_NOTE,
    },
  }

  return {
    ...draft,
    review_mode: 'ocr_assisted',
    evaluation_condition: 'ocr_assisted_human_review',
    mode_opted_in_at: draft.mode_opted_in_at ?? stamp,
    updated_at: stamp,
    cases: { ...draft.cases, [caseId]: updatedCase },
  }
}

export function recordOcrCopyRawText(annotation: CaseAnnotation, now = new Date()): CaseAnnotation {
  const ocr = annotation.ocr_assistance
  if (ocr.status !== 'displayed' || ocr.ocr_raw_text === null) {
    fail('Não há texto OCR disponível para copiar neste caso.')
  }
  const stamp = now.toISOString()
  const event: OcrCopyActionRecord = {
    target: 'raw_text',
    source: 'ocr_raw_text',
    applied_to_field: false,
    copied_value: ocr.ocr_raw_text.slice(0, MAX_VALUE_LENGTH),
    copied_at: stamp,
    phase: annotation.phase1.status === 'saved' ? 'phase2' : 'phase1',
  }
  const events = [...ocr.observable_copy_events, event].slice(-MAX_COPY_EVENTS)
  return {
    ...annotation,
    ocr_assistance: {
      ...ocr,
      assisted_before_completion: ocr.assisted_before_completion || caseStage(annotation) !== 'complete',
      observable_copied_raw_text: true,
      observable_copy_events: events,
    },
  }
}

/**
 * Registra cópia observável de um campo recortado por `OCRRegex` e, quando `applyToField=true`
 * na Fase 1 aberta, preenche somente o campo clicado pelo usuário (`state: 'present'`).
 * Campos com valor `null` na RegEx jamais podem ser copiados nem marcados como `absent`.
 */
export function recordOcrCopyField(
  annotation: CaseAnnotation,
  fieldKey: FieldKey,
  applyToField: boolean,
  now = new Date(),
): CaseAnnotation {
  const ocr = annotation.ocr_assistance
  if (ocr.status !== 'displayed' || !ocr.regex_fields) {
    fail('Leitura OCR ainda não disponível neste caso.')
  }
  const extractedValue = ocr.regex_fields[fieldKey]
  if (extractedValue === null || extractedValue.trim() === '') {
    fail(`${FIELD_LABEL[fieldKey]}: valor não extraído pela RegEx do OCR; nada é preenchido nem marcado como ausente.`)
  }
  if (applyToField && annotation.phase1.status === 'saved') {
    fail('A fase 1 está travada; reabra a fase 1 se precisar alterar um campo transcrito.')
  }

  const trimmed = extractedValue.trim().slice(0, MAX_VALUE_LENGTH)
  const stamp = now.toISOString()
  const event: OcrCopyActionRecord = {
    target: fieldKey,
    source: 'ocr_regex_field',
    applied_to_field: applyToField,
    copied_value: trimmed,
    copied_at: stamp,
    phase: annotation.phase1.status === 'saved' ? 'phase2' : 'phase1',
  }
  const copiedFields = ocr.observable_copied_fields.includes(fieldKey)
    ? ocr.observable_copied_fields
    : [...ocr.observable_copied_fields, fieldKey]
  const events = [...ocr.observable_copy_events, event].slice(-MAX_COPY_EVENTS)

  const nextPhase1: Phase1 = applyToField
    ? {
        ...annotation.phase1,
        fields: {
          ...annotation.phase1.fields,
          [fieldKey]: { state: 'present', value: trimmed },
        },
      }
    : annotation.phase1

  return {
    ...annotation,
    phase1: nextPhase1,
    ocr_assistance: {
      ...ocr,
      assisted_before_completion: ocr.assisted_before_completion || caseStage(annotation) !== 'complete',
      observable_copied_fields: copiedFields,
      observable_copy_events: events,
    },
  }
}

/** Permite rejeitar/limpar manualmente um valor inserido na Fase 1, preservando o histórico de auditoria OCR. */
export function rejectOcrFieldSuggestion(annotation: CaseAnnotation, fieldKey: FieldKey): CaseAnnotation {
  if (annotation.phase1.status === 'saved') {
    fail('A fase 1 está travada.')
  }
  return {
    ...annotation,
    phase1: {
      ...annotation.phase1,
      fields: {
        ...annotation.phase1.fields,
        [fieldKey]: { state: null, value: '' },
      },
    },
  }
}

/* ---------- Armazenamento local separado por modo (preserva originais e v1) ---------- */

function reviewerStorageToken(reviewer: string): string {
  return encodeURIComponent(normalizeReviewer(reviewer).toLowerCase())
}

function storageKeyV1(packageSha: string, reviewer: string): string {
  return `${STORAGE_PREFIX_V1}:${packageSha}:${reviewerStorageToken(reviewer)}`
}

function storageKeyV2(packageSha: string, reviewer: string, mode: ReviewMode): string {
  return `${STORAGE_PREFIX_V2}:${packageSha}:${reviewerStorageToken(reviewer)}:${mode}`
}

export type StoredDraft =
  | { kind: 'none' }
  | { kind: 'ok'; draft: ReviewDraft }
  | { kind: 'corrupt'; message: string }

export interface StoredModesSummary {
  unassisted: StoredDraft
  ocr_assisted: StoredDraft
}

export function loadStoredDraft(
  pkg: AnnotationPackage,
  reviewer: string,
  mode: ReviewMode = 'unassisted',
): StoredDraft {
  try {
    const v2Text = globalThis.localStorage.getItem(storageKeyV2(pkg.package_sha256, reviewer, mode))
    if (v2Text !== null) {
      const draft = draftFromObject(JSON.parse(v2Text), pkg, reviewer)
      if (draft.review_mode !== mode) {
        return {
          kind: 'corrupt',
          message: `Modo salvo (${draft.review_mode}) difere do slot esperado (${mode}).`,
        }
      }
      return { kind: 'ok', draft }
    }
    if (mode === 'unassisted') {
      const legacyV1Text = globalThis.localStorage.getItem(storageKeyV1(pkg.package_sha256, reviewer))
      if (legacyV1Text !== null) {
        const migrated = draftFromObject(JSON.parse(legacyV1Text), pkg, reviewer)
        return { kind: 'ok', draft: migrated }
      }
    }
    return { kind: 'none' }
  } catch (error) {
    return { kind: 'corrupt', message: error instanceof Error ? error.message : 'Rascunho local ilegível.' }
  }
}

export function inspectStoredModes(pkg: AnnotationPackage, reviewer: string): StoredModesSummary {
  return {
    unassisted: loadStoredDraft(pkg, reviewer, 'unassisted'),
    ocr_assisted: loadStoredDraft(pkg, reviewer, 'ocr_assisted'),
  }
}

export function persistDraft(draft: ReviewDraft): boolean {
  try {
    globalThis.localStorage.setItem(
      storageKeyV2(draft.package_sha256, draft.reviewer, draft.review_mode),
      JSON.stringify(draft),
    )
    return true
  } catch {
    return false
  }
}

/**
 * Preserva o rascunho `unassisted` original em seu slot próprio antes de migrar a sessão ativa
 * para `ocr_assisted`, evitando mistura silenciosa ou perda do estado manual anterior.
 */
export function optInDraftToOcrAssisted(
  draft: ReviewDraft,
  now = new Date(),
): { upgraded: ReviewDraft; unassistedPreserved: boolean; storageOk: boolean } {
  let unassistedPreserved = true
  if (draft.review_mode === 'unassisted') {
    unassistedPreserved = persistDraft(draft)
  }
  const upgraded = enableOcrAssistedMode(draft, now)
  const storageOk = persistDraft(upgraded)
  return { upgraded, unassistedPreserved, storageOk }
}

export function discardStoredDraft(pkg: AnnotationPackage, reviewer: string, mode?: ReviewMode): void {
  try {
    if (!mode || mode === 'unassisted') {
      globalThis.localStorage.removeItem(storageKeyV2(pkg.package_sha256, reviewer, 'unassisted'))
      globalThis.localStorage.removeItem(storageKeyV1(pkg.package_sha256, reviewer))
    }
    if (!mode || mode === 'ocr_assisted') {
      globalThis.localStorage.removeItem(storageKeyV2(pkg.package_sha256, reviewer, 'ocr_assisted'))
    }
  } catch {
    /* Armazenamento indisponível: nada a descartar. */
  }
}

/* ---------- Validação de estruturas importadas (v1 legada + v2 assistida) ---------- */

function parseTimestamp(value: unknown, path: string): string {
  const text = expectString(value, path, 64)
  if (Number.isNaN(Date.parse(text))) fail(`${path}: data/hora inválida`)
  return text
}

function parsePhase1(value: unknown, path: string): Phase1 {
  const raw = expectExactKeys(value, ['status', 'absence_acknowledged', 'fields', 'saved_at'], path)
  if (raw.status !== 'in_progress' && raw.status !== 'saved') fail(`${path}.status inválido`)
  if (typeof raw.absence_acknowledged !== 'boolean') fail(`${path}.absence_acknowledged: esperado booleano`)
  const fieldsRaw = expectExactKeys(raw.fields, FIELD_KEYS, `${path}.fields`)
  const fields = {} as Record<FieldKey, FieldAnnotation>
  for (const key of FIELD_KEYS) {
    const item = expectExactKeys(fieldsRaw[key], ['state', 'value'], `${path}.fields.${key}`)
    if (item.state !== null && !STATES.includes(item.state as string)) fail(`${path}.fields.${key}.state inválido`)
    const text = expectString(item.value, `${path}.fields.${key}.value`, MAX_VALUE_LENGTH)
    if (item.state !== 'present' && text !== '') fail(`${path}.fields.${key}: valor só é permitido com estado "present"`)
    fields[key] = { state: item.state as FieldState | null, value: text }
  }
  const savedAt = raw.saved_at === null ? null : parseTimestamp(raw.saved_at, `${path}.saved_at`)
  if ((raw.status === 'saved') !== (savedAt !== null)) fail(`${path}: saved_at deve existir exatamente quando status=saved`)
  return { status: raw.status, absence_acknowledged: raw.absence_acknowledged, fields, saved_at: savedAt }
}

function parsePhase2(value: unknown, path: string): Phase2 {
  const raw = expectExactKeys(value, ['status', 'association', 'verdict', 'reason_code', 'basis_fields', 'note', 'saved_at'], path)
  if (raw.status !== 'in_progress' && raw.status !== 'saved') fail(`${path}.status inválido`)
  if (raw.association !== null && !ASSOCIATION_VALUES.includes(raw.association as string)) fail(`${path}.association inválida`)
  if (raw.verdict !== null && !VERDICT_VALUES.includes(raw.verdict as string)) fail(`${path}.verdict inválida`)
  if (raw.reason_code !== null && !REASONS.some(item => item.code === raw.reason_code)) fail(`${path}.reason_code desconhecido`)
  if (!Array.isArray(raw.basis_fields) || raw.basis_fields.some(item => !FIELD_KEYS.includes(item as FieldKey))) fail(`${path}.basis_fields inválido`)
  const savedAt = raw.saved_at === null ? null : parseTimestamp(raw.saved_at, `${path}.saved_at`)
  if ((raw.status === 'saved') !== (savedAt !== null)) fail(`${path}: saved_at deve existir exatamente quando status=saved`)
  return {
    status: raw.status,
    association: raw.association as Association | null,
    verdict: raw.verdict as Verdict | null,
    reason_code: raw.reason_code as ReasonCode | null,
    basis_fields: [...new Set(raw.basis_fields as FieldKey[])],
    note: expectString(raw.note, `${path}.note`, MAX_NOTE_LENGTH),
    saved_at: savedAt,
  }
}

function parseCopyEvent(value: unknown, path: string): OcrCopyActionRecord {
  const raw = expectExactKeys(
    value,
    ['target', 'source', 'applied_to_field', 'copied_value', 'copied_at', 'phase'],
    path,
  )
  const target = raw.target
  if (target !== 'raw_text' && !FIELD_KEYS.includes(target as FieldKey)) {
    fail(`${path}.target inválido`)
  }
  if (raw.source !== 'ocr_raw_text' && raw.source !== 'ocr_regex_field') {
    fail(`${path}.source inválido`)
  }
  if (typeof raw.applied_to_field !== 'boolean') {
    fail(`${path}.applied_to_field: esperado booleano`)
  }
  if (raw.phase !== 'phase1' && raw.phase !== 'phase2') {
    fail(`${path}.phase inválido`)
  }
  return {
    target: target as 'raw_text' | FieldKey,
    source: raw.source,
    applied_to_field: raw.applied_to_field,
    copied_value: expectString(raw.copied_value, `${path}.copied_value`, MAX_VALUE_LENGTH),
    copied_at: parseTimestamp(raw.copied_at, `${path}.copied_at`),
    phase: raw.phase,
  }
}

function parseCaseOcrAssistance(value: unknown, path: string, pkgCase: PackageCase): CaseOcrAssistance {
  const raw = expectExactKeys(
    value,
    [
      'status',
      'assisted_before_completion',
      'requested_count',
      'first_requested_at',
      'last_accessed_at',
      'last_error',
      'document_id',
      'document_mime_type',
      'document_sha256',
      'provider',
      'tesseract_version',
      'params',
      'ocr_raw_text',
      'regex_fields',
      'observable_copied_raw_text',
      'observable_copied_fields',
      'observable_copy_events',
      'observability_limit_note',
    ],
    path,
  )
  if (!OCR_STATUS_VALUES.includes(raw.status as OcrAssistanceStatus)) fail(`${path}.status inválido`)
  if (typeof raw.assisted_before_completion !== 'boolean') fail(`${path}.assisted_before_completion: esperado booleano`)
  const requestedCount = raw.requested_count
  if (typeof requestedCount !== 'number' || !Number.isInteger(requestedCount) || requestedCount < 0 || requestedCount > 10_000) {
    fail(`${path}.requested_count inválido`)
  }
  const firstRequestedAt = raw.first_requested_at === null ? null : parseTimestamp(raw.first_requested_at, `${path}.first_requested_at`)
  const lastAccessedAt = raw.last_accessed_at === null ? null : parseTimestamp(raw.last_accessed_at, `${path}.last_accessed_at`)
  const lastError = expectNullableString(raw.last_error, `${path}.last_error`, MAX_VALUE_LENGTH)
  const docId = expectNullableString(raw.document_id, `${path}.document_id`, 120)
  if (docId !== null && docId !== pkgCase.case_id) {
    fail(`${path}.document_id (${docId}) não corresponde ao caso ${pkgCase.case_id}`)
  }
  const docMime = expectNullableString(raw.document_mime_type, `${path}.document_mime_type`, 64)
  if (docMime !== null) {
    if (!(DOCUMENT_MIME_TYPES as readonly string[]).includes(docMime)) fail(`${path}.document_mime_type inválido`)
    if (pkgCase.document && docMime !== pkgCase.document.mime_type) {
      fail(`${path}.document_mime_type difere do comprovante do pacote`)
    }
  }
  const docSha = raw.document_sha256 === null ? null : expectSha256(raw.document_sha256, `${path}.document_sha256`)
  if (docSha !== null && docSha !== (pkgCase.document?.sha256 ?? null)) {
    fail(`${path}.document_sha256 não confere com o comprovante do pacote`)
  }
  const provider = expectNullableString(raw.provider, `${path}.provider`, 80)
  const tesseractVersion = expectNullableString(raw.tesseract_version, `${path}.tesseract_version`, 200)
  const params = raw.params === null ? null : parseOcrParams(raw.params, `${path}.params`)
  const ocrRawText = expectNullableString(raw.ocr_raw_text, `${path}.ocr_raw_text`, MAX_OCR_TEXT_LENGTH)
  const regexFields = raw.regex_fields === null ? null : parseOcrRegexFields(raw.regex_fields, `${path}.regex_fields`)
  if (typeof raw.observable_copied_raw_text !== 'boolean') {
    fail(`${path}.observable_copied_raw_text: esperado booleano`)
  }
  if (
    !Array.isArray(raw.observable_copied_fields) ||
    raw.observable_copied_fields.some(item => !FIELD_KEYS.includes(item as FieldKey))
  ) {
    fail(`${path}.observable_copied_fields inválido`)
  }
  if (!Array.isArray(raw.observable_copy_events) || raw.observable_copy_events.length > MAX_COPY_EVENTS) {
    fail(`${path}.observable_copy_events inválido`)
  }
  const copyEvents = raw.observable_copy_events.map((item, idx) =>
    parseCopyEvent(item, `${path}.observable_copy_events[${idx}]`),
  )
  const limitNote = expectString(raw.observability_limit_note, `${path}.observability_limit_note`, 500)

  if (raw.status === 'not_requested' && requestedCount > 0) {
    fail(`${path}: status=not_requested incompatível com requested_count > 0`)
  }
  if (raw.status === 'displayed' && (requestedCount < 1 || docSha === null || ocrRawText === null || regexFields === null)) {
    fail(`${path}: status=displayed exige requested_count >= 1, document_sha256, ocr_raw_text e regex_fields`)
  }

  return {
    status: raw.status as OcrAssistanceStatus,
    assisted_before_completion: raw.assisted_before_completion,
    requested_count: requestedCount,
    first_requested_at: firstRequestedAt,
    last_accessed_at: lastAccessedAt,
    last_error: lastError,
    document_id: docId,
    document_mime_type: docMime as DocumentMime | null,
    document_sha256: docSha,
    provider,
    tesseract_version: tesseractVersion,
    params,
    ocr_raw_text: ocrRawText,
    regex_fields: regexFields,
    observable_copied_raw_text: raw.observable_copied_raw_text,
    observable_copied_fields: [...new Set(raw.observable_copied_fields as FieldKey[])],
    observable_copy_events: copyEvents,
    observability_limit_note: limitNote,
  }
}

function parseCaseAnnotation(value: unknown, path: string, pkgCase: PackageCase, allowLegacyV1: boolean): CaseAnnotation {
  if (!isPlainObject(value)) fail(`${path}: esperado objeto`)
  const hasOcrField = 'ocr_assistance' in value
  if (!hasOcrField && !allowLegacyV1) {
    fail(`${path}: chave ausente: ocr_assistance`)
  }
  const expectedKeys = hasOcrField
    ? (['case_id', 'document_sha256', 'xml_sha256', 'phase1', 'phase2', 'phase1_reopen_count', 'ocr_assistance'] as const)
    : (['case_id', 'document_sha256', 'xml_sha256', 'phase1', 'phase2', 'phase1_reopen_count'] as const)
  const raw = expectExactKeys(value, expectedKeys, path)
  if (raw.case_id !== pkgCase.case_id) fail(`${path}: case_id fora da ordem do pacote`)
  const documentSha = raw.document_sha256 === null ? null : expectSha256(raw.document_sha256, `${path}.document_sha256`)
  if (documentSha !== (pkgCase.document?.sha256 ?? null)) fail(`${pkgCase.case_id}: hash do documento não confere com o pacote carregado`)
  if (expectSha256(raw.xml_sha256, `${path}.xml_sha256`) !== pkgCase.xml.sha256) fail(`${pkgCase.case_id}: hash do XML não confere com o pacote carregado`)
  const reopen = raw.phase1_reopen_count
  if (typeof reopen !== 'number' || !Number.isInteger(reopen) || reopen < 0 || reopen > 1000) fail(`${path}.phase1_reopen_count inválido`)
  const phase1 = parsePhase1(raw.phase1, `${path}.phase1`)
  const phase2 = raw.phase2 === null ? null : parsePhase2(raw.phase2, `${path}.phase2`)
  if (phase2 && phase1.status !== 'saved') fail(`${pkgCase.case_id}: fase 2 existe sem fase 1 salva`)
  const ocrAssistance = hasOcrField
    ? parseCaseOcrAssistance(raw.ocr_assistance, `${path}.ocr_assistance`, pkgCase)
    : emptyOcrAssistance()
  const annotation: CaseAnnotation = {
    case_id: pkgCase.case_id,
    document_sha256: documentSha,
    xml_sha256: pkgCase.xml.sha256,
    phase1,
    phase2,
    phase1_reopen_count: reopen,
    ocr_assistance: ocrAssistance,
  }
  const problems = annotationProblems(annotation, false)
  if (problems.length) fail(`${pkgCase.case_id}: fase salva inválida — ${problems[0]}`)
  return annotation
}

function draftFromObject(value: unknown, pkg: AnnotationPackage, reviewer: string): ReviewDraft {
  scanForbiddenKeys(value, '$', true)
  if (!isPlainObject(value)) fail('rascunho: esperado objeto')
  const isV2 = 'review_mode' in value
  const expectedTopKeys = isV2
    ? ([
        'package_version',
        'guide_version',
        'package_sha256',
        'reviewer',
        'review_mode',
        'evaluation_condition',
        'mode_opted_in_at',
        'migrated_from_export_version',
        'created_at',
        'updated_at',
        'cases',
      ] as const)
    : (['package_version', 'guide_version', 'package_sha256', 'reviewer', 'created_at', 'updated_at', 'cases'] as const)

  const raw = expectExactKeys(value, expectedTopKeys, 'rascunho')
  if (raw.package_version !== pkg.package_version) fail('package_version do rascunho difere do pacote carregado.')
  if (raw.guide_version !== pkg.guide_version) fail('guide_version do rascunho difere do pacote carregado.')
  if (raw.package_sha256 !== pkg.package_sha256) fail('Rascunho pertence a outro pacote (hash diferente).')
  const owner = expectString(raw.reviewer, 'reviewer', 200)
  if (!sameReviewer(owner, reviewer)) fail('Rascunho pertence a outro revisor; não é carregado.')

  const casesRaw = expectExactKeys(raw.cases, pkg.cases.map(item => item.case_id), 'rascunho.cases')
  const cases: Record<string, CaseAnnotation> = {}
  for (const item of pkg.cases) {
    cases[item.case_id] = parseCaseAnnotation(casesRaw[item.case_id], `cases.${item.case_id}`, item, !isV2)
  }

  let reviewMode: ReviewMode = 'unassisted'
  let modeOptedInAt: string | null = null
  let migratedFrom: typeof EXPORT_VERSION_V1 | null = isV2 ? null : EXPORT_VERSION_V1

  if (isV2) {
    if (raw.review_mode !== 'unassisted' && raw.review_mode !== 'ocr_assisted') {
      fail('rascunho.review_mode inválido')
    }
    reviewMode = raw.review_mode
    if (
      raw.evaluation_condition !== 'independent_unassisted_human_review' &&
      raw.evaluation_condition !== 'ocr_assisted_human_review'
    ) {
      fail('rascunho.evaluation_condition inválido')
    }
    modeOptedInAt = raw.mode_opted_in_at === null ? null : parseTimestamp(raw.mode_opted_in_at, 'mode_opted_in_at')
    if (raw.migrated_from_export_version !== null && raw.migrated_from_export_version !== EXPORT_VERSION_V1) {
      fail('rascunho.migrated_from_export_version inválido')
    }
    migratedFrom = raw.migrated_from_export_version
    if (reviewMode === 'unassisted' && hasAnyOcrAssistance(cases)) {
      fail('Inconsistência metodológica: rascunho marcado como "unassisted", mas contém registros de auxílio OCR.')
    }
    const expectedCondition = evaluationConditionFor(reviewMode, cases)
    if (raw.evaluation_condition !== expectedCondition) {
      fail(`Inconsistência metodológica: evaluation_condition (${String(raw.evaluation_condition)}) não corresponde ao modo/casos (${expectedCondition}).`)
    }
  }

  return {
    package_version: pkg.package_version,
    guide_version: pkg.guide_version,
    package_sha256: pkg.package_sha256,
    reviewer: normalizeReviewer(owner),
    review_mode: reviewMode,
    evaluation_condition: evaluationConditionFor(reviewMode, cases),
    mode_opted_in_at: modeOptedInAt,
    migrated_from_export_version: migratedFrom,
    created_at: parseTimestamp(raw.created_at, 'created_at'),
    updated_at: parseTimestamp(raw.updated_at, 'updated_at'),
    cases,
  }
}

/* ---------- Exportação / importação de arquivos (v2 + migração compatível v1) ---------- */

export async function buildExport(
  draft: ReviewDraft,
  pkg: AnnotationPackage,
  kind: 'draft' | 'final',
  now = new Date(),
): Promise<ReviewExport> {
  if (kind === 'final') {
    const pending = incompleteCases(draft, pkg)
    if (pending.length) fail(`Exportação final bloqueada: ${pending.length} caso(s) incompleto(s) (${pending.join(', ')}).`)
  }
  const cases = pkg.cases.map(item => draft.cases[item.case_id])
  const anyAssisted = hasAnyOcrAssistance(cases)
  const effectiveMode: ReviewMode = draft.review_mode === 'ocr_assisted' || anyAssisted ? 'ocr_assisted' : 'unassisted'
  const condition = evaluationConditionFor(effectiveMode, cases)
  const body: Omit<ReviewExport, 'annotation_sha256'> = {
    export_version: EXPORT_VERSION_V2,
    kind,
    package_version: pkg.package_version,
    guide_version: pkg.guide_version,
    package_sha256: pkg.package_sha256,
    reviewer: normalizeReviewer(draft.reviewer),
    review_mode: effectiveMode,
    evaluation_condition: condition,
    mode_opted_in_at: draft.mode_opted_in_at,
    migrated_from_export_version: draft.migrated_from_export_version,
    methodology_note: methodologyNoteFor(condition),
    exported_at: now.toISOString(),
    cases,
  }
  return { ...body, annotation_sha256: await canonicalSha256(body) }
}

export interface ParseExportOptions {
  expectedMode?: ReviewMode
  allowModeSwitch?: boolean
}

export async function parseExport(
  text: string,
  pkg: AnnotationPackage,
  reviewer: string,
  options?: ParseExportOptions,
): Promise<ReviewDraft> {
  let raw: unknown
  try {
    raw = JSON.parse(text)
  } catch {
    return fail('Arquivo não é JSON válido.')
  }
  scanForbiddenKeys(raw, '$', true)
  if (!isPlainObject(raw)) fail('exportação: esperado objeto')

  const version = raw.export_version
  if (version !== EXPORT_VERSION_V1 && version !== EXPORT_VERSION_V2) {
    fail(`export_version não suportada: ${String(version)}`)
  }

  const topKeys =
    version === EXPORT_VERSION_V1
      ? (['export_version', 'kind', 'package_version', 'guide_version', 'package_sha256', 'reviewer', 'exported_at', 'cases', 'annotation_sha256'] as const)
      : ([
          'export_version',
          'kind',
          'package_version',
          'guide_version',
          'package_sha256',
          'reviewer',
          'review_mode',
          'evaluation_condition',
          'mode_opted_in_at',
          'migrated_from_export_version',
          'methodology_note',
          'exported_at',
          'cases',
          'annotation_sha256',
        ] as const)

  const top = expectExactKeys(raw, topKeys, 'exportação')
  if (top.kind !== 'draft' && top.kind !== 'final') fail('kind deve ser "draft" ou "final".')
  const { annotation_sha256: claimed, ...body } = top
  if ((await canonicalSha256(body)) !== expectSha256(claimed, 'annotation_sha256')) {
    fail('annotation_sha256 não confere: arquivo alterado ou corrompido.')
  }
  if (!Array.isArray(top.cases)) fail('cases: esperado lista')
  if (top.cases.length !== pkg.cases.length) fail('Quantidade de casos difere do pacote carregado.')

  const owner = expectString(top.reviewer, 'reviewer', 200)
  const exportedAt = parseTimestamp(top.exported_at, 'exported_at')

  const draftObj =
    version === EXPORT_VERSION_V1
      ? {
          package_version: top.package_version,
          guide_version: top.guide_version,
          package_sha256: top.package_sha256,
          reviewer: owner,
          created_at: exportedAt,
          updated_at: exportedAt,
          cases: Object.fromEntries(top.cases.map(item => [isPlainObject(item) ? String(item.case_id) : '', item])),
        }
      : {
          package_version: top.package_version,
          guide_version: top.guide_version,
          package_sha256: top.package_sha256,
          reviewer: owner,
          review_mode: top.review_mode,
          evaluation_condition: top.evaluation_condition,
          mode_opted_in_at: top.mode_opted_in_at,
          migrated_from_export_version: top.migrated_from_export_version,
          created_at: exportedAt,
          updated_at: exportedAt,
          cases: Object.fromEntries(top.cases.map(item => [isPlainObject(item) ? String(item.case_id) : '', item])),
        }

  const draft = draftFromObject(draftObj, pkg, reviewer)
  if (top.kind === 'final') {
    const pending = incompleteCases(draft, pkg)
    if (pending.length) fail('Arquivo marcado como final, mas há casos incompletos.')
  }

  if (options?.expectedMode && draft.review_mode !== options.expectedMode && !options.allowModeSwitch) {
    const importedLabel = draft.review_mode === 'ocr_assisted' ? 'revisão assistida por OCR' : 'revisão manual sem auxílio'
    const currentLabel = options.expectedMode === 'ocr_assisted' ? 'revisão assistida por OCR' : 'revisão manual sem auxílio'
    fail(
      `Importação bloqueada para não misturar rascunhos silenciosamente: o arquivo importado é de "${importedLabel}" (${draft.review_mode}), mas a sessão ativa está em "${currentLabel}" (${options.expectedMode}). Marque a confirmação de troca de modo ou troque o modo da sessão.`,
    )
  }

  return draft
}

export function exportFilename(draft: ReviewDraft, kind: 'draft' | 'final'): string {
  const slug = normalizeReviewer(draft.reviewer).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'revisor'
  const modeSuffix = draft.review_mode === 'ocr_assisted' || hasAnyOcrAssistance(draft.cases) ? '-ocr-assistido' : ''
  return `anotacao-${slug}-${draft.package_sha256.slice(0, 8)}${modeSuffix}-${kind}.json`
}
