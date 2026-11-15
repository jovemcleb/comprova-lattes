import { base64ToBytes, canonicalSha256, sha256Hex } from './canonical'

export const PACKAGE_VERSION = 'annotation-package-v1'
export const MAX_PACKAGE_BYTES = 120 * 1024 * 1024
const MAX_DOCUMENT_BYTES = 20 * 1024 * 1024
const MAX_XML_BYTES = 4 * 1024 * 1024
const MAX_CASES = 500

export const DOCUMENT_MIME_TYPES = ['application/pdf', 'image/png', 'image/jpeg'] as const
export type DocumentMime = (typeof DOCUMENT_MIME_TYPES)[number]

export const CATEGORIES = [
  'FORMACAO_ACADEMICA',
  'FORMACAO_COMPLEMENTAR',
  'PARTICIPACAO_EVENTO',
  'APRESENTACAO_TRABALHO',
  'ORGANIZACAO_EVENTO',
] as const

/** Chaves que nunca podem existir em pacote público; espelha `annotation_package.FORBIDDEN_KEYS`. */
export const FORBIDDEN_KEYS: ReadonlySet<string> = new Set([
  'gold', 'expected', 'operator', 'family_id', 'template_id', 'issuer_id', 'partition',
  'degradation', 'seed', 'curriculum', 'raw_metadata', 'confianca_extracao', 'categoria_sugerida',
  'extraction_status', 'similarity_score', 'association_score', 'match_status', 'thresholds',
  'field_evidences', 'reason_code', 'diagnostics',
])

export type RecordTextKey =
  | 'record_id' | 'subtype' | 'sequence' | 'holder_name' | 'institution' | 'institution_acronym'
  | 'title' | 'event_name' | 'city' | 'location' | 'workload_hours' | 'status' | 'validation_code'
  | 'nature_raw' | 'participation_type_raw' | 'participation_form_raw' | 'participation_role'

const RECORD_TEXT_KEYS: readonly RecordTextKey[] = [
  'record_id', 'subtype', 'sequence', 'holder_name', 'institution', 'institution_acronym', 'title',
  'event_name', 'city', 'location', 'workload_hours', 'status', 'validation_code', 'nature_raw',
  'participation_type_raw', 'participation_form_raw', 'participation_role',
]
const RECORD_YEAR_KEYS = ['start_year', 'end_year'] as const

export type PackageRecord = Record<RecordTextKey, string | null> &
  Record<(typeof RECORD_YEAR_KEYS)[number], number | null> & {
    category: (typeof CATEGORIES)[number]
  }

export interface PackageDocument {
  mime_type: DocumentMime
  sha256: string
  content_base64: string
}

export interface PackageXml {
  sha256: string
  content_base64: string
}

export interface PackageCase {
  case_id: string
  document: PackageDocument | null
  xml: PackageXml
  record: PackageRecord
}

export interface AnnotationPackage {
  package_version: typeof PACKAGE_VERSION
  guide_version: string
  package_sha256: string
  cases: PackageCase[]
}

export class AnnotationValidationError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'AnnotationValidationError'
  }
}

export function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export function fail(message: string): never {
  throw new AnnotationValidationError(message)
}

export function scanForbiddenKeys(value: unknown, path = '$', allowPhase2Reason = false): void {
  if (Array.isArray(value)) {
    value.forEach((child, index) => scanForbiddenKeys(child, `${path}[${index}]`, allowPhase2Reason))
  } else if (isPlainObject(value)) {
    for (const [key, child] of Object.entries(value)) {
      const allowedReason = allowPhase2Reason && key === 'reason_code' && path.endsWith('.phase2')
      if (FORBIDDEN_KEYS.has(key) && !allowedReason) fail(`Chave proibida em arquivo público: ${path}.${key}`)
      scanForbiddenKeys(child, `${path}.${key}`, allowPhase2Reason)
    }
  }
}

export function expectExactKeys(value: unknown, keys: readonly string[], path: string): Record<string, unknown> {
  if (!isPlainObject(value)) fail(`${path}: esperado objeto`)
  const extra = Object.keys(value).filter(key => !keys.includes(key))
  if (extra.length) fail(`${path}: chaves não permitidas: ${extra.join(', ')}`)
  const missing = keys.filter(key => !(key in value))
  if (missing.length) fail(`${path}: chaves ausentes: ${missing.join(', ')}`)
  return value
}

export function expectString(value: unknown, path: string, max = 200_000): string {
  if (typeof value !== 'string') fail(`${path}: esperado texto`)
  if (value.length > max) fail(`${path}: texto longo demais`)
  return value
}

export function expectNullableString(value: unknown, path: string, max = 2_000): string | null {
  return value === null ? null : expectString(value, path, max)
}

const SHA256 = /^[0-9a-f]{64}$/
export function expectSha256(value: unknown, path: string): string {
  const text = expectString(value, path, 64)
  if (!SHA256.test(text)) fail(`${path}: SHA-256 malformado`)
  return text
}

function looksLikeRawCorpus(value: Record<string, unknown>): boolean {
  if ('seed' in value && 'cases' in value) return true
  if (!Array.isArray(value.cases)) return false
  return value.cases.some(item => isPlainObject(item) && ('gold' in item || 'expected' in item || 'operator' in item))
}

function sniffMatches(mime: DocumentMime, bytes: Uint8Array): boolean {
  const starts = (signature: number[]) => signature.every((byte, index) => bytes[index] === byte)
  if (mime === 'application/pdf') return starts([0x25, 0x50, 0x44, 0x46, 0x2d])
  if (mime === 'image/png') return starts([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])
  return starts([0xff, 0xd8, 0xff])
}

async function verifiedBytes(encoded: string, sha256: string, maxBytes: number, label: string): Promise<Uint8Array> {
  let bytes: Uint8Array
  try {
    bytes = base64ToBytes(encoded)
  } catch {
    return fail(`${label}: base64 inválido`)
  }
  if (bytes.length > maxBytes) fail(`${label}: arquivo grande demais`)
  if ((await sha256Hex(bytes)) !== sha256) fail(`${label}: hash SHA-256 não confere com os bytes`)
  return bytes
}

function parseRecord(value: unknown, path: string): PackageRecord {
  const raw = expectExactKeys(value, ['category', ...RECORD_TEXT_KEYS, ...RECORD_YEAR_KEYS], path)
  const category = expectString(raw.category, `${path}.category`, 64)
  if (!(CATEGORIES as readonly string[]).includes(category)) fail(`${path}.category: categoria desconhecida`)
  const record: Record<string, unknown> = { category }
  for (const key of RECORD_TEXT_KEYS) record[key] = expectNullableString(raw[key], `${path}.${key}`)
  for (const key of RECORD_YEAR_KEYS) {
    const year = raw[key]
    if (year !== null && !(typeof year === 'number' && Number.isInteger(year))) fail(`${path}.${key}: esperado inteiro`)
    record[key] = year
  }
  return record as PackageRecord
}

async function parseCase(value: unknown, index: number): Promise<PackageCase> {
  const path = `cases[${index}]`
  const raw = expectExactKeys(value, ['case_id', 'document', 'xml', 'record'], path)
  const caseId = expectString(raw.case_id, `${path}.case_id`, 64)
  if (!/^case-\d{3,}$/.test(caseId)) fail(`${path}.case_id: identificador não neutro (esperado case-001, case-002…)`)

  const xmlRaw = expectExactKeys(raw.xml, ['sha256', 'content_base64'], `${path}.xml`)
  const xml: PackageXml = {
    sha256: expectSha256(xmlRaw.sha256, `${path}.xml.sha256`),
    content_base64: expectString(xmlRaw.content_base64, `${path}.xml.content_base64`, MAX_XML_BYTES * 2),
  }
  await verifiedBytes(xml.content_base64, xml.sha256, MAX_XML_BYTES, `${caseId} XML`)

  let document: PackageDocument | null = null
  if (raw.document !== null) {
    const docRaw = expectExactKeys(raw.document, ['mime_type', 'sha256', 'content_base64'], `${path}.document`)
    const mime = expectString(docRaw.mime_type, `${path}.document.mime_type`, 64)
    if (!(DOCUMENT_MIME_TYPES as readonly string[]).includes(mime)) fail(`${caseId}: MIME não permitido (${mime})`)
    document = {
      mime_type: mime as DocumentMime,
      sha256: expectSha256(docRaw.sha256, `${path}.document.sha256`),
      content_base64: expectString(docRaw.content_base64, `${path}.document.content_base64`, MAX_DOCUMENT_BYTES * 2),
    }
    const bytes = await verifiedBytes(document.content_base64, document.sha256, MAX_DOCUMENT_BYTES, `${caseId} documento`)
    if (!sniffMatches(document.mime_type, bytes)) fail(`${caseId}: bytes do documento não correspondem ao MIME declarado`)
  }
  return { case_id: caseId, document, xml, record: parseRecord(raw.record, `${path}.record`) }
}

/** Valida pacote sanitizado: rejeita Corpus bruto, chaves extras e hashes/MIME incoerentes. */
export async function parseAnnotationPackage(text: string): Promise<AnnotationPackage> {
  let raw: unknown
  try {
    raw = JSON.parse(text)
  } catch {
    return fail('Arquivo não é JSON válido.')
  }
  if (!isPlainObject(raw)) fail('Pacote deve ser um objeto JSON.')
  if (looksLikeRawCorpus(raw)) {
    fail('Este arquivo parece um Corpus bruto (contém gabarito/metadados internos). Importe somente o pacote sanitizado gerado por annotation_package.')
  }
  scanForbiddenKeys(raw)
  const top = expectExactKeys(raw, ['package_version', 'guide_version', 'package_sha256', 'cases'], 'pacote')
  if (top.package_version !== PACKAGE_VERSION) fail(`package_version não suportada: ${String(top.package_version)}`)
  const guideVersion = expectString(top.guide_version, 'guide_version', 120).trim()
  if (!guideVersion) fail('guide_version vazio')
  const packageSha = expectSha256(top.package_sha256, 'package_sha256')
  if (!Array.isArray(top.cases) || top.cases.length === 0) fail('Pacote sem casos.')
  if (top.cases.length > MAX_CASES) fail(`Pacote excede ${MAX_CASES} casos.`)

  const cases: PackageCase[] = []
  const seen = new Set<string>()
  for (const [index, item] of top.cases.entries()) {
    const parsed = await parseCase(item, index)
    if (seen.has(parsed.case_id)) fail(`case_id duplicado: ${parsed.case_id}`)
    seen.add(parsed.case_id)
    cases.push(parsed)
  }
  const { package_sha256: _ignored, ...body } = raw
  void _ignored
  if ((await canonicalSha256(body)) !== packageSha) fail('package_sha256 não confere com o conteúdo do pacote (arquivo alterado ou corrompido).')
  return { package_version: PACKAGE_VERSION, guide_version: guideVersion, package_sha256: packageSha, cases }
}

export function decodeXml(pkgCase: PackageCase): string {
  return new TextDecoder('utf-8').decode(base64ToBytes(pkgCase.xml.content_base64))
}
