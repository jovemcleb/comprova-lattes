import { canonicalSha256 } from './canonical'
import {
  expectExactKeys,
  expectSha256,
  expectString,
  fail,
  isPlainObject,
  scanForbiddenKeys,
  type AnnotationPackage,
  type PackageCase,
} from './package'

export const EXPORT_VERSION = 'annotation-export-v1'
const STORAGE_PREFIX = 'comprova-lattes:annotation-draft:v1'
const MAX_VALUE_LENGTH = 500
const MAX_NOTE_LENGTH = 2000
const MIN_CONTEXT_NOTE = 10

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

export interface CaseAnnotation {
  case_id: string
  document_sha256: string | null
  xml_sha256: string
  phase1: Phase1
  phase2: Phase2 | null
  phase1_reopen_count: number
}

export interface ReviewDraft {
  package_version: string
  guide_version: string
  package_sha256: string
  reviewer: string
  created_at: string
  updated_at: string
  cases: Record<string, CaseAnnotation>
}

export interface ReviewExport {
  export_version: typeof EXPORT_VERSION
  kind: 'draft' | 'final'
  package_version: string
  guide_version: string
  package_sha256: string
  reviewer: string
  exported_at: string
  cases: CaseAnnotation[]
  annotation_sha256: string
}

export type CaseStage = 'not_started' | 'phase1' | 'phase2' | 'complete'

const STATES: readonly string[] = FIELD_STATES.map(item => item.value)
const ASSOCIATION_VALUES: readonly string[] = ASSOCIATIONS.map(item => item.value)
const VERDICT_VALUES: readonly string[] = VERDICTS.map(item => item.value)

export function emptyPhase1(): Phase1 {
  const fields = Object.fromEntries(FIELD_KEYS.map(key => [key, { state: null, value: '' }])) as Record<FieldKey, FieldAnnotation>
  return { status: 'in_progress', absence_acknowledged: false, fields, saved_at: null }
}

export function emptyPhase2(): Phase2 {
  return { status: 'in_progress', association: null, verdict: null, reason_code: null, basis_fields: [], note: '', saved_at: null }
}

export function emptyCase(pkgCase: PackageCase): CaseAnnotation {
  return {
    case_id: pkgCase.case_id,
    document_sha256: pkgCase.document?.sha256 ?? null,
    xml_sha256: pkgCase.xml.sha256,
    phase1: emptyPhase1(),
    phase2: null,
    phase1_reopen_count: 0,
  }
}

export function newDraft(pkg: AnnotationPackage, reviewer: string, now = new Date()): ReviewDraft {
  const stamp = now.toISOString()
  return {
    package_version: pkg.package_version,
    guide_version: pkg.guide_version,
    package_sha256: pkg.package_sha256,
    reviewer,
    created_at: stamp,
    updated_at: stamp,
    cases: Object.fromEntries(pkg.cases.map(item => [item.case_id, emptyCase(item)])),
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
  const stages = Object.values(draft.cases).map(caseStage)
  return {
    total: stages.length,
    phase1Saved: stages.filter(stage => stage === 'phase2' || stage === 'complete').length,
    complete: stages.filter(stage => stage === 'complete').length,
  }
}

function hasDocument(annotation: CaseAnnotation): boolean {
  return annotation.document_sha256 !== null
}

function annotationProblems(annotation: CaseAnnotation, strict: boolean): string[] {
  const problems: string[] = []
  if (annotation.phase1.status === 'saved' || strict) problems.push(...validatePhase1(annotation.phase1, hasDocument(annotation)))
  if (annotation.phase2 && (annotation.phase2.status === 'saved' || strict)) problems.push(...validatePhase2(annotation.phase2, hasDocument(annotation)))
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

/* ---------- Armazenamento local (por revisor e hash do pacote) ---------- */

function storageKey(packageSha: string, reviewer: string): string {
  return `${STORAGE_PREFIX}:${packageSha}:${encodeURIComponent(normalizeReviewer(reviewer).toLowerCase())}`
}

export type StoredDraft =
  | { kind: 'none' }
  | { kind: 'ok'; draft: ReviewDraft }
  | { kind: 'corrupt'; message: string }

export function loadStoredDraft(pkg: AnnotationPackage, reviewer: string): StoredDraft {
  try {
    const text = globalThis.localStorage.getItem(storageKey(pkg.package_sha256, reviewer))
    if (text === null) return { kind: 'none' }
    return { kind: 'ok', draft: draftFromObject(JSON.parse(text), pkg, reviewer) }
  } catch (error) {
    return { kind: 'corrupt', message: error instanceof Error ? error.message : 'Rascunho local ilegível.' }
  }
}

export function persistDraft(draft: ReviewDraft): boolean {
  try {
    globalThis.localStorage.setItem(storageKey(draft.package_sha256, draft.reviewer), JSON.stringify(draft))
    return true
  } catch {
    return false
  }
}

export function discardStoredDraft(pkg: AnnotationPackage, reviewer: string): void {
  try {
    globalThis.localStorage.removeItem(storageKey(pkg.package_sha256, reviewer))
  } catch {
    /* Armazenamento indisponível: nada a descartar. */
  }
}

/* ---------- Validação de estruturas importadas ---------- */

function parseTimestamp(value: unknown, path: string): string {
  const text = expectString(value, path, 40)
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

function parseCaseAnnotation(value: unknown, path: string, pkgCase: PackageCase): CaseAnnotation {
  const raw = expectExactKeys(value, ['case_id', 'document_sha256', 'xml_sha256', 'phase1', 'phase2', 'phase1_reopen_count'], path)
  if (raw.case_id !== pkgCase.case_id) fail(`${path}: case_id fora da ordem do pacote`)
  const documentSha = raw.document_sha256 === null ? null : expectSha256(raw.document_sha256, `${path}.document_sha256`)
  if (documentSha !== (pkgCase.document?.sha256 ?? null)) fail(`${pkgCase.case_id}: hash do documento não confere com o pacote carregado`)
  if (expectSha256(raw.xml_sha256, `${path}.xml_sha256`) !== pkgCase.xml.sha256) fail(`${pkgCase.case_id}: hash do XML não confere com o pacote carregado`)
  const reopen = raw.phase1_reopen_count
  if (typeof reopen !== 'number' || !Number.isInteger(reopen) || reopen < 0 || reopen > 1000) fail(`${path}.phase1_reopen_count inválido`)
  const phase1 = parsePhase1(raw.phase1, `${path}.phase1`)
  const phase2 = raw.phase2 === null ? null : parsePhase2(raw.phase2, `${path}.phase2`)
  if (phase2 && phase1.status !== 'saved') fail(`${pkgCase.case_id}: fase 2 existe sem fase 1 salva`)
  const annotation: CaseAnnotation = { case_id: pkgCase.case_id, document_sha256: documentSha, xml_sha256: pkgCase.xml.sha256, phase1, phase2, phase1_reopen_count: reopen }
  const problems = annotationProblems(annotation, false)
  if (problems.length) fail(`${pkgCase.case_id}: fase salva inválida — ${problems[0]}`)
  return annotation
}

function draftFromObject(value: unknown, pkg: AnnotationPackage, reviewer: string): ReviewDraft {
  scanForbiddenKeys(value, '$', true)
  const raw = expectExactKeys(value, ['package_version', 'guide_version', 'package_sha256', 'reviewer', 'created_at', 'updated_at', 'cases'], 'rascunho')
  if (raw.package_version !== pkg.package_version) fail('package_version do rascunho difere do pacote carregado.')
  if (raw.guide_version !== pkg.guide_version) fail('guide_version do rascunho difere do pacote carregado.')
  if (raw.package_sha256 !== pkg.package_sha256) fail('Rascunho pertence a outro pacote (hash diferente).')
  const owner = expectString(raw.reviewer, 'reviewer', 200)
  if (!sameReviewer(owner, reviewer)) fail('Rascunho pertence a outro revisor; não é carregado.')
  const casesRaw = expectExactKeys(raw.cases, pkg.cases.map(item => item.case_id), 'rascunho.cases')
  const cases: Record<string, CaseAnnotation> = {}
  for (const item of pkg.cases) cases[item.case_id] = parseCaseAnnotation(casesRaw[item.case_id], `cases.${item.case_id}`, item)
  return {
    package_version: pkg.package_version,
    guide_version: pkg.guide_version,
    package_sha256: pkg.package_sha256,
    reviewer: normalizeReviewer(owner),
    created_at: parseTimestamp(raw.created_at, 'created_at'),
    updated_at: parseTimestamp(raw.updated_at, 'updated_at'),
    cases,
  }
}

/* ---------- Exportação / importação de arquivos ---------- */

export async function buildExport(draft: ReviewDraft, pkg: AnnotationPackage, kind: 'draft' | 'final', now = new Date()): Promise<ReviewExport> {
  if (kind === 'final') {
    const pending = incompleteCases(draft, pkg)
    if (pending.length) fail(`Exportação final bloqueada: ${pending.length} caso(s) incompleto(s) (${pending.join(', ')}).`)
  }
  const body: Omit<ReviewExport, 'annotation_sha256'> = {
    export_version: EXPORT_VERSION,
    kind,
    package_version: pkg.package_version,
    guide_version: pkg.guide_version,
    package_sha256: pkg.package_sha256,
    reviewer: normalizeReviewer(draft.reviewer),
    exported_at: now.toISOString(),
    cases: pkg.cases.map(item => draft.cases[item.case_id]),
  }
  return { ...body, annotation_sha256: await canonicalSha256(body) }
}

export async function parseExport(text: string, pkg: AnnotationPackage, reviewer: string): Promise<ReviewDraft> {
  let raw: unknown
  try {
    raw = JSON.parse(text)
  } catch {
    return fail('Arquivo não é JSON válido.')
  }
  scanForbiddenKeys(raw, '$', true)
  const top = expectExactKeys(raw, ['export_version', 'kind', 'package_version', 'guide_version', 'package_sha256', 'reviewer', 'exported_at', 'cases', 'annotation_sha256'], 'exportação')
  if (top.export_version !== EXPORT_VERSION) fail(`export_version não suportada: ${String(top.export_version)}`)
  if (top.kind !== 'draft' && top.kind !== 'final') fail('kind deve ser "draft" ou "final".')
  const { annotation_sha256: claimed, ...body } = top
  if ((await canonicalSha256(body)) !== expectSha256(claimed, 'annotation_sha256')) fail('annotation_sha256 não confere: arquivo alterado ou corrompido.')
  if (!Array.isArray(top.cases)) fail('cases: esperado lista')
  const owner = expectString(top.reviewer, 'reviewer', 200)
  const exportedAt = parseTimestamp(top.exported_at, 'exported_at')
  const draft = draftFromObject(
    {
      package_version: top.package_version,
      guide_version: top.guide_version,
      package_sha256: top.package_sha256,
      reviewer: owner,
      created_at: exportedAt,
      updated_at: exportedAt,
      cases: Object.fromEntries(top.cases.map(item => [isPlainObject(item) ? String(item.case_id) : '', item])),
    },
    pkg,
    reviewer,
  )
  if (top.kind === 'final') {
    const pending = incompleteCases(draft, pkg)
    if (pending.length) fail('Arquivo marcado como final, mas há casos incompletos.')
  }
  if (top.cases.length !== pkg.cases.length) fail('Quantidade de casos difere do pacote carregado.')
  return draft
}

export function exportFilename(draft: ReviewDraft, kind: 'draft' | 'final'): string {
  const slug = normalizeReviewer(draft.reviewer).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'revisor'
  return `anotacao-${slug}-${draft.package_sha256.slice(0, 8)}-${kind}.json`
}
