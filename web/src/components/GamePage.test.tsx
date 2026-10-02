import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { GamePage, ResultOverlay, portraitState } from './GamePage'

const submitDecision = vi.fn()
const returnHome = vi.fn()
let request: any
let generals: Record<string, any> = {}
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
      generals,
      result: null,
      error: '',
    },
    actions: { submitDecision, returnHome, clearError: vi.fn() },
  }),
}))

describe('GamePage', () => {
  beforeEach(() => { submitDecision.mockClear(); request = null; generals = {}; players[0].character_id = 'caocao'; players[0].skill_labels = ['奸雄']; delete (players[0] as any).special_piles; delete (players[0] as any).active_transformation; delete (players[0] as any).transformation_pool })

  it('maps shared portrait state for turn, target, response and chain feedback', () => {
    const state = portraitState({ ...players[1], face_up: false, chained: true }, true, true, true)
    expect(state).toMatchObject({ currentTurn: false, selectableTarget: true, selectedTarget: true, waitingResponse: true, chained: true, faceDown: true })
  })

  it('renders the five-player table, hand and skill bar', () => {
    render(<GamePage />)
    expect(screen.getAllByText(/手牌/)).toHaveLength(5)
    expect(screen.getByRole('button', { name: /杀/ })).toBeDisabled()
    expect(screen.getByLabelText('技能栏')).toBeInTheDocument()
  })

  it('shows Mountain field and private transformation state', () => {
    ;(players[0] as any).special_piles = { tian: [{ ...card, card_id: 'field-1' }] }
    ;(players[0] as any).active_transformation = 'wind_wei_yan'
    ;(players[0] as any).transformation_pool = ['wind_wei_yan', 'fire_xun_yu']
    render(<GamePage />)
    expect(screen.getByText('田 1')).toBeInTheDocument()
    expect(screen.getByText('化身 wind_wei_yan')).toBeInTheDocument()
    expect(screen.getByText('化身池 2')).toBeInTheDocument()
  })

  it('requires confirm after selecting a response card', async () => {
    request = { request_id: 'r1', player_id: 'p1', request_type: 'respond_with_card', prompt: '请打出闪', choices: [], allowed_player_ids: [], required_definition_id: 'basic.dodge', eligible_card_ids: ['slash-1'], allow_pass: true, min_count: 1, max_count: 1, subject_player_id: 'p2', remaining_ms: 30000 }
    render(<GamePage />)
    await userEvent.click(screen.getByRole('button', { name: /杀/ }))
    expect(submitDecision).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button', { name: '确定' }))
    expect(submitDecision).toHaveBeenCalledWith('r1', 'slash-1')
  })

  it('offers Guhuo in a response window and submits the virtual choice', async () => {
    players[0].character_id = 'wind_yuji'
    players[0].skill_labels = ['蛊惑']
    generals = { wind_yuji: { skills: [{ id: 'guhuo', name: '蛊惑', type: 'view_as', description: '蛊惑规则' }] } }
    request = { request_id: 'guhuo-response', player_id: 'p1', request_type: 'respond_with_card', prompt: '请打出闪', choices: [], allowed_player_ids: [], required_definition_id: 'basic.dodge', eligible_card_ids: ['virtual:guhuo'], allow_pass: true, min_count: 1, max_count: 1, subject_player_id: 'p1', remaining_ms: 30000 }
    render(<GamePage />)
    await userEvent.click(screen.getByRole('button', { name: '蛊惑' }))
    await userEvent.click(screen.getByRole('button', { name: '确定' }))
    expect(submitDecision).toHaveBeenCalledWith('guhuo-response', 'virtual:guhuo')
  })

  it('submits Jiuchi wine from a hand card during self rescue', async () => {
    players[0].character_id = 'forest_dong_zhuo'
    players[0].skill_labels = ['酒池']
    generals = { forest_dong_zhuo: { skills: [{ id: 'jiuchi', name: '酒池', type: 'view_as', description: '黑桃手牌当酒' }] } }
    request = { request_id: 'jiuchi-rescue', player_id: 'p1', request_type: 'respond_with_card', prompt: '濒死：请打出桃救援或放弃', choices: [], allowed_player_ids: [], required_definition_id: 'basic.peach', eligible_card_ids: ['virtual:jiuchi:slash-1'], allow_pass: true, min_count: 1, max_count: 1, subject_player_id: 'p1', remaining_ms: 30000 }
    render(<GamePage />)
    await userEvent.click(screen.getByRole('button', { name: '酒池' }))
    await userEvent.click(screen.getByRole('button', { name: '确定' }))
    expect(submitDecision).toHaveBeenCalledWith('jiuchi-rescue', 'virtual:jiuchi:slash-1')
  })

  it('lets a physical response replace a previously selected Guhuo option', async () => {
    players[0].character_id = 'wind_yuji'
    players[0].skill_labels = ['蛊惑']
    generals = { wind_yuji: { skills: [{ id: 'guhuo', name: '蛊惑', type: 'view_as', description: '蛊惑规则' }] } }
    request = { request_id: 'guhuo-switch', player_id: 'p1', request_type: 'respond_with_card', prompt: '请打出杀', choices: [], allowed_player_ids: [], required_definition_id: 'basic.slash', eligible_card_ids: ['virtual:guhuo', 'slash-1'], allow_pass: true, min_count: 1, max_count: 1, subject_player_id: 'p2', remaining_ms: 30000 }
    render(<GamePage />)
    await userEvent.click(screen.getByRole('button', { name: '蛊惑' }))
    await userEvent.click(screen.getByRole('button', { name: /杀/ }))
    await userEvent.click(screen.getByRole('button', { name: '确定' }))
    expect(submitDecision).toHaveBeenCalledWith('guhuo-switch', 'slash-1')
  })

  it('labels the two challenge decisions', async () => {
    request = { request_id: 'guhuo-challenge', player_id: 'p1', request_type: 'yes_no', prompt: '蛊惑声明【杀】：是否质疑？', choices: ['declared:basic.slash'], allowed_player_ids: [], required_definition_id: null, eligible_card_ids: [], allow_pass: false, min_count: 0, max_count: 0, subject_player_id: 'p2', remaining_ms: 30000 }
    render(<GamePage />)
    await userEvent.click(screen.getByRole('button', { name: '质疑' }))
    expect(submitDecision).toHaveBeenCalledWith('guhuo-challenge', true)
  })

  it('selects a target before submitting it', async () => {
    request = { request_id: 'r2', player_id: 'p1', request_type: 'choose_player', prompt: 'Choose a target', choices: [], allowed_player_ids: ['p2'], required_definition_id: 'basic.slash', eligible_card_ids: [], allow_pass: false, min_count: 1, max_count: 1, subject_player_id: null, remaining_ms: 30000 }
    render(<GamePage />)
    expect(screen.getByText('请选择目标')).toBeInTheDocument()
    await userEvent.click(screen.getByText('来宾'))
    expect(submitDecision).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button', { name: '确定' }))
    expect(submitDecision).toHaveBeenCalledWith('r2', 'p2')
  })
})

describe('ResultOverlay', () => {
  it('returns to home from the result screen', async () => {
    render(<ResultOverlay result="主公与忠臣胜利" identity="主公" onHome={returnHome} onReplay={vi.fn()} />)
    expect(screen.getByRole('dialog', { name: '对局结果' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: '返回首页' }))
    expect(returnHome).toHaveBeenCalled()
  })
  it('shows defeat when the server winning side differs from the player identity', () => {
    render(<ResultOverlay result="反贼胜利" identity="主公" onHome={returnHome} onReplay={vi.fn()} />)
    expect(screen.getByRole('heading', { name: '败北' })).toBeInTheDocument()
  })
})
