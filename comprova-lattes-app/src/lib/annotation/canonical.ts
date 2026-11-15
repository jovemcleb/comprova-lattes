/** JSON canônico e SHA-256 compatíveis com `experiments.freeze.canonical` (Python). */

export function canonicalJson(value: unknown): string {
  return walk(value).replace(
    /[\u007f-\uffff]/g,
    char => `\\u${char.charCodeAt(0).toString(16).padStart(4, '0')}`,
  )
}

function walk(value: unknown): string {
  if (value === null) return 'null'
  if (typeof value === 'string') return JSON.stringify(value)
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  if (typeof value === 'number') {
    if (!Number.isInteger(value)) throw new TypeError('JSON canônico aceita apenas inteiros')
    return String(value)
  }
  if (Array.isArray(value)) return `[${value.map(walk).join(',')}]`
  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>).sort(([a], [b]) =>
      a < b ? -1 : a > b ? 1 : 0,
    )
    return `{${entries.map(([key, child]) => `${JSON.stringify(key)}:${walk(child)}`).join(',')}}`
  }
  throw new TypeError(`Valor não serializável: ${typeof value}`)
}

export async function sha256Hex(data: Uint8Array | string): Promise<string> {
  const subtle = globalThis.crypto?.subtle
  if (!subtle) {
    throw new Error('Web Crypto indisponível: abra a interface em localhost ou HTTPS para verificar hashes.')
  }
  const bytes = typeof data === 'string' ? new TextEncoder().encode(data) : new Uint8Array(data)
  const digest = await subtle.digest('SHA-256', bytes)
  return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('')
}

export async function canonicalSha256(value: unknown): Promise<string> {
  return sha256Hex(canonicalJson(value))
}

export function base64ToBytes(encoded: string): Uint8Array {
  if (encoded.length % 4 !== 0 || !/^[A-Za-z0-9+/]*={0,2}$/.test(encoded)) {
    throw new Error('base64 inválido')
  }
  const binary = atob(encoded)
  const bytes = new Uint8Array(binary.length)
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index)
  return bytes
}
