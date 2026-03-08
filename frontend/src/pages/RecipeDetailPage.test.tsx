import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '@/mocks/server'
import { mockUserRecipe, mockSourceRecipe } from '@/mocks/handlers'
import { renderWithProviders } from '@/test/renderWithProviders'
import { RecipeDetailPage } from './RecipeDetailPage'

const OPTS = { route: '/recipes/1', path: '/recipes/:id' }

describe('RecipeDetailPage', () => {
  it('shows loading skeleton while fetching recipe', () => {
    server.use(
      http.get('/api/recipes/mine/:id', async () => {
        await new Promise((r) => setTimeout(r, 200))
        return HttpResponse.json(mockUserRecipe)
      }),
    )
    renderWithProviders(<RecipeDetailPage />, OPTS)
    expect(screen.getByRole('status', { name: /loading recipe/i })).toBeInTheDocument()
  })

  it('renders recipe title, ingredients, and instructions on success', async () => {
    renderWithProviders(<RecipeDetailPage />, OPTS)
    expect(await screen.findByText(mockUserRecipe.title)).toBeInTheDocument()
    // "1 cup flour" appears in both user recipe and "Compare with original" section
    expect(screen.getAllByText('1 cup flour').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Mix ingredients')).toBeInTheDocument()
    expect(screen.getByText('Bake at 350°F')).toBeInTheDocument()
  })

  it('shows error alert when fetch fails', async () => {
    server.use(
      http.get('/api/recipes/mine/:id', () => new HttpResponse(null, { status: 404 })),
    )
    renderWithProviders(<RecipeDetailPage />, OPTS)
    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })

  it('entering edit mode shows form fields pre-populated with recipe data', async () => {
    const user = userEvent.setup()
    renderWithProviders(<RecipeDetailPage />, OPTS)
    await screen.findByText(mockUserRecipe.title)
    await user.click(screen.getByRole('button', { name: /edit recipe/i }))

    const titleInput = screen.getByLabelText(/^title$/i) as HTMLInputElement
    expect(titleInput.value).toBe(mockUserRecipe.title)

    // Each ingredient and step gets its own input
    expect(
      (screen.getByRole('textbox', { name: /ingredient 1/i }) as HTMLTextAreaElement).value,
    ).toBe('1 cup flour')
    expect(
      (screen.getByRole('textbox', { name: /step 1/i }) as HTMLTextAreaElement).value,
    ).toBe('Mix ingredients')
  })

  it('saves changes and returns to view mode', async () => {
    const user = userEvent.setup()
    renderWithProviders(<RecipeDetailPage />, OPTS)
    await screen.findByText(mockUserRecipe.title)

    await user.click(screen.getByRole('button', { name: /edit recipe/i }))
    const titleInput = screen.getByLabelText(/^title$/i)
    await user.clear(titleInput)
    await user.type(titleInput, 'Updated Title')

    await user.click(screen.getByRole('button', { name: /save changes/i }))

    // Returns to view mode — Edit Recipe button reappears
    expect(await screen.findByRole('button', { name: /edit recipe/i })).toBeInTheDocument()
    expect(screen.queryByLabelText(/^title$/i)).not.toBeInTheDocument()
  })

  it('cancels edit mode without saving', async () => {
    const user = userEvent.setup()
    renderWithProviders(<RecipeDetailPage />, OPTS)
    await screen.findByText(mockUserRecipe.title)

    await user.click(screen.getByRole('button', { name: /edit recipe/i }))
    expect(screen.getByLabelText(/^title$/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /^cancel$/i }))
    expect(screen.queryByLabelText(/^title$/i)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /edit recipe/i })).toBeInTheDocument()
  })

  it('shows error alert when save fails', async () => {
    server.use(
      http.put('/api/recipes/mine/:id', () => new HttpResponse(null, { status: 500 })),
    )
    const user = userEvent.setup()
    renderWithProviders(<RecipeDetailPage />, OPTS)
    await screen.findByText(mockUserRecipe.title)

    await user.click(screen.getByRole('button', { name: /edit recipe/i }))
    await user.click(screen.getByRole('button', { name: /save changes/i }))

    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })

  it('shows "Compare with original" section when source_recipe is present', async () => {
    renderWithProviders(<RecipeDetailPage />, OPTS)
    await screen.findByText(mockUserRecipe.title)
    expect(screen.getByText(/compare with original/i)).toBeInTheDocument()
  })

  it('shows the original source URL as a link inside "Compare with original"', async () => {
    renderWithProviders(<RecipeDetailPage />, OPTS)
    await screen.findByText(mockUserRecipe.title)
    const link = screen.getByRole('link', { name: mockSourceRecipe.url })
    expect(link).toHaveAttribute('href', mockSourceRecipe.url)
    expect(link).toHaveAttribute('target', '_blank')
  })

  it('back button navigates to dashboard', async () => {
    const user = userEvent.setup()
    renderWithProviders(<RecipeDetailPage />, OPTS)
    await screen.findByText(mockUserRecipe.title)
    await user.click(screen.getByRole('button', { name: /← back/i }))
    expect(screen.getByTestId('navigated-page')).toBeInTheDocument()
  })

  it('shows confirmation UI when Delete is clicked', async () => {
    const user = userEvent.setup()
    renderWithProviders(<RecipeDetailPage />, OPTS)
    await screen.findByText(mockUserRecipe.title)
    await user.click(screen.getByRole('button', { name: /^delete$/i }))
    expect(screen.getByRole('group', { name: /confirm delete/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /yes, delete/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^cancel$/i })).toBeInTheDocument()
  })

  it('cancelling delete confirmation restores the Delete button', async () => {
    const user = userEvent.setup()
    renderWithProviders(<RecipeDetailPage />, OPTS)
    await screen.findByText(mockUserRecipe.title)
    await user.click(screen.getByRole('button', { name: /^delete$/i }))
    await user.click(screen.getByRole('button', { name: /^cancel$/i }))
    expect(screen.queryByRole('group', { name: /confirm delete/i })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^delete$/i })).toBeInTheDocument()
  })

  it('confirming delete navigates to dashboard', async () => {
    const user = userEvent.setup()
    renderWithProviders(<RecipeDetailPage />, OPTS)
    await screen.findByText(mockUserRecipe.title)
    await user.click(screen.getByRole('button', { name: /^delete$/i }))
    await user.click(screen.getByRole('button', { name: /yes, delete/i }))
    expect(await screen.findByTestId('navigated-page')).toBeInTheDocument()
  })

  it('shows error alert when delete fails', async () => {
    server.use(
      http.delete('/api/recipes/mine/:id', () => new HttpResponse(null, { status: 500 })),
    )
    const user = userEvent.setup()
    renderWithProviders(<RecipeDetailPage />, OPTS)
    await screen.findByText(mockUserRecipe.title)
    await user.click(screen.getByRole('button', { name: /^delete$/i }))
    await user.click(screen.getByRole('button', { name: /yes, delete/i }))
    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })
})
