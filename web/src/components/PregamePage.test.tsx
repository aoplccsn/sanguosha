import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { PregamePage } from './PregamePage'

const selectGeneral = vi.fn()
const confirmGeneral = vi.fn()
vi.mock('../state/GameContext', () => ({
  useGame: () => ({
    state: {
      selectedGeneral: '',
      generals: {
        caocao: {
          id: 'caocao', name: '曹操', kingdom: 'wei', max_hp: 4,
          portrait: '/cao.png', gender: 'male',
          skills: [{ id: 'jianxiong', name: '奸雄', description: '受伤后获得牌。', type: 'triggered' }],
        },
      },
      draft: {
        identity: 'lord', lord_id: 'p1',
        request: { request_id: 'draft:p1:1', remaining_ms: 30000, choices: ['caocao'] },
      },
    },
    actions: { selectGeneral, confirmGeneral },
  }),
}))

describe('PregamePage', () => {
  it('shows identity and requires a deliberate general selection', async () => {
    render(<PregamePage />)
    expect(screen.getByText('主公')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '确认武将' })).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: /曹操/ }))
    expect(selectGeneral).toHaveBeenCalledWith('caocao')
  })
})
