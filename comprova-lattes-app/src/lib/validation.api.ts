import type { CreateInput, Health, ReviewInput, ValidationDetail, ValidationListItem } from '../types/validation'
export const apiBase = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')
export class ApiError extends Error {
  status: number
  validationId?: string
  constructor(status: number, detail: unknown) {
    super(`HTTP ${status}: ${typeof detail === 'string' ? detail : JSON.stringify(detail)}`)
    this.status = status
    if (detail && typeof detail === 'object' && 'id' in detail && typeof detail.id === 'string') this.validationId = detail.id
  }
}
async function request<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, { method: body === undefined ? 'GET' : 'POST', signal, headers: body === undefined ? undefined : { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) })
  const data = await response.json().catch(() => null)
  if (!response.ok) throw new ApiError(response.status, data?.detail ?? response.statusText)
  return data as T
}
export const getHealth = (signal?: AbortSignal) => request<Health>('/health', undefined, signal)
export async function getValidations(signal?: AbortSignal): Promise<ValidationListItem[]> {
  const rows: ValidationListItem[] = []
  for (let offset = 0; ; offset += 100) {
    const page = await request<ValidationListItem[]>(`/validations?offset=${offset}&limit=100`, undefined, signal)
    rows.push(...page)
    if (page.length < 100) break
  }
  return rows.sort((a, b) => b.created_at.localeCompare(a.created_at) || b.id.localeCompare(a.id))
}
export const getValidation = (id: string, signal?: AbortSignal) => request<ValidationDetail>(`/validations/${encodeURIComponent(id)}`, undefined, signal)
export const createValidation = (input: CreateInput) => request<ValidationDetail>('/validations', input)
export const submitReview = (id: string, index: number, input: ReviewInput) => request<ValidationDetail>(`/validations/${encodeURIComponent(id)}/records/${index}/review`, input)
export async function fileBase64(file: File): Promise<string> {
  const bytes = new Uint8Array(await file.arrayBuffer())
  let binary = ''
  for (let start = 0; start < bytes.length; start += 8192) binary += String.fromCharCode(...bytes.subarray(start, start + 8192))
  return btoa(binary)
}
export function documentMime(file: File): string {
  const formats: Record<string, string> = { pdf: 'application/pdf', png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg', webp: 'image/webp' }
  const mime = file.type || formats[file.name.split('.').pop()?.toLowerCase() ?? '']
  if (!Object.values(formats).includes(mime)) throw new Error(`Formato não suportado: ${file.name}`)
  if (!file.size || file.size > 21_000_000) throw new Error(`Documento vazio ou maior que 21 MB: ${file.name}`)
  return mime
}
