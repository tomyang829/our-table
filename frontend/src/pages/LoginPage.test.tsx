import { describe, it, expect, vi, afterEach } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '@/test/renderWithProviders'
import { LoginPage } from './LoginPage'

describe('LoginPage', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders heading and description', () => {
    renderWithProviders(<LoginPage />, { route: '/login', path: '/login' })
    expect(screen.getByRole('heading', { name: /our table/i })).toBeInTheDocument()
    expect(screen.getByText(/save and personalise/i)).toBeInTheDocument()
  })

  it('renders Google and GitHub login buttons', () => {
    renderWithProviders(<LoginPage />, { route: '/login', path: '/login' })
    expect(screen.getByRole('button', { name: /continue with google/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /continue with github/i })).toBeInTheDocument()
  })

  it('clicking Google button redirects to Google OAuth endpoint', async () => {
    const user = userEvent.setup()
    const hrefSetter = vi.fn()
    vi.spyOn(window, 'location', 'get').mockReturnValue({
      ...window.location,
      set href(v: string) {
        hrefSetter(v)
      },
    } as Location)

    renderWithProviders(<LoginPage />, { route: '/login', path: '/login' })
    await user.click(screen.getByRole('button', { name: /continue with google/i }))
    expect(hrefSetter).toHaveBeenCalledWith('/api/auth/google')
  })

  it('clicking GitHub button redirects to GitHub OAuth endpoint', async () => {
    const user = userEvent.setup()
    const hrefSetter = vi.fn()
    vi.spyOn(window, 'location', 'get').mockReturnValue({
      ...window.location,
      set href(v: string) {
        hrefSetter(v)
      },
    } as Location)

    renderWithProviders(<LoginPage />, { route: '/login', path: '/login' })
    await user.click(screen.getByRole('button', { name: /continue with github/i }))
    expect(hrefSetter).toHaveBeenCalledWith('/api/auth/github')
  })
})
