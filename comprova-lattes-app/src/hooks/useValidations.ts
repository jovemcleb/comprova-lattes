import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createValidation, getHealth, getValidation, getValidations, submitReview } from '../lib/validation.api'
import type { ReviewInput } from '../types/validation'
export const useHealth = () => useQuery({ queryKey: ['health'], queryFn: ({ signal }) => getHealth(signal), refetchInterval: 30000, retry: 1 })
export const useValidationsList = (offset: number, limit = 20) => useQuery({ queryKey: ['validations'], queryFn: ({ signal }) => getValidations(signal), select: rows => rows.slice(offset, offset + limit), refetchInterval: 10000 })
export const useValidationDetail = (id: string) => useQuery({ queryKey: ['validation', id], queryFn: ({ signal }) => getValidation(id, signal), enabled: !!id, refetchInterval: query => ['PENDING', 'PROCESSING'].includes(query.state.data?.status ?? '') ? 2000 : false })
export function useCreateValidation() {
  const client = useQueryClient()
  return useMutation({ mutationFn: createValidation, retry: false, onSuccess: data => { client.setQueryData(['validation', data.id], data); void client.invalidateQueries({ queryKey: ['validations'] }) } })
}
export function useSubmitHumanReview(id: string, index: number) {
  const client = useQueryClient()
  return useMutation({ mutationFn: (input: ReviewInput) => submitReview(id, index, input), retry: false, onSuccess: data => { client.setQueryData(['validation', id], data) } })
}
