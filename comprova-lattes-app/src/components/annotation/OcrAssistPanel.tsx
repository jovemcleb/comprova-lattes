import { useEffect, useRef, useState } from 'react'
import type { PackageCase } from '../../lib/annotation/package'
import {
  FIELD_DEFS,
  type CaseAnnotation,
  type FieldKey,
  type ReviewMode,
} from '../../lib/annotation/draft'
import {
  DEFAULT_OCR_SERVICE_URL,
  inspectCaseOcrAssistance,
  OcrServiceError,
  requestCaseOcr,
  type VerifiedOcrResponse,
} from '../../lib/annotation/ocr'

interface OcrAssistPanelProps {
  pkgCase: PackageCase
  annotation: CaseAnnotation
  reviewMode: ReviewMode
  onOptInAndRead: (caseId: string) => void
  onOcrSuccess: (caseId: string, response: VerifiedOcrResponse) => void
  onOcrFailure: (caseId: string, errorMessage: string) => void
  onCopyRawText: () => void
  onCopyField: (fieldKey: FieldKey, applyToField: boolean) => void
}

async function writeClipboardSafe(text: string): Promise<boolean> {
  try {
    if (globalThis.navigator?.clipboard?.writeText) {
      await globalThis.navigator.clipboard.writeText(text)
      return true
    }
  } catch {
    /* Clipboard API pode falhar em contextos restritos; o registro observável do botão continua funcionando. */
  }
  return false
}

export function OcrAssistPanel({
  pkgCase,
  annotation,
  reviewMode,
  onOptInAndRead,
  onOcrSuccess,
  onOcrFailure,
  onCopyRawText,
  onCopyField,
}: OcrAssistPanelProps) {
  const [confirmOptIn, setConfirmOptIn] = useState(false)
  const [loading, setLoading] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null)
  const [lastResponse, setLastResponse] = useState<VerifiedOcrResponse | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    return () => {
      abortRef.current?.abort()
    }
  }, [pkgCase.case_id])

  const ocr = annotation.ocr_assistance
  const matchedResponse =
    lastResponse &&
    lastResponse.document_id === pkgCase.case_id &&
    lastResponse.sha256 === ocr.document_sha256
      ? lastResponse
      : null
  const inspected =
    ocr.status === 'displayed' && ocr.regex_fields !== null
      ? inspectCaseOcrAssistance(ocr, matchedResponse)
      : null
  const invalidEntries = inspected ? Object.entries(inspected.fieldWarnings) : []

  async function runOcrRequest() {
    if (!pkgCase.document || loading) return
    setConfirmOptIn(false)
    setLocalError(null)
    setCopyFeedback(null)
    setLoading(true)

    const controller = new AbortController()
    abortRef.current = controller
    const targetCaseId = pkgCase.case_id

    try {
      const verified = await requestCaseOcr(pkgCase, {
        baseUrl: DEFAULT_OCR_SERVICE_URL,
        signal: controller.signal,
      })
      setLastResponse(verified)
      onOcrSuccess(targetCaseId, verified)
    } catch (err) {
      if (err instanceof OcrServiceError && err.code === 'ABORTED') {
        setLocalError('Leitura OCR cancelada. A transcrição manual permanece disponível.')
      } else {
        const message =
          err instanceof Error
            ? err.message
            : 'Falha ao consultar o serviço OCR local. Continue a transcrição manualmente.'
        setLocalError(message)
        onOcrFailure(targetCaseId, message)
      }
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null
      }
      setLoading(false)
    }
  }

  function handlePrimaryButton() {
    if (reviewMode === 'unassisted') {
      setConfirmOptIn(true)
      return
    }
    void runOcrRequest()
  }

  function confirmOptInAndExecute() {
    onOptInAndRead(pkgCase.case_id)
    void runOcrRequest()
  }

  async function handleCopyRawText() {
    if (ocr.ocr_raw_text === null) return
    const copiedToClipboard = await writeClipboardSafe(ocr.ocr_raw_text)
    onCopyRawText()
    setCopyFeedback(
      copiedToClipboard
        ? 'Texto bruto copiado para a área de transferência e registrado no rascunho.'
        : 'Acionamento de cópia do texto bruto registrado no rascunho (selecione o texto caso a área de transferência esteja restrita).',
    )
  }

  async function handleCopyField(fieldKey: FieldKey, applyToField: boolean) {
    const val = inspected?.validFields[fieldKey] ?? null
    if (!val) return
    if (!applyToField) {
      await writeClipboardSafe(val)
    }
    onCopyField(fieldKey, applyToField)
    setCopyFeedback(
      applyToField
        ? `Valor OCR inserido em "${FIELD_DEFS.find(d => d.key === fieldKey)?.label ?? fieldKey}". Confira visualmente no comprovante; você pode editar ou rejeitar.`
        : `Valor de "${FIELD_DEFS.find(d => d.key === fieldKey)?.label ?? fieldKey}" copiado e registrado no rascunho.`,
    )
  }

  const displayError = localError ?? ocr.last_error

  return (
    <section className="annot-ocr-panel" aria-labelledby={`ocr-panel-title-${pkgCase.case_id}`}>
      <div className="annot-ocr-header">
        <div>
          <h4 id={`ocr-panel-title-${pkgCase.case_id}`}>
            Auxílio opcional de leitura · OCR local (Tesseract + RegEx)
          </h4>
          <p className="annot-note">
            <strong>Atenção metodológica (potencial viés de baseline):</strong> este botão consulta somente o serviço local
            offline (<span className="code">{DEFAULT_OCR_SERVICE_URL}/ocr</span>) com os bytes deste comprovante (sem XML e sem
            gabarito), executando a mesma pilha <span className="code">TesseractOCR</span> + <span className="code">OCRRegex</span> do
            baseline clássico. <strong>Nunca trate o OCR como gabarito.</strong> Solicitar ou exibir o OCR antes de concluir o caso
            altera a condição para <strong>revisão humana assistida</strong> (não anotação independente sem auxílio). Se o serviço
            estiver desligado, continue a revisão manual normalmente.
          </p>
        </div>
        <div className="annot-actions">
          {!loading ? (
            <button type="button" className="secondary" onClick={handlePrimaryButton}>
              {ocr.status === 'displayed' ? 'Reler com OCR (Tesseract local)' : 'Ler com OCR (opt-in)'}
            </button>
          ) : (
            <button
              type="button"
              className="secondary"
              onClick={() => {
                abortRef.current?.abort()
              }}
            >
              Cancelar leitura OCR
            </button>
          )}
        </div>
      </div>

      {confirmOptIn && reviewMode === 'unassisted' && (
        <div className="attention" role="region" aria-label="Confirmação de ativação do modo assistido por OCR">
          <p>
            <strong>Confirmar ativação de revisão assistida por OCR?</strong> A sessão atual está em modo manual não assistido
            (<span className="code">unassisted</span>). Ao confirmar:
          </p>
          <ul>
            <li>
              O estado manual atual permanece salvo separadamente no navegador como rascunho não assistido (sem misturar rascunhos).
            </li>
            <li>
              A sessão ativa passa para <span className="code">ocr_assisted</span> (<span className="code">ocr_assisted_human_review</span>) e
              registra no JSON exportado o provedor, versão, DPI, hash do documento, data de acesso e ações observáveis de cópia.
            </li>
            <li>
              Nenhum campo será preenchido automaticamente: você deverá conferir visualmente o comprovante antes de usar qualquer trecho.
            </li>
          </ul>
          <div className="annot-actions">
            <button type="button" onClick={confirmOptInAndExecute}>
              Confirmar modo assistido e ler com OCR
            </button>
            <button type="button" className="secondary" onClick={() => setConfirmOptIn(false)}>
              Continuar somente manual (sem OCR)
            </button>
          </div>
        </div>
      )}

      {loading && (
        <p role="status" className="annot-note">
          Executando Tesseract OCR local sobre o comprovante… Você pode continuar preenchendo os campos manualmente sem bloqueio.
        </p>
      )}

      {displayError && (
        <div className="annot-errors" role="alert">
          <strong>Auxílio OCR indisponível ou com falha:</strong> {displayError}
          <p className="annot-note">
            A transcrição manual na Fase 1 permanece totalmente liberada e não depende do servidor OCR.
          </p>
        </div>
      )}

      {copyFeedback && (
        <p role="status" className="annot-ocr-feedback">
          {copyFeedback}
        </p>
      )}

      {ocr.status === 'displayed' && ocr.ocr_raw_text !== null && ocr.regex_fields !== null && (
        <div className="annot-ocr-results">
          <dl className="annot-record annot-ocr-meta">
            <dt>Condição registrada</dt>
            <dd>
              <span className="badge">Revisão assistida por OCR</span>
              {ocr.assisted_before_completion ? ' (acionado antes da conclusão do caso)' : ' (acionado após conclusão)'}
            </dd>
            <dt>Provedor / versão</dt>
            <dd className="code">
              {ocr.provider} · {ocr.tesseract_version}
            </dd>
            <dt>Parâmetros OCR</dt>
            <dd className="code">
              DPI {ocr.params?.dpi} · idioma {ocr.params?.lang} · timeout {ocr.params?.timeout_ms} ms · máx. {ocr.params?.max_pdf_pages}{' '}
              páginas PDF ({ocr.params?.pdf_text_extraction})
              {inspected?.assistPreset &&
                ` · preset ${inspected.assistPreset.preset_id} (${inspected.assistPreset.pdf_resampling}, PSM ${inspected.assistPreset.psm ?? 'padrão'})`}
            </dd>
            <dt>Documento verificado</dt>
            <dd className="code">
              {ocr.document_id} · {ocr.document_mime_type} · SHA-256 {ocr.document_sha256?.slice(0, 16)}… · acesso em {ocr.last_accessed_at}
            </dd>
          </dl>

          {invalidEntries.length > 0 && (
            <div className="attention" role="alert">
              <strong>Alertas de validação OCR ({invalidEntries.length} campo(s) bloqueado(s)):</strong>
              <p className="annot-note">
                Capturas inválidas da RegEx ficam visíveis abaixo apenas para conferência, nunca são auto-corrigidas nem preenchidas nos campos.
              </p>
              <ul>
                {invalidEntries.map(([fieldKey, message]) => (
                  <li key={fieldKey}>{message}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="annot-ocr-section">
            <div className="annot-ocr-section-head">
              <h5>1. Texto bruto reconhecido pelo Tesseract (TesseractOCR)</h5>
              <button type="button" className="secondary" onClick={() => void handleCopyRawText()}>
                Copiar texto bruto
              </button>
            </div>
            <p className="annot-note">
              Saída textual direta do reconhecimento óptico de caracteres, separada dos recortes de expressão regular abaixo.
            </p>
            <pre className="annot-ocr-pre" tabIndex={0}>
              {ocr.ocr_raw_text.trim() ? ocr.ocr_raw_text : '(Nenhum caractere legível retornado pelo Tesseract)'}
            </pre>
          </div>

          <div className="annot-ocr-section">
            <h5>2. Valores recortados por expressão regular (OCRRegex — separados do texto bruto)</h5>
            <p className="annot-note">
              Valores capturados por <span className="code">OCRRegex</span> a partir do texto bruto acima.{' '}
              <strong>Ausência de extração aqui significa apenas que a RegEx não encontrou o padrão</strong> — nunca significa que o
              campo esteja ausente ou ilegível no comprovante e jamais marca o campo como <em>Ausente</em>. Todo valor copiado exige
              conferência visual no comprovante ao lado.
            </p>
            <div className="annot-ocr-fields">
              {FIELD_DEFS.map(def => {
                const extracted = inspected?.validFields[def.key] ?? null
                const invalidRaw = inspected?.invalidFields[def.key] ?? null
                const fieldWarning = inspected?.fieldWarnings[def.key] ?? null
                const wasCopied = ocr.observable_copied_fields.includes(def.key)
                return (
                  <div className="annot-ocr-field-row" key={def.key}>
                    <div className="annot-ocr-field-info">
                      <strong>{def.label}</strong>
                      {extracted !== null ? (
                        <span className="code annot-ocr-val">{extracted}</span>
                      ) : invalidRaw !== null ? (
                        <>
                          <span className="code annot-ocr-val">{invalidRaw}</span>
                          <span className="badge">Captura RegEx inválida (bloqueada)</span>
                          {fieldWarning && <span className="annot-note">{fieldWarning}</span>}
                        </>
                      ) : (
                        <span className="annot-ocr-unextracted">
                          Não extraído pela RegEx (confira no comprovante; não implica ausência no documento)
                        </span>
                      )}
                      {wasCopied && <span className="badge">Cópia/uso via painel registrado</span>}
                    </div>
                    {extracted !== null && (
                      <div className="annot-actions">
                        <button
                          type="button"
                          className="secondary"
                          onClick={() => void handleCopyField(def.key, true)}
                        >
                          Usar no campo (conferir visualmente)
                        </button>
                        <button
                          type="button"
                          className="secondary"
                          onClick={() => void handleCopyField(def.key, false)}
                        >
                          Copiar valor
                        </button>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          <p className="annot-note">
            <strong>Limite de observabilidade:</strong> {ocr.observability_limit_note}
          </p>
        </div>
      )}
    </section>
  )
}
