import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { LoginPage } from '@/pages/LoginPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { AddRecipePage } from '@/pages/AddRecipePage'
import { RecipeDetailPage } from '@/pages/RecipeDetailPage'
import { useUser } from '@/hooks/useUser'
import { TopBanner } from '@/components/TopBanner'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 1000 * 60 * 5,
    },
  },
})

/** Renders children only when authenticated; redirects to /login otherwise. */
function ProtectedRoute() {
  const { isLoading, isError } = useUser()
  if (isLoading) return null
  if (isError) return <Navigate to="/login" replace />
  return (
    <>
      <TopBanner />
      <Outlet />
    </>
  )
}

/** Renders children only when NOT authenticated; redirects to /dashboard otherwise. */
function PublicRoute() {
  const { isLoading, isSuccess } = useUser()
  if (isLoading) return null
  if (isSuccess) return <Navigate to="/dashboard" replace />
  return <Outlet />
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<PublicRoute />}>
            <Route path="/login" element={<LoginPage />} />
          </Route>
          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/recipes/add" element={<AddRecipePage />} />
            <Route path="/recipes/:id" element={<RecipeDetailPage />} />
          </Route>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}
