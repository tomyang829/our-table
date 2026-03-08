import { useQuery } from '@tanstack/react-query'
import { api } from '@/api'
import type { User } from '@/types'

export function useUser() {
  return useQuery({
    queryKey: ['user', 'me'],
    queryFn: () => api.get<User>('/api/users/me'),
    retry: false,
    staleTime: Infinity,
  })
}
