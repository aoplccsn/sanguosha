import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { GamePage, ResultOverlay } from './GamePage'

const submitDecision = vi.fn()
const returnHome = vi.fn()
let request: any
const card = { card_id: 'slash-1', name: '杀', suit: '♠', rank: '7', definition_id: 'basic.slash', category: 'basic', equipment_slot: '', details: '' }
const players = [
  { player_id: 'p1', name: '你 · 房主', character_name: '曹操', identity_label: '主公', hp: 4, max_hp: 4, hand_count: 1, alive: true, active: true, character_id: 'caocao', faction: '魏', chained: false, equipment: [], judgments: [], base_distance: null, effective_distance: null, attack_range: 1, skill_labels: ['奸雄'] },
  { player_id: 'p2', name: '来宾', character_name: '刘备', identity_label: '未知', hp: 4, max_hp: 4, hand_count: 4, alive: true, active: false, character_id: 'liubei', faction: '蜀', chained: false, equipment: [], judgments: [], base_distance: 1, effective_distance: 1, attack_range: 1, skill_labels: ['仁德'] },
  ...['p3', 'p4', 'p5'].map((id, index) => ({ player_id: id, name: '玩家' + (index + 3), character_name: '武将', identity_label: '未知', hp: 4, max_hp: 4, hand_count: 4, alive: true, active: false, character_id: '', faction: '群', chained: false, equipment: [], judgments: [], base_distance: 2, effective_distance: 2, attack_range: 1, skill_labels: [] })),
]

vi.mock('../state/GameContext', () => ({
  useGame: () => ({
    state: {
      seatId: 'p1',
      projection: { players, hand: [card], current_phase: 'play', turn_number: 1, deck_count: 120, discard_count: 5, result: null, discard_top: null, shared_cards: [] },
      pendingRequest: request,
      publicEvents: [],
      generals: {},
      result: null,
      error: '',
    },
    actions: { submitDecision, returnHome, clearError: vi.fn() },
  }),
}))

describe('GamePage', () => {
  beforeEach(() => { submitDecision.mockClear(); request = null })

  it('renders the five-player table, hand and skill bar', () => {
    render(<GamePage />)
    expect(screen.getAllByText(/手牌/)).toHaveLength(5)
    expect(screen.getByRole('button', { name: /杀/ })).toBeDisabled()
    expect(screen.getByLabelText('技能栏')).toBeInTheDocument()
  })

  it('requires confirm after selecting a response card', async () => {
    request = { request_id: 'r1', player_id: 'p1', request_type: 'respond_with_card', prompt: '请打出闪', choices: [], allowed_player_ids: [], required_definition_id: 'basic.dodge', eligible_card_ids: ['slash-1'], allow_pass: true, min_count: 1, max_count: 1, subject_player_id: 'p2', remaining_ms: 30000 }
    render(<GamePage />)
    await userEvent.click(screen.getByRole('button', { name: /杀/ }))
    expect(submitDecision).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button', { name: '确定' }))
    expect(submitDecision).toHaveBeenCalledWith('r1', 'slash-1')
  })

  it('selects a target before submitting it', async () => {
    request = { request_id: 'r2', player_id: 'p1', request_type: 'choose_player', prompt: '选择目标', choices: [], allowed_player_ids: ['p2'], required_definition_id: 'basic.slash', eligible_card_ids: [], allow_pass: false, min_count: 1, max_count: 1, subject_player_id: null, remaining_ms: 30000 }
    render(<GamePage />)
    await userEvent.click(screen.getByText('来宾'))
    expect(submitDecision).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button', { name: '确定' }))
    expect(submitDecision).toHaveBeenCalledWith('r2', 'p2')
  })
})

describe('ResultOverlay', () => {
  it('returns to home from the result screen', async () => {
    render(<ResultOverlay result="主公与忠臣胜利" onHome={returnHome} />)
    expect(screen.getByRole('dialog', { name: '对局结果' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: '返回首页' }))
    expect(returnHome).toHaveBeenCalled()
  })
})
