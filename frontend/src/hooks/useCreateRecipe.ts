import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api'
import type { CreateRecipeInput, UserRecipe } from '@/types'

export function useCreateRecipe() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateRecipeInput) => api.post<UserRecipe>('/api/recipes/mine', body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['recipes', 'mine'] })
    },
  })
}
