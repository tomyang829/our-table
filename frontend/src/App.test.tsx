import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import App from './App'

describe('App', () => {
  it('renders without crashing', () => {
    render(<App />)
    expect(document.body).toBeTruthy()
  })

  it('redirects / to /dashboard', () => {
    render(<App />)
    expect(screen.getByText('My Recipes')).toBeInTheDocument()
  })
})
