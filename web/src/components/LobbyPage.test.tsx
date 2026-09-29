import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { LobbyPage } from './LobbyPage'

vi.mock('../state/GameContext', () => ({
  useGame: () => ({
    state: {
      roomCode: '7KQ9MX',
      seatId: 'p1',
      error: '',
      lobby: {
        phase: 'OPEN',
        host_id: 'p1',
        seats: [
          { seat_id: 'p1', player_name: '房主', controller_type: 'HUMAN', ready: false, connected: true },
          { seat_id: 'p2', player_name: '来宾', controller_type: 'HUMAN', ready: true, connected: true },
          ...Array.from({ length: 3 }, (_, index) => ({
            seat_id: 'p' + (index + 3),
            player_name: '',
            controller_type: 'EMPTY',
            ready: false,
            connected: false,
          })),
        ],
      },
    },
    actions: { startGame: vi.fn(), setReady: vi.fn(), returnHome: vi.fn() },
  }),
}))

describe('LobbyPage', () => {
  it('shows five seats and enables host start when guests are ready', () => {
    render(<LobbyPage />)
    expect(screen.getAllByText(/真人|空位/)).toHaveLength(5)
    expect(screen.getByRole('button', { name: '开始游戏' })).toBeEnabled()
    expect(screen.getByText('7KQ9MX')).toBeInTheDocument()
  })
})
