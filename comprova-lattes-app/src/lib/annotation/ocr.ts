import {
  DOCUMENT_MIME_TYPES,
  expectExactKeys,
  expectNullableString,
  expectSha256,
  expectString,
  fail,
  isPlainObject,
  scanForbiddenKeys,
  type DocumentMime,
  type PackageCase,
} from './package'
import { FIELD_DEFS, FIELD_KEYS, type CaseOcrAssistance, type FieldKey } from './draft'

export const DEFAULT_OCR_SERVICE_URL = 'http://127.0.0.1:8766'
const ALLOWED_LOOPBACK_HOSTNAMES = new Set(['127.0.0.1', 'localhost', '[::1]', '::1'])
const MAX_OCR_TEXT_LENGTH = 200_000
const MAX_FIELD_VALUE_LENGTH = 500
const YEAR_FIELDS = new Set<FieldKey>(['start_year', 'end_year', 'activity_year'])
const FOUR_DIGIT_YEAR = /^\d{4}$/
const DIGITS_ONLY = /^\d+$/
const VALID_DECIMAL_HOURS = /^\d+(?:\.\d+)?$/

const REQUIRED_RESPONSE_KEYS = [
  'service_version',
  'document_id',
  'mime_type',
  'sha256',
  'accessed_at',
  'provider',
  'tesseract_version',
  'params',
  'ocr_text',
  'regex_fields',
  'field_labels',
  'extracted_field_count',
  'unextracted_fields',
  'warnings',
] as const

const OPTIONAL_RESPONSE_KEYS = [
  'diagnostics_version',
  'assist_preset',
  'invalid_regex_fields',
  'field_warnings',
] as const

const RAW_LABEL_PATTERNS: Record<FieldKey, RegExp> = {
  holder_name: /^[ \t]*(?:holder_name|Titular)[ \t]*:[ \t]*([^\r\n]+?)[ \t\r]*$/im,
  activity_title: /^[ \t]*(?:activity_title|Atividade)[ \t]*:[ \t]*([^\r\n]+?)[ \t\r]*$/im,
  event_name: /^[ \t]*(?:event_name|Evento)[ \t]*:[ \t]*([^\r\n]+?)[ \t\r]*$/im,
  participation_role_raw: /^[ \t]*(?:participation_role_raw|Papel)[ \t]*:[ \t]*([^\r\n]+?)[ \t\r]*$/im,
  issuer_institution: /^[ \t]*(?:issuer_institution|Institui[çc][ãa]o[ \t]+emissora)[ \t]*:[ \t]*([^\r\n]+?)[ \t\r]*$/im,
  issuer_acronym: /^[ \t]*(?:issuer_acronym|Sigla[ \t]+da[ \t]+institui[çc][ãa]o)[ \t]*:[ \t]*([^\r\n]+?)[ \t\r]*$/im,
  issuer_name_acronym_evidence:
    /^[ \t]*(?:issuer_name_acronym_evidence|Identifica[çc][ãa]o[ \t]+da[ \t]+institui[çc][ãa]o)[ \t]*:[ \t]*([^\r\n]+?)[ \t\r]*$/im,
  start_year: /^[ \t]*(?:start_year|Ano[ \t]+de[ \t]+in[íi]cio)[ \t]*:[ \t]*([^\r\n]+?)[ \t\r]*$/im,
  end_year: /^[ \t]*(?:end_year|Ano[ \t]+de[ \t]+conclus[ãa]o)[ \t]*:[ \t]*([^\r\n]+?)[ \t\r]*$/im,
  activity_year: /^[ \t]*(?:activity_year|Ano[ \t]+da[ \t]+atividade)[ \t]*:[ \t]*([^\r\n]+?)[ \t\r]*$/im,
  workload_hours: /^[ \t]*(?:workload_hours|Carga[ \t]+hor[áa]ria)[ \t]*:[ \t]*([^\r\n]+?)[ \t\r]*$/im,
}

export interface OcrRequestPayload {
  document_id: string
  mime_type: DocumentMime
  sha256: string
  content_base64: string
}

export interface OcrParamsRecord {
  dpi: number
  lang: string
  timeout_ms: number
  max_pdf_pages: number
  max_image_pixels: number
  pdf_text_extraction: string
  regex_extractor: string
}

export interface OcrAssistPresetMetadata {
  preset_id: string
  baseline_compatible: boolean
  dpi: number
  pdf_resampling: string
  upscale_small_images: boolean
  psm: number | null
}

export interface VerifiedOcrResponse {
  service_version: string
  diagnostics_version?: string
  document_id: string
  mime_type: DocumentMime
  sha256: string
  accessed_at: string
  provider: string
  tesseract_version: string
  params: OcrParamsRecord
  assist_preset?: OcrAssistPresetMetadata
  ocr_text: string
  regex_fields: Record<FieldKey, string | null>
  invalid_regex_fields?: Partial<Record<FieldKey, string>>
  field_warnings?: Partial<Record<FieldKey, string>>
  extracted_field_count: number
  unextracted_fields: FieldKey[]
  warnings: string[]
}

export interface InspectedOcrSuggestions {
  validFields: Record<FieldKey, string | null>
  invalidFields: Partial<Record<FieldKey, string>>
  fieldWarnings: Partial<Record<FieldKey, string>>
  generalWarnings: string[]
  assistPreset: OcrAssistPresetMetadata | null
}

export class OcrServiceError extends Error {
  readonly code: string

  constructor(code: string, message: string) {
    super(message)
    this.name = 'OcrServiceError'
    this.code = code
  }
}

export function validateLoopbackOcrUrl(rawUrl = DEFAULT_OCR_SERVICE_URL): string {
  let parsed: URL
  try {
    parsed = new URL(rawUrl)
  } catch {
    throw new OcrServiceError('INVALID_OCR_URL', 'URL do serviço OCR local é inválida.')
  }
  if (parsed.protocol !== 'http:') {
    throw new OcrServiceError('FORBIDDEN_OCR_URL', 'Serviço OCR deve usar exclusivamente HTTP loopback local.')
  }
  if (!ALLOWED_LOOPBACK_HOSTNAMES.has(parsed.hostname.toLowerCase())) {
    throw new OcrServiceError(
      'FORBIDDEN_OCR_URL',
      `Host ${parsed.hostname} não permitido: o auxílio OCR só pode conectar a 127.0.0.1 ou localhost.`,
    )
  }
  if (parsed.username || parsed.password || parsed.search || parsed.hash) {
    throw new OcrServiceError('FORBIDDEN_OCR_URL', 'URL do serviço OCR não deve conter credenciais, query ou hash.')
  }
  const cleanPath = parsed.pathname.replace(/\/+$/, '')
  return `${parsed.origin}${cleanPath}`
}

/** Constrói o payload mínimo para o OCR: apenas document_id, mime_type, sha256 e content_base64. Nunca inclui XML ou record. */
export function buildOcrRequestPayload(pkgCase: PackageCase): OcrRequestPayload {
  if (!pkgCase.document) {
    throw new OcrServiceError('NO_DOCUMENT', `O caso ${pkgCase.case_id} não possui comprovante para leitura OCR.`)
  }
  return {
    document_id: pkgCase.case_id,
    mime_type: pkgCase.document.mime_type,
    sha256: pkgCase.document.sha256,
    content_base64: pkgCase.document.content_base64,
  }
}

function expectPositiveInt(value: unknown, path: string, min = 1, max = 100_000_000): number {
  if (typeof value !== 'number' || !Number.isInteger(value) || value < min || value > max) {
    fail(`${path}: esperado inteiro entre ${min} e ${max}`)
  }
  return value
}

export function parseOcrParams(value: unknown, path: string): OcrParamsRecord {
  const raw = expectExactKeys(
    value,
    ['dpi', 'lang', 'timeout_ms', 'max_pdf_pages', 'max_image_pixels', 'pdf_text_extraction', 'regex_extractor'],
    path,
  )
  return {
    dpi: expectPositiveInt(raw.dpi, `${path}.dpi`, 72, 600),
    lang: expectString(raw.lang, `${path}.lang`, 40).trim(),
    timeout_ms: expectPositiveInt(raw.timeout_ms, `${path}.timeout_ms`, 100, 300_000),
    max_pdf_pages: expectPositiveInt(raw.max_pdf_pages, `${path}.max_pdf_pages`, 1, 500),
    max_image_pixels: expectPositiveInt(raw.max_image_pixels, `${path}.max_image_pixels`, 1024, 200_000_000),
    pdf_text_extraction: expectString(raw.pdf_text_extraction, `${path}.pdf_text_extraction`, 80),
    regex_extractor: expectString(raw.regex_extractor, `${path}.regex_extractor`, 80),
  }
}

export function parseOcrRegexFields(value: unknown, path: string): Record<FieldKey, string | null> {
  const raw = expectExactKeys(value, FIELD_KEYS, path)
  const fields = {} as Record<FieldKey, string | null>
  for (const key of FIELD_KEYS) {
    fields[key] = expectNullableString(raw[key], `${path}.${key}`, MAX_FIELD_VALUE_LENGTH)
  }
  return fields
}

function expectRequiredAndOptionalKeys(
  value: unknown,
  requiredKeys: readonly string[],
  optionalKeys: readonly string[],
  path: string,
): Record<string, unknown> {
  if (!isPlainObject(value)) fail(`${path}: esperado objeto`)
  const allowed = new Set([...requiredKeys, ...optionalKeys])
  const extra = Object.keys(value).filter(key => !allowed.has(key))
  if (extra.length) fail(`${path}: chaves não permitidas: ${extra.join(', ')}`)
  const missing = requiredKeys.filter(key => !(key in value))
  if (missing.length) fail(`${path}: chaves ausentes: ${missing.join(', ')}`)
  return value
}

function parseAssistPreset(value: unknown, path: string): OcrAssistPresetMetadata {
  const raw = expectExactKeys(
    value,
    ['preset_id', 'baseline_compatible', 'dpi', 'pdf_resampling', 'upscale_small_images', 'psm'],
    path,
  )
  if (typeof raw.baseline_compatible !== 'boolean') {
    fail(`${path}.baseline_compatible: esperado booleano`)
  }
  if (typeof raw.upscale_small_images !== 'boolean') {
    fail(`${path}.upscale_small_images: esperado booleano`)
  }
  let psm: number | null = null
  if (raw.psm !== null) {
    psm = expectPositiveInt(raw.psm, `${path}.psm`, 0, 13)
  }
  return {
    preset_id: expectString(raw.preset_id, `${path}.preset_id`, 120),
    baseline_compatible: raw.baseline_compatible,
    dpi: expectPositiveInt(raw.dpi, `${path}.dpi`, 72, 600),
    pdf_resampling: expectString(raw.pdf_resampling, `${path}.pdf_resampling`, 64),
    upscale_small_images: raw.upscale_small_images,
    psm,
  }
}

function parsePartialFieldMap(
  value: unknown,
  path: string,
  maxLen: number,
): Partial<Record<FieldKey, string>> {
  if (!isPlainObject(value)) fail(`${path}: esperado objeto`)
  const out: Partial<Record<FieldKey, string>> = {}
  for (const [key, entry] of Object.entries(value)) {
    if (!FIELD_KEYS.includes(key as FieldKey)) {
      fail(`${path}: campo desconhecido: ${key}`)
    }
    out[key as FieldKey] = expectString(entry, `${path}.${key}`, maxLen)
  }
  return out
}

function fieldLabelFor(fieldKey: FieldKey): string {
  return FIELD_DEFS.find(def => def.key === fieldKey)?.label ?? fieldKey
}

function buildInvalidFieldWarning(fieldKey: FieldKey, rawValue: string): string {
  const label = fieldLabelFor(fieldKey)
  if (YEAR_FIELDS.has(fieldKey)) {
    if (DIGITS_ONLY.test(rawValue)) {
      return `${label} capturado ('${rawValue}') possui ${rawValue.length} dígitos (esperado ano com exatamente 4 dígitos). Possível erro de OCR; não foi corrigido nem preenchido automaticamente — confira a imagem.`
    }
    return `${label} capturado ('${rawValue}') não é um ano válido de 4 dígitos. Não foi corrigido nem preenchido automaticamente — confira a imagem.`
  }
  if (fieldKey === 'workload_hours') {
    return `${label} capturada ('${rawValue}') não é um número decimal válido (ex.: 40 ou 40.5). Não foi preenchida automaticamente — confira o comprovante.`
  }
  if (fieldKey === 'issuer_name_acronym_evidence') {
    return `${label} capturada ('${rawValue}') não comprova simultaneamente nome e sigla válidos nos campos extraídos. Valor bruto preservado para conferência visual; não aplicado automaticamente.`
  }
  return `${label} capturado ('${rawValue}') falhou na validação de formato. Valor bruto preservado apenas para conferência visual; não aplicado automaticamente.`
}

function validateFieldSyntax(fieldKey: FieldKey, value: string): string | null {
  const trimmed = value.trim()
  if (!trimmed) return 'Valor vazio capturado pela RegEx.'
  if (YEAR_FIELDS.has(fieldKey) && !FOUR_DIGIT_YEAR.test(trimmed)) {
    return buildInvalidFieldWarning(fieldKey, trimmed)
  }
  if (fieldKey === 'workload_hours' && !VALID_DECIMAL_HOURS.test(trimmed)) {
    return buildInvalidFieldWarning(fieldKey, trimmed)
  }
  return null
}

export function inspectCaseOcrAssistance(
  ocr: CaseOcrAssistance,
  latestResponse?: VerifiedOcrResponse | null,
): InspectedOcrSuggestions {
  const matchedResponse =
    latestResponse &&
    latestResponse.document_id === ocr.document_id &&
    latestResponse.sha256 === ocr.document_sha256
      ? latestResponse
      : null

  const validFields = {} as Record<FieldKey, string | null>
  const invalidFields: Partial<Record<FieldKey, string>> = {
    ...(matchedResponse?.invalid_regex_fields ?? {}),
  }
  const fieldWarnings: Partial<Record<FieldKey, string>> = {
    ...(matchedResponse?.field_warnings ?? {}),
  }

  for (const key of FIELD_KEYS) {
    const rawVal = ocr.regex_fields?.[key] ?? null
    if (rawVal === null) {
      validFields[key] = null
      continue
    }
    const problem = validateFieldSyntax(key, rawVal)
    if (problem !== null) {
      validFields[key] = null
      if (!invalidFields[key]) invalidFields[key] = rawVal.trim()
      if (!fieldWarnings[key]) fieldWarnings[key] = problem
    } else {
      validFields[key] = rawVal
    }
  }

  if (ocr.ocr_raw_text) {
    for (const key of FIELD_KEYS) {
      if (validFields[key] !== null || invalidFields[key] !== undefined) continue
      const match = ocr.ocr_raw_text.match(RAW_LABEL_PATTERNS[key])
      const captured = match?.[1]?.trim()
      if (!captured) continue
      const problem = validateFieldSyntax(key, captured)
      if (problem !== null || key === 'issuer_name_acronym_evidence') {
        invalidFields[key] = captured.slice(0, MAX_FIELD_VALUE_LENGTH)
        if (!fieldWarnings[key]) {
          fieldWarnings[key] = problem ?? buildInvalidFieldWarning(key, invalidFields[key]!)
        }
      }
    }
  }

  const warningSet = new Set<string>(matchedResponse?.warnings ?? [])
  for (const key of FIELD_KEYS) {
    const msg = fieldWarnings[key]
    if (msg) {
      const summary = `Sugestão inválida bloqueada em '${fieldLabelFor(key)}': ${msg}`
      if (![...warningSet].some(existing => existing.includes(msg) || existing === summary)) {
        warningSet.add(summary)
      }
    }
  }

  return {
    validFields,
    invalidFields,
    fieldWarnings,
    generalWarnings: [...warningSet],
    assistPreset: matchedResponse?.assist_preset ?? null,
  }
}

export function validateOcrResponse(
  raw: unknown,
  expected: { document_id: string; mime_type: DocumentMime; sha256: string },
): VerifiedOcrResponse {
  if (!isPlainObject(raw)) {
    throw new OcrServiceError('INVALID_OCR_RESPONSE', 'Resposta do serviço OCR não é um objeto JSON.')
  }
  scanForbiddenKeys(raw)
  const top = expectRequiredAndOptionalKeys(
    raw,
    REQUIRED_RESPONSE_KEYS,
    OPTIONAL_RESPONSE_KEYS,
    'ocr_response',
  )
  const serviceVersion = expectString(top.service_version, 'ocr_response.service_version', 80)
  const docId = expectString(top.document_id, 'ocr_response.document_id', 120)
  const mime = expectString(top.mime_type, 'ocr_response.mime_type', 64)
  if (!(DOCUMENT_MIME_TYPES as readonly string[]).includes(mime)) {
    throw new OcrServiceError('INVALID_OCR_RESPONSE', `MIME inválido na resposta OCR: ${mime}`)
  }
  const sha = expectSha256(top.sha256, 'ocr_response.sha256')

  if (docId !== expected.document_id) {
    throw new OcrServiceError(
      'RESPONSE_MISMATCH',
      `Resposta OCR descartada por troca de identificador: esperado ${expected.document_id}, recebido ${docId}.`,
    )
  }
  if (sha !== expected.sha256) {
    throw new OcrServiceError(
      'RESPONSE_MISMATCH',
      `Resposta OCR descartada: hash SHA-256 retornado (${sha.slice(0, 12)}…) não confere com o comprovante (${expected.sha256.slice(0, 12)}…).`,
    )
  }
  if (mime !== expected.mime_type) {
    throw new OcrServiceError(
      'RESPONSE_MISMATCH',
      `Resposta OCR descartada: MIME retornado (${mime}) difere do comprovante (${expected.mime_type}).`,
    )
  }

  const accessedAt = expectString(top.accessed_at, 'ocr_response.accessed_at', 64)
  if (Number.isNaN(Date.parse(accessedAt))) {
    throw new OcrServiceError('INVALID_OCR_RESPONSE', 'ocr_response.accessed_at inválido.')
  }
  const provider = expectString(top.provider, 'ocr_response.provider', 80)
  const tesseractVersion = expectString(top.tesseract_version, 'ocr_response.tesseract_version', 200)
  const params = parseOcrParams(top.params, 'ocr_response.params')
  const ocrText = expectString(top.ocr_text, 'ocr_response.ocr_text', MAX_OCR_TEXT_LENGTH)
  const regexFields = parseOcrRegexFields(top.regex_fields, 'ocr_response.regex_fields')

  const extractedCount = expectPositiveInt(top.extracted_field_count, 'ocr_response.extracted_field_count', 0, FIELD_KEYS.length)
  if (!Array.isArray(top.unextracted_fields) || top.unextracted_fields.some(k => !FIELD_KEYS.includes(k as FieldKey))) {
    throw new OcrServiceError('INVALID_OCR_RESPONSE', 'ocr_response.unextracted_fields inválido.')
  }
  if (!Array.isArray(top.warnings)) {
    throw new OcrServiceError('INVALID_OCR_RESPONSE', 'ocr_response.warnings inválido.')
  }
  const warnings = top.warnings.map((w, idx) => expectString(w, `ocr_response.warnings[${idx}]`, 1000))
  const diagnosticsVersion =
    'diagnostics_version' in top
      ? expectString(top.diagnostics_version, 'ocr_response.diagnostics_version', 80)
      : undefined
  const assistPreset =
    'assist_preset' in top ? parseAssistPreset(top.assist_preset, 'ocr_response.assist_preset') : undefined
  const invalidRegexFields =
    'invalid_regex_fields' in top
      ? parsePartialFieldMap(top.invalid_regex_fields, 'ocr_response.invalid_regex_fields', MAX_FIELD_VALUE_LENGTH)
      : {}
  const fieldWarnings =
    'field_warnings' in top
      ? parsePartialFieldMap(top.field_warnings, 'ocr_response.field_warnings', 1000)
      : {}

  const sanitizedRegexFields = { ...regexFields }
  const unextractedSet = new Set<FieldKey>(top.unextracted_fields as FieldKey[])

  for (const key of FIELD_KEYS) {
    const val = sanitizedRegexFields[key]
    if (val === null) continue
    const problem = validateFieldSyntax(key, val)
    if (problem !== null) {
      const trimmed = val.trim()
      sanitizedRegexFields[key] = null
      if (!invalidRegexFields[key]) invalidRegexFields[key] = trimmed
      if (!fieldWarnings[key]) fieldWarnings[key] = problem
      unextractedSet.delete(key)
      const alertLine = `Sugestão inválida bloqueada em '${fieldLabelFor(key)}': ${fieldWarnings[key]}`
      if (!warnings.includes(alertLine)) warnings.push(alertLine)
    }
  }

  for (const key of Object.keys(invalidRegexFields) as FieldKey[]) {
    unextractedSet.delete(key)
  }

  const sanitizedCount = FIELD_KEYS.filter(key => sanitizedRegexFields[key] !== null).length
  const finalCount =
    Object.keys(invalidRegexFields).length > 0 || sanitizedCount !== extractedCount
      ? sanitizedCount
      : extractedCount

  return {
    service_version: serviceVersion,
    ...(diagnosticsVersion !== undefined ? { diagnostics_version: diagnosticsVersion } : {}),
    document_id: docId,
    mime_type: mime as DocumentMime,
    sha256: sha,
    accessed_at: accessedAt,
    provider,
    tesseract_version: tesseractVersion,
    params,
    ...(assistPreset !== undefined ? { assist_preset: assistPreset } : {}),
    ocr_text: ocrText,
    regex_fields: sanitizedRegexFields,
    ...(Object.keys(invalidRegexFields).length > 0 ? { invalid_regex_fields: invalidRegexFields } : {}),
    ...(Object.keys(fieldWarnings).length > 0 ? { field_warnings: fieldWarnings } : {}),
    extracted_field_count: finalCount,
    unextracted_fields: FIELD_KEYS.filter(key => unextractedSet.has(key)),
    warnings,
  }
}

function mapHttpError(status: number, body: unknown): OcrServiceError {
  const code = isPlainObject(body) && typeof body.error_code === 'string' ? body.error_code : `HTTP_${status}`
  const detail = isPlainObject(body) && typeof body.detail === 'string' ? body.detail : `Erro HTTP ${status} no serviço OCR.`

  switch (code) {
    case 'TESSERACT_NOT_FOUND':
      return new OcrServiceError(
        code,
        `Tesseract não encontrado na máquina local (${detail}). A transcrição manual continua disponível normalmente.`,
      )
    case 'TESSERACT_LANGUAGE_MISSING':
      return new OcrServiceError(
        code,
        `Idioma português ('por.traineddata') ausente no Tesseract (${detail}). A transcrição manual continua disponível.`,
      )
    case 'TESSERACT_TIMEOUT':
      return new OcrServiceError(
        code,
        `Tempo limite excedido ao executar o Tesseract (${detail}). Você pode tentar novamente ou transcrever manualmente.`,
      )
    case 'SHA256_MISMATCH':
      return new OcrServiceError(code, `Falha de integridade SHA-256 no serviço OCR: ${detail}`)
    case 'PAYLOAD_TOO_LARGE':
      return new OcrServiceError(code, `Comprovante rejeitado por limite de tamanho no serviço OCR: ${detail}`)
    case 'OCR_CONCURRENCY_LIMIT':
      return new OcrServiceError(code, detail)
    case 'OCR_RENDER_ERROR':
      return new OcrServiceError(code, detail)
    default:
      return new OcrServiceError(code, detail)
  }
}

export async function requestCaseOcr(
  pkgCase: PackageCase,
  options?: {
    baseUrl?: string
    fetchImpl?: typeof fetch
    signal?: AbortSignal
  },
): Promise<VerifiedOcrResponse> {
  const baseUrl = validateLoopbackOcrUrl(options?.baseUrl ?? DEFAULT_OCR_SERVICE_URL)
  const payload = buildOcrRequestPayload(pkgCase)
  const fetchFn = options?.fetchImpl ?? globalThis.fetch
  if (typeof fetchFn !== 'function') {
    throw new OcrServiceError('SERVICE_UNREACHABLE', 'Fetch indisponível neste ambiente.')
  }

  let response: Response
  try {
    response = await fetchFn(`${baseUrl}/ocr`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: options?.signal,
    })
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new OcrServiceError('ABORTED', 'Leitura OCR cancelada pelo revisor.')
    }
    throw new OcrServiceError(
      'SERVICE_UNREACHABLE',
      `Serviço OCR local desligado ou inacessível em ${baseUrl}. A revisão manual permanece liberada; se desejar usar o OCR, inicie o servidor local com: python -m comprova_lattes.experiments.review_ocr`,
    )
  }

  let rawJson: unknown
  try {
    rawJson = await response.json()
  } catch {
    if (!response.ok) {
      throw new OcrServiceError(`HTTP_${response.status}`, `Serviço OCR respondeu com erro HTTP ${response.status}.`)
    }
    throw new OcrServiceError('INVALID_OCR_RESPONSE', 'Serviço OCR retornou resposta que não é JSON válido.')
  }

  if (!response.ok) {
    throw mapHttpError(response.status, rawJson)
  }

  try {
    return validateOcrResponse(rawJson, {
      document_id: payload.document_id,
      mime_type: payload.mime_type,
      sha256: payload.sha256,
    })
  } catch (error) {
    if (error instanceof OcrServiceError) throw error
    throw new OcrServiceError(
      'INVALID_OCR_RESPONSE',
      error instanceof Error ? error.message : 'Resposta OCR inválida.',
    )
  }
}
