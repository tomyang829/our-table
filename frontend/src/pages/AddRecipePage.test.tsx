import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '@/mocks/server'
import { mockSourceRecipe, mockUserRecipe } from '@/mocks/handlers'
import { renderWithProviders } from '@/test/renderWithProviders'
import { AddRecipePage } from './AddRecipePage'

const OPTS = { route: '/recipes/add', path: '/recipes/add' }

async function fillAndSubmit(url = 'https://example.com/recipe') {
  const user = userEvent.setup()
  await user.type(screen.getByLabelText(/recipe url/i), url)
  await user.click(screen.getByRole('button', { name: /extract recipe/i }))
  return user
}

describe('AddRecipePage', () => {
  it('renders URL input form', () => {
    renderWithProviders(<AddRecipePage />, OPTS)
    expect(screen.getByLabelText(/recipe url/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /extract recipe/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
  })

  it('shows extracting state while request is pending', async () => {
    server.use(
      http.post('/api/recipes/extract', async () => {
        await new Promise((r) => setTimeout(r, 200))
        return HttpResponse.json({ source_recipe: mockSourceRecipe, already_saved: false })
      }),
    )
    renderWithProviders(<AddRecipePage />, OPTS)
    await fillAndSubmit()
    expect(screen.getByRole('button', { name: /extracting/i })).toBeInTheDocument()
  })

  it('shows extracted recipe preview on success', async () => {
    renderWithProviders(<AddRecipePage />, OPTS)
    await fillAndSubmit()
    expect(await screen.findByText(mockSourceRecipe.title)).toBeInTheDocument()
    expect(screen.getByText(/a test recipe/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /save recipe/i })).toBeInTheDocument()
  })

  it('shows error alert on extract failure', async () => {
    server.use(
      http.post('/api/recipes/extract', () => new HttpResponse(null, { status: 500 })),
    )
    renderWithProviders(<AddRecipePage />, OPTS)
    await fillAndSubmit()
    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })

  it('shows duplicate conflict dialog on 409 from extract', async () => {
    server.use(
      http.post('/api/recipes/extract', () =>
        HttpResponse.json(
          { detail: 'Already saved', source_recipe_id: mockSourceRecipe.id, user_recipe_id: mockUserRecipe.id },
          { status: 409 },
        ),
      ),
    )
    renderWithProviders(<AddRecipePage />, OPTS)
    await fillAndSubmit()
    expect(await screen.findByRole('dialog', { name: /duplicate recipe/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /view existing recipe/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /save another copy/i })).toBeInTheDocument()
  })

  it('shows duplicate conflict dialog when already_saved is true', async () => {
    server.use(
      http.post('/api/recipes/extract', () =>
        HttpResponse.json({
          source_recipe: mockSourceRecipe,
          already_saved: true,
          user_recipe_id: mockUserRecipe.id,
        }),
      ),
    )
    renderWithProviders(<AddRecipePage />, OPTS)
    await fillAndSubmit()
    expect(await screen.findByRole('dialog', { name: /duplicate recipe/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /view existing recipe/i })).toBeInTheDocument()
  })

  it('navigates to recipe detail after saving', async () => {
    renderWithProviders(<AddRecipePage />, OPTS)
    await fillAndSubmit()
    await screen.findByRole('button', { name: /save recipe/i })
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /save recipe/i }))
    expect(await screen.findByTestId('navigated-page')).toBeInTheDocument()
  })

  it('saves another copy from conflict dialog after 409 and navigates', async () => {
    server.use(
      http.post('/api/recipes/extract', () =>
        HttpResponse.json(
          { detail: 'Already saved', source_recipe_id: mockSourceRecipe.id, user_recipe_id: mockUserRecipe.id },
          { status: 409 },
        ),
      ),
    )
    renderWithProviders(<AddRecipePage />, OPTS)
    await fillAndSubmit()
    await screen.findByRole('dialog', { name: /duplicate recipe/i })
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /save another copy/i }))
    expect(await screen.findByTestId('navigated-page')).toBeInTheDocument()
  })

  it('shows save error alert when save fails', async () => {
    server.use(
      http.post('/api/recipes/source/:id/save', () => new HttpResponse(null, { status: 500 })),
    )
    renderWithProviders(<AddRecipePage />, OPTS)
    await fillAndSubmit()
    await screen.findByRole('button', { name: /save recipe/i })
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /save recipe/i }))
    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })
})
