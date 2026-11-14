import type { MatcherConfig } from '../types/validation'
export const configTemplate = JSON.stringify({ thresholds: { association: null, ambiguity_margin: null, holder_low: null, holder_high: null, title_low: null, title_high: null, institution_low: null, institution_high: null }, mode: 'PROPOSED', text_metric: 'LEVENSHTEIN_NORM', acronym_table: {}, acronym_table_version: 'unconfigured', calibration_metadata: {} }, null, 2)
export const exampleConfigJson = JSON.stringify({ ...JSON.parse(configTemplate), thresholds: { association: 0.3, ambiguity_margin: 0.01, holder_low: 0.4, holder_high: 0.95, title_low: 0.4, title_high: 0.95, institution_low: 0.4, institution_high: 0.95 }, calibration_metadata: { purpose: 'Exemplo operacional de sessão; sem calibração aprovada' } }, null, 2)
function object(value: unknown): value is Record<string, unknown> { return !!value && typeof value === 'object' && !Array.isArray(value) }
export function parseMatcherConfig(text: string): MatcherConfig {
  const config: unknown = JSON.parse(text)
  if (!object(config) || !object(config.thresholds)) throw new Error('Informe MatcherConfig com thresholds explícitos.')
  const keys = ['association', 'ambiguity_margin', 'holder_low', 'holder_high', 'title_low', 'title_high', 'institution_low', 'institution_high']
  if (Object.keys(config.thresholds).some(key => !keys.includes(key))) throw new Error('Threshold desconhecido.')
  for (const key of keys) {
    const value = config.thresholds[key]
    if (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > 1 || (key === 'association' && value === 0)) throw new Error(`${key}: informe número entre 0 e 1 (association deve ser positivo).`)
  }
  for (const key of ['holder', 'title', 'institution']) if (Number(config.thresholds[`${key}_low`]) > Number(config.thresholds[`${key}_high`])) throw new Error(`${key}: low deve ser menor ou igual a high.`)
  if (!['PROPOSED', 'BASELINE_EXACT', 'BASELINE_NORMALIZED'].includes(String(config.mode))) throw new Error('Modo inválido.')
  if (!['LEVENSHTEIN_NORM', 'JARO_WINKLER', 'TOKEN_HYBRID'].includes(String(config.text_metric))) throw new Error('Métrica inválida.')
  if (!object(config.acronym_table) || Object.values(config.acronym_table).some(value => typeof value !== 'string')) throw new Error('acronym_table deve mapear siglas para textos.')
  if (typeof config.acronym_table_version !== 'string' || !config.acronym_table_version.trim()) throw new Error('Informe acronym_table_version.')
  if (!object(config.calibration_metadata)) throw new Error('calibration_metadata deve ser um objeto.')
  if (Object.keys(config).some(key => !['thresholds', 'mode', 'text_metric', 'acronym_table', 'acronym_table_version', 'calibration_metadata'].includes(key))) throw new Error('Campo desconhecido em MatcherConfig.')
  return config as MatcherConfig
}
