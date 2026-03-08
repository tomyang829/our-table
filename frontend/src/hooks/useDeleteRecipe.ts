import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api'

export function useDeleteRecipe() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.delete<void>(`/api/recipes/mine/${id}`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['recipes', 'mine'] })
    },
  })
}
