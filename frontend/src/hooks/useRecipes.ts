import { useQuery } from '@tanstack/react-query'
import { api } from '@/api'
import type { UserRecipe } from '@/types'

export function useMyRecipes() {
  return useQuery({
    queryKey: ['recipes', 'mine'],
    queryFn: () => api.get<UserRecipe[]>('/api/recipes/mine'),
  })
}

export function useRecipe(id: number | undefined) {
  return useQuery({
    queryKey: ['recipes', 'mine', id],
    queryFn: () => api.get<UserRecipe>(`/api/recipes/mine/${id}`),
    enabled: id !== undefined && id > 0,
  })
}
