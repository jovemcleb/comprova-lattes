import { useState } from 'react'
import { useCreateValidation } from './useValidations'
import { documentMime, fileBase64 } from '../lib/validation.api'
import { parseMatcherConfig } from '../lib/matcher.schema'
export function useValidationUpload() {
  const mutation = useCreateValidation()
  const [preparing, setPreparing] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  async function upload(mode: string, xmlFile: File | null, xmlText: string, files: File[], config: string) {
    setError(null)
    setPreparing(true)
    try {
      const matcher_config = parseMatcherConfig(config)
      if (files.length > 100) throw new Error('Limite de 100 comprovantes por lote.')
      if (mode === 'file' && (!xmlFile || !xmlFile.size || xmlFile.size > 10_485_760)) throw new Error('Selecione um XML não vazio com até 10 MiB.')
      if (mode === 'text' && (!xmlText.trim() || new TextEncoder().encode(xmlText).length > 10_485_760)) throw new Error('Informe XML não vazio com até 10 MiB.')
      if (mode === 'text' && /encoding\s*=\s*['"](?!utf-?8['"])/i.test(xmlText)) throw new Error('Texto é enviado em UTF-8. Use arquivo para preservar outra codificação ou ajuste a declaração para UTF-8.')
      const documents = await Promise.all(files.map(async (file, index) => ({ document_id: `doc-${index + 1}`, filename: file.name, mime_type: documentMime(file), content_base64: await fileBase64(file) })))
      const xml = mode === 'file' && xmlFile ? { xml_base64: await fileBase64(xmlFile) } : { xml_content: xmlText }
      return await mutation.mutateAsync({ ...xml, documents, matcher_config })
    } catch (cause) { setError(cause instanceof Error ? cause : new Error('Falha ao preparar envio.')); return null }
    finally { setPreparing(false) }
  }
  return { upload, error, pending: preparing || mutation.isPending }
}
