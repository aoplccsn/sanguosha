import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { GamePage, ResultOverlay, portraitState } from './GamePage'

vi.mock('../idlePortraits', () => ({ idlePortrait: (id: string) => id.includes('god_') || id === 'wind_zhang_jiao' ? { video: '/test-idle.mp4' } : undefined }))

const submitDecision = vi.fn()
const returnHome = vi.fn()
let request: any
let generals: Record<string, any> = {}
let publicEvents: any[] = []
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
      connection: 'connected',
      decisionProcessing: null,
      projection: { players, hand: [card], current_phase: 'play', turn_number: 1, deck_count: 120, discard_count: 5, result: null, discard_top: null, shared_cards: [] },
      pendingRequest: request,
      publicEvents,
      generals,
      result: null,
      error: '',
    },
    actions: { submitDecision, returnHome, clearError: vi.fn() },
  }),
}))

describe('GamePage', () => {
  it('highlights only the real decision actor while thinking and clears for a human request', () => {
    request = null
    publicEvents = [{ event_id: 'thinking', kind: 'AIThinkingEvent', source_id: 'p2', complexity: 'ordinary' }]
    const { container, rerender } = render(<GamePage />)
    expect(screen.getByText('刘备 正在思考……')).toBeInTheDocument()
    expect(container.querySelectorAll('.player-panel.thinking')).toHaveLength(1)
    expect(container.querySelector('[data-player-id="p2"]')).toHaveClass('thinking')
    request = { request_id: 'human', player_id: 'p1', request_type: 'yes_no', prompt: '真人响应', choices: [], eligible_card_ids: [], allowed_player_ids: [], min_count: 0, max_count: 0, remaining_ms: 60000 }
    rerender(<GamePage />)
    expect(screen.getByText('真人响应')).toBeInTheDocument()
    expect(container.querySelectorAll('.player-panel.thinking')).toHaveLength(0)
  })
  beforeEach(() => { submitDecision.mockClear(); request = null; generals = {}; publicEvents = []; card.name = '杀'; card.definition_id = 'basic.slash'; players[0].character_id = 'caocao'; players[0].skill_labels = ['奸雄']; delete (players[0] as any).special_piles; delete (players[0] as any).active_transformation; delete (players[0] as any).transformation_pool })

  it.each([
    [{ event_id: 'slash', kind: 'CardUsedEvent', source_id: 'p1', target_ids: ['p2'], card_name: '杀' }, '曹操 对 刘备 使用【杀】', 'p1', 'p2'],
    [{ event_id: 'dodge', kind: 'CardRespondedEvent', source_id: 'p2', definition_id: 'basic.dodge' }, '刘备 打出【闪】', 'p2', ''],
    [{ event_id: 'skill', kind: 'SkillEvent', source_id: 'p1', skill_name: '奸雄' }, '曹操 发动【奸雄】', 'p1', ''],
  ])('names the actor and highlights action/target for %s', (event, text, actor, target) => {
    publicEvents = [event]
    const { container } = render(<GamePage />)
    expect(screen.getByText(text)).toBeInTheDocument()
    expect(container.querySelector(`[data-player-id="${actor}"]`)).toHaveClass('presenting-action')
    if (target) expect(container.querySelector(`[data-player-id="${target}"]`)).toHaveClass('event-target')
  })

  it('selects a Slash target and submits card plus target with one final confirm', async () => {
    request = { request_id: 'play-1', player_id: 'p1', request_type: 'choose_option', prompt: 'Choose a play action or end the play phase', choices: ['use:slash-1', 'end_play_phase'], allowed_player_ids: [], eligible_card_ids: [], required_definition_id: null, allow_pass: false, min_count: 0, max_count: 0, remaining_ms: 60000,
      play_card_targets: { 'use:slash-1': { targets: ['p2'], min: 1, max: 1 } } }
    render(<GamePage />)
    await userEvent.click(screen.getByRole('button', { name: /杀/ }))
    expect(screen.getByRole('button', { name: /杀/ })).toHaveClass('selected')
    expect(screen.getByText('杀 → 请选择目标')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '确定' })).toBeDisabled()
    await userEvent.click(screen.getByText('来宾'))
    expect(screen.getByText('杀 → 来宾')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: '确定' }))
    expect(submitDecision).toHaveBeenCalledOnce()
    expect(submitDecision).toHaveBeenCalledWith('play-1', { option: 'use:slash-1', targets: ['p2'] })
  })

  it('confirms equipment without requesting a character target', async () => {
    card.name = '的卢'; card.definition_id = 'equipment.horse.dilu'
    request = { request_id: 'play-equip', player_id: 'p1', request_type: 'choose_option', prompt: 'Choose a play action or end the play phase', choices: ['use:slash-1', 'end_play_phase'], allowed_player_ids: [], eligible_card_ids: [], required_definition_id: null, allow_pass: false, min_count: 0, max_count: 0, remaining_ms: 60000,
      play_card_targets: { 'use:slash-1': { targets: [], min: 0, max: 0 } } }
    render(<GamePage />)
    await userEvent.click(screen.getByRole('button', { name: /的卢/ }))
    expect(screen.getAllByText('的卢')).toHaveLength(2)
    expect(screen.getByRole('button', { name: '确定' })).toBeEnabled()
    await userEvent.click(screen.getByRole('button', { name: '确定' }))
    expect(submitDecision).toHaveBeenCalledWith('play-equip', { option: 'use:slash-1', targets: [] })
  })

  it('shows Chinese labels for Yinghun branches while preserving machine values', async () => {
    request = { request_id: 'yinghun-1', player_id: 'p1', request_type: 'choose_option', prompt: '英魂：选择分支', choices: ['draw_x_discard_one', 'draw_one_discard_x'], allowed_player_ids: [], eligible_card_ids: [], required_definition_id: null, allow_pass: false, min_count: 0, max_count: 0, remaining_ms: 60000 }
    render(<GamePage />)
    await userEvent.click(screen.getByRole('button', { name: '摸 X 张，弃一张' }))
    expect(submitDecision).toHaveBeenCalledWith('yinghun-1', 'draw_x_discard_one')
    expect(screen.queryByText('draw_one_discard_x')).not.toBeInTheDocument()
  })

  it('maps shared portrait state for turn, target, response and chain feedback', () => {
    const state = portraitState({ ...players[1], face_up: false, chained: true }, true, true, true)
    expect(state).toMatchObject({ currentTurn: false, selectableTarget: true, selectedTarget: true, waitingResponse: true, chained: true, faceDown: true })
  })

  it('renders the five-player table, hand and skill bar', () => {
    render(<GamePage />)
    expect(screen.getAllByText(/手牌/)).toHaveLength(5)
    expect(screen.getByRole('button', { name: /杀/ })).toHaveAttribute('aria-disabled', 'true')
    expect(screen.getByLabelText('技能栏')).toBeInTheDocument()
  })

  it('shows Mountain field and private transformation state', () => {
    ;(players[0] as any).special_piles = { tian: [{ ...card, card_id: 'field-1' }] }
    ;(players[0] as any).active_transformation = 'wind_wei_yan'
    ;(players[0] as any).transformation_pool = ['wind_wei_yan', 'fire_xun_yu']
    render(<GamePage />)
    expect(screen.getByText('田 1')).toBeInTheDocument()
    expect(screen.getByText('化身 已选择武将')).toBeInTheDocument()
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

describe('T15 dynamic target interaction', () => {
  it('selects immediately on the first portrait click with multiple dynamic panels', async () => {
    const originals = players.map(p => p.character_id)
    players[0].character_id = 'wind_zhang_jiao'
    players[1].character_id = 'forest_god_lvbu'
    players[2].character_id = 'wind_god_guanyu'
    players[3].character_id = 'fire_god_zhouyu'
    players[4].character_id = 'mountain_god_zhaoyun'
    request = { request_id: 't15-target', player_id: 'p1', request_type: 'choose_option', prompt: 'Choose a play action or end the play phase', choices: ['use:slash-1', 'end_play_phase'], allowed_player_ids: [], eligible_card_ids: [], allow_pass: false, min_count: 0, max_count: 0, remaining_ms: 60000, play_card_targets: { 'use:slash-1': { targets: ['p2'], min: 1, max: 1 } } }
    Object.defineProperty(HTMLMediaElement.prototype, 'play', { configurable: true, value: vi.fn(() => Promise.resolve()) })
    Object.defineProperty(HTMLMediaElement.prototype, 'pause', { configurable: true, value: vi.fn() })
    vi.stubGlobal('IntersectionObserver', undefined)
    try {
      const { container } = render(<GamePage />)
      expect(container.querySelectorAll('video')).toHaveLength(5)
      await userEvent.click(screen.getByRole('button', { name: /杀/ }))
      const panel = container.querySelector('[data-player-id="p2"]')!
      await userEvent.click(panel.querySelector('.portrait-button')!)
      expect(panel).toHaveClass('selected-target')
      expect(container.querySelector('.game-general-detail')).toBeNull()
      expect(screen.getByRole('button', { name: '确定' })).toBeEnabled()
    } finally { players.forEach((p, i) => p.character_id = originals[i]); vi.unstubAllGlobals() }
  })
})
