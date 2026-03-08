import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api'
import type { UserRecipe } from '@/types'

export interface UpdateRecipeInput {
  id: number
  title?: string
  ingredients?: string[]
  instructions?: string[]
  notes?: string | null
  servings?: string | null
}

export function useUpdateRecipe() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...body }: UpdateRecipeInput) =>
      api.put<UserRecipe>(`/api/recipes/mine/${id}`, body),
    onSuccess: (data) => {
      queryClient.setQueryData(['recipes', 'mine', data.id], data)
      void queryClient.invalidateQueries({ queryKey: ['recipes', 'mine'] })
    },
  })
}
