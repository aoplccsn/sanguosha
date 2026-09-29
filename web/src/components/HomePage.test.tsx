import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { HomePage } from './HomePage'

const createRoom = vi.fn()
const joinRoom = vi.fn()
vi.mock('../state/GameContext', () => ({
  useGame: () => ({
    state: { connection: 'connected', error: '' },
    actions: { createRoom, joinRoom, clearError: vi.fn() },
  }),
}))

describe('HomePage', () => {
  beforeEach(() => {
    createRoom.mockClear()
    joinRoom.mockClear()
    localStorage.clear()
    window.history.pushState({}, '', '/')
  })

  it('creates a single-player cloud room', async () => {
    render(<HomePage />)
    await userEvent.type(screen.getByLabelText('玩家昵称'), '玄德')
    await userEvent.click(screen.getByRole('button', { name: '单人游戏' }))
    expect(createRoom).toHaveBeenCalledWith('玄德', true)
  })

  it('prefills a shared room URL', () => {
    window.history.pushState({}, '', '/room/7KQ9MX')
    render(<HomePage />)
    expect(screen.getByLabelText('房间码')).toHaveValue('7KQ9MX')
  })
})
