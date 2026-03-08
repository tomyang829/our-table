import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '@/mocks/server'
import { mockUserRecipe } from '@/mocks/handlers'
import { renderWithProviders } from '@/test/renderWithProviders'
import { DashboardPage } from './DashboardPage'

const OPTS = { route: '/dashboard', path: '/dashboard' }

describe('DashboardPage', () => {
  it('shows loading skeleton while fetching recipes', () => {
    server.use(
      http.get('/api/recipes/mine', async () => {
        await new Promise((r) => setTimeout(r, 200))
        return HttpResponse.json([mockUserRecipe])
      }),
    )
    renderWithProviders(<DashboardPage />, OPTS)
    expect(screen.getByRole('status', { name: /loading recipes/i })).toBeInTheDocument()
  })

  it('renders recipe list after successful fetch', async () => {
    renderWithProviders(<DashboardPage />, OPTS)
    expect(await screen.findByText(mockUserRecipe.title)).toBeInTheDocument()
    expect(screen.getByText(/2 ingredients/i)).toBeInTheDocument()
  })

  it('renders welcome message with user name', async () => {
    renderWithProviders(<DashboardPage />, OPTS)
    expect(await screen.findByText(/welcome, test user/i)).toBeInTheDocument()
  })

  it('renders empty state when user has no recipes', async () => {
    server.use(http.get('/api/recipes/mine', () => HttpResponse.json([])))
    renderWithProviders(<DashboardPage />, OPTS)
    expect(await screen.findByText(/no recipes yet/i)).toBeInTheDocument()
  })

  it('shows error alert when fetch fails', async () => {
    server.use(
      http.get('/api/recipes/mine', () => new HttpResponse(null, { status: 500 })),
    )
    renderWithProviders(<DashboardPage />, OPTS)
    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })

  it('renders Add Recipe link in header', async () => {
    renderWithProviders(<DashboardPage />, OPTS)
    await screen.findByText(mockUserRecipe.title)
    const addLinks = screen.getAllByRole('link', { name: /add recipe/i })
    expect(addLinks.length).toBeGreaterThan(0)
  })

  it('recipe card links to detail page', async () => {
    renderWithProviders(<DashboardPage />, OPTS)
    const link = await screen.findByRole('link', { name: new RegExp(mockUserRecipe.title, 'i') })
    expect(link).toHaveAttribute('href', `/recipes/${mockUserRecipe.id}`)
  })
})
