import { act, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { Timer } from './Timer'

describe('Timer', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('renders the server remaining time without advancing game state', () => {
    let now = 0
    vi.spyOn(performance, 'now').mockImplementation(() => now)
    render(<Timer remainingMs={30000} />)
    expect(screen.getByLabelText('剩余 30 秒')).toBeInTheDocument()
    now = 25100
    act(() => vi.advanceTimersByTime(25100))
    expect(screen.getByLabelText('剩余 5 秒')).toHaveClass('urgent')
  })
})
