import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api'
import type { UserRecipe } from '@/types'

export function useSaveRecipe() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (sourceId: number) =>
      api.post<UserRecipe>(`/api/recipes/source/${sourceId}/save`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['recipes', 'mine'] })
    },
  })
}
