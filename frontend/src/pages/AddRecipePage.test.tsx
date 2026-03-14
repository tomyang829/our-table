import { afterEach, describe, it, expect } from 'vitest'
import { act, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '@/mocks/server'
import { mockSourceRecipe, mockUserRecipe } from '@/mocks/handlers'
import { renderWithProviders } from '@/test/renderWithProviders'
import { AddRecipePage } from './AddRecipePage'

const OPTS = { route: '/recipes/add', path: '/recipes/add' }

class MockSpeechRecognition {
  static instances: MockSpeechRecognition[] = []

  lang = 'en-US'
  continuous = false
  interimResults = false
  onresult: ((event: unknown) => void) | null = null
  onerror: ((event: unknown) => void) | null = null
  onend: (() => void) | null = null

  constructor() {
    MockSpeechRecognition.instances.push(this)
  }

  static latest() {
    const instance = MockSpeechRecognition.instances.at(-1)
    if (!instance) throw new Error('No mock speech recognition instance')
    return instance
  }

  start() {}

  stop() {
    this.onend?.()
  }

  emitResult(transcript: string, isFinal = true) {
    this.onresult?.({
      resultIndex: 0,
      results: {
        length: 1,
        0: {
          isFinal,
          0: { transcript },
        },
      },
    })
  }

  emitError(error: string) {
    this.onerror?.({ error })
  }

  emitEnd() {
    this.onend?.()
  }
}

function installSpeechRecognitionMock() {
  MockSpeechRecognition.instances = []
  Object.defineProperty(window, 'SpeechRecognition', {
    configurable: true,
    writable: true,
    value: MockSpeechRecognition,
  })
  Object.defineProperty(window, 'webkitSpeechRecognition', {
    configurable: true,
    writable: true,
    value: undefined,
  })
}

function removeSpeechRecognitionMock() {
  Object.defineProperty(window, 'SpeechRecognition', {
    configurable: true,
    writable: true,
    value: undefined,
  })
  Object.defineProperty(window, 'webkitSpeechRecognition', {
    configurable: true,
    writable: true,
    value: undefined,
  })
}

afterEach(() => {
  removeSpeechRecognitionMock()
})

async function fillAndSubmit(url = 'https://example.com/recipe') {
  const user = userEvent.setup()
  await user.type(screen.getByLabelText(/recipe url/i), url)
  await user.click(screen.getByRole('button', { name: /extract recipe/i }))
  return user
}

describe('AddRecipePage', () => {
  it('shows unsupported fallback message and still allows manual submit', async () => {
    removeSpeechRecognitionMock()
    renderWithProviders(<AddRecipePage />, OPTS)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /create from scratch/i }))
    expect(
      screen.getByText(/dictation is not supported in this browser/i),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /start ingredients dictation/i }),
    ).not.toBeInTheDocument()
    await user.type(screen.getByLabelText(/^title$/i), 'Manual Soup')
    await user.click(screen.getByRole('button', { name: /create recipe/i }))
    expect(await screen.findByTestId('navigated-page')).toBeInTheDocument()
  })

  it('renders URL input form', () => {
    renderWithProviders(<AddRecipePage />, OPTS)
    expect(screen.getByLabelText(/recipe url/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /extract recipe/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create from scratch/i })).toBeInTheDocument()
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
          {
            detail: {
              message: 'You have already saved this recipe',
              source_recipe_id: mockSourceRecipe.id,
              existing_recipe_id: mockUserRecipe.id,
            },
          },
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
          {
            detail: {
              message: 'You have already saved this recipe',
              source_recipe_id: mockSourceRecipe.id,
              existing_recipe_id: mockUserRecipe.id,
            },
          },
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

  it('renders manual recipe form when create from scratch is selected', async () => {
    installSpeechRecognitionMock()
    renderWithProviders(<AddRecipePage />, OPTS)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /create from scratch/i }))
    expect(screen.getByLabelText(/^title$/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/ingredients \(one per line\)/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/instructions \(one step per line\)/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create recipe/i })).toBeInTheDocument()
  })

  it('creates a recipe from scratch and navigates to detail', async () => {
    installSpeechRecognitionMock()
    renderWithProviders(<AddRecipePage />, OPTS)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /create from scratch/i }))
    await user.type(screen.getByLabelText(/^title$/i), 'Pantry Pasta')
    await user.type(screen.getByLabelText(/ingredients \(one per line\)/i), 'pasta{enter}olive oil')
    await user.type(screen.getByLabelText(/instructions \(one step per line\)/i), 'Boil pasta{enter}Toss')
    await user.click(screen.getByRole('button', { name: /create recipe/i }))
    expect(await screen.findByTestId('navigated-page')).toBeInTheDocument()
  })

  it('shows error alert when creating from scratch fails', async () => {
    installSpeechRecognitionMock()
    server.use(http.post('/api/recipes/mine', () => new HttpResponse(null, { status: 500 })))
    renderWithProviders(<AddRecipePage />, OPTS)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /create from scratch/i }))
    await user.type(screen.getByLabelText(/^title$/i), 'Pantry Pasta')
    await user.click(screen.getByRole('button', { name: /create recipe/i }))
    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })

  it('dictates into ingredients and toggles listening states', async () => {
    installSpeechRecognitionMock()
    renderWithProviders(<AddRecipePage />, OPTS)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /create from scratch/i }))

    await user.click(screen.getByRole('button', { name: /start ingredients dictation/i }))

    const recognition = MockSpeechRecognition.latest()
    await act(async () => {
      recognition.emitResult('2 cups flour')
    })
    expect(screen.getByLabelText(/ingredients \(one per line\)/i)).toHaveValue('2 cups flour')

    const instructionsStart = screen.getByRole('button', { name: /start instructions dictation/i })
    expect(instructionsStart).toBeDisabled()

    await act(async () => {
      recognition.emitEnd()
    })
    expect(
      screen.getByRole('button', { name: /start ingredients dictation/i }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /start instructions dictation/i }),
    ).toBeInTheDocument()
  })

  it('dictates into instructions and appends new lines', async () => {
    installSpeechRecognitionMock()
    renderWithProviders(<AddRecipePage />, OPTS)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /create from scratch/i }))
    await user.type(screen.getByLabelText(/instructions \(one step per line\)/i), 'Existing step')

    await user.click(screen.getByRole('button', { name: /start instructions dictation/i }))

    const recognition = MockSpeechRecognition.latest()
    await act(async () => {
      recognition.emitResult('Second step')
    })

    expect(screen.getByLabelText(/instructions \(one step per line\)/i)).toHaveValue(
      'Existing step\nSecond step',
    )
  })

  it('shows dictation error, then clears it when restarting dictation', async () => {
    installSpeechRecognitionMock()
    renderWithProviders(<AddRecipePage />, OPTS)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /create from scratch/i }))

    await user.click(screen.getByRole('button', { name: /start ingredients dictation/i }))
    const firstRecognition = MockSpeechRecognition.latest()
    await act(async () => {
      firstRecognition.emitError('network')
    })
    expect(await screen.findByRole('alert')).toHaveTextContent(/speech dictation failed: network/i)
    await act(async () => {
      firstRecognition.emitEnd()
    })

    await user.click(screen.getByRole('button', { name: /start ingredients dictation/i }))
    expect(screen.queryByText(/speech dictation failed/i)).not.toBeInTheDocument()
  })
})
