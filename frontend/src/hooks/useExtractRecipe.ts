import { useMutation } from '@tanstack/react-query'
import { api } from '@/api'
import type { ExtractResponse } from '@/types'

export function useExtractRecipe() {
  return useMutation({
    mutationFn: (url: string) =>
      api.post<ExtractResponse>('/api/recipes/extract', { url }),
  })
}
