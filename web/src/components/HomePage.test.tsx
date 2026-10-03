import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { HomePage } from './HomePage'

const createRoom = vi.fn()
const joinRoom = vi.fn()
let mockState: any
vi.mock('../state/GameContext', () => ({
  useGame: () => ({
    state: mockState,
    actions: { createRoom, joinRoom, clearError: vi.fn() },
  }),
}))

describe('HomePage', () => {
  beforeEach(() => {
    createRoom.mockClear()
    joinRoom.mockClear()
    localStorage.clear()
    window.history.pushState({}, '', '/')
    mockState = { connection: 'connected', error: '', updateAvailable: false, serverVersion: null }
  })

  it('creates a single-player cloud room', async () => {
    render(<HomePage />)
    await userEvent.type(screen.getByLabelText('玩家昵称'), '玄德')
    await userEvent.click(screen.getByRole('button', { name: '单人游戏' }))
    expect(createRoom).toHaveBeenCalledWith('玄德', true, 'military-five', false)
  })

  it('creates a military-eight room with the God roster option', async () => {
    render(<HomePage />)
    await userEvent.selectOptions(screen.getByLabelText('对局模式'), 'military-eight')
    await userEvent.click(screen.getByLabelText('允许神将进入候选池'))
    await userEvent.click(screen.getByRole('button', { name: '创建多人房间' }))
    expect(createRoom).toHaveBeenCalledWith('玩家', false, 'military-eight', true)
  })

  it('prefills a shared room URL', () => {
    window.history.pushState({}, '', '/room/7KQ9MX')
    render(<HomePage />)
    expect(screen.getByLabelText('房间码')).toHaveValue('7KQ9MX')
  })

  it('shows a non-blocking new version prompt from server state', () => {
    mockState = { connection: 'connected', error: '', updateAvailable: true, serverVersion: { app_version: '0.4.0', build_commit: 'next', protocol_version: 2 } }
    render(<HomePage />)
    expect(screen.getByRole('status')).toHaveTextContent('新版本可用：v0.4.0')
    expect(screen.getByText(/协议 2/)).toBeInTheDocument()
  })
})
