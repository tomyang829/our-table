import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api'
import type { UserRecipe } from '@/types'

export function useUploadRecipeImage() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ recipeId, file }: { recipeId: number; file: File }) =>
      api.uploadRecipeImage<UserRecipe>(`/api/recipes/mine/${recipeId}/image`, file),
    onSuccess: (data) => {
      queryClient.setQueryData(['recipes', 'mine', data.id], data)
      queryClient.invalidateQueries({ queryKey: ['recipes', 'mine'] })
    },
  })
}
