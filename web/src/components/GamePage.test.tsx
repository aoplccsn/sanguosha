import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { GamePage, ResultOverlay, portraitState } from './GamePage'

vi.mock('../idlePortraits', () => ({ idlePortrait: (id: string) => id.includes('god_') || id === 'wind_zhang_jiao' ? { video: '/test-idle.mp4' } : undefined }))

const submitDecision = vi.fn()
const returnHome = vi.fn()
let seatId = 'p1'
let request: any
let waiting: any = undefined
let combat: any = undefined
let generals: Record<string, any> = {}
let publicEvents: any[] = []
let publicHistory: any[] = []
const card = { card_id: 'slash-1', name: '杀', suit: '♠', rank: '7', definition_id: 'basic.slash', category: 'basic', equipment_slot: '', details: '' }
let extraCards: typeof card[] = []
const players = [
  { player_id: 'p1', name: '你 · 房主', character_name: '曹操', identity_label: '主公', hp: 4, max_hp: 4, hand_count: 1, alive: true, active: true, character_id: 'caocao', faction: '魏', chained: false, equipment: [], judgments: [], base_distance: null, effective_distance: null, attack_range: 1, skill_labels: ['奸雄'] },
  { player_id: 'p2', name: '来宾', character_name: '刘备', identity_label: '未知', hp: 4, max_hp: 4, hand_count: 4, alive: true, active: false, character_id: 'liubei', faction: '蜀', chained: false, equipment: [], judgments: [], base_distance: 1, effective_distance: 1, attack_range: 1, skill_labels: ['仁德'] },
  ...['p3', 'p4', 'p5'].map((id, index) => ({ player_id: id, name: '玩家' + (index + 3), character_name: '武将', identity_label: '未知', hp: 4, max_hp: 4, hand_count: 4, alive: true, active: false, character_id: '', faction: '群', chained: false, equipment: [], judgments: [], base_distance: 2, effective_distance: 2, attack_range: 1, skill_labels: [] })),
]

vi.mock('../state/GameContext', () => ({
  useGame: () => ({
    state: {
      seatId,
      connection: 'connected',
      decisionProcessing: null,
      projection: { public_card_history: publicHistory, waiting, combat, players, hand: [card, ...extraCards], current_phase: 'play', turn_number: 1, deck_count: 120, discard_count: 5, result: null, discard_top: null, shared_cards: [] },
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
  it('retains final judgment outcome while showing its public card', () => {
    publicEvents=[{kind:'JudgmentEvent',event_id:'judge-result',source_id:'p1',matched:false,cards:[card]}]
    render(<GamePage />)
    expect(screen.getByText(/\u5224\u5b9a\u672a\u901a\u8fc7/)).toBeInTheDocument()
  })
  it('shows the delayed trick consequence in Chinese', () => {
    publicEvents=[{kind:'DelayedResultEvent',event_id:'delayed-result',source_id:'p1',message:'\u3010\u4e50\u4e0d\u601d\u8700\u3011\u5224\u5b9a\u975e\u7ea2\u6843\uff1a\u8df3\u8fc7\u51fa\u724c\u9636\u6bb5'}]
    render(<GamePage />)
    expect(screen.getByText(/\u8df3\u8fc7\u51fa\u724c\u9636\u6bb5/)).toBeInTheDocument()
  })

  it('labels a recast face as 重铸 in the public presentation', () => {
    publicEvents=[{kind:'DiscardEvent',event_id:'recast-public',player_id:'p1',reason:'recast',cards:[{...card,name:'铁索连环',definition_id:'trick.iron_chain'}]}]
    render(<GamePage />)
    expect(screen.getByText(/重铸：/)).toBeInTheDocument()
    expect(screen.queryByText(/弃置：/)).not.toBeInTheDocument()
  })
  it('acquired Qixi deselect, cancel and normal play are independent contexts', async()=>{
    const original={character_id:players[0].character_id,skill_labels:players[0].skill_labels}
    players[0].character_id='mountain_zuoci';players[0].skill_labels=['化身','奇袭']
    generals={mountain_zuoci:{skills:[{id:'huashen',name:'化身',description:'化身规则',type:'triggered'}]},ganning:{skills:[{id:'qixi',name:'奇袭',description:'黑牌转拆',type:'view_as'}]}}
    extraCards=[{...card,card_id:'peach',name:'桃',suit:'♥',definition_id:'basic.peach'}]
    request={request_id:'qixi-lifecycle',player_id:'p1',request_type:'choose_option',prompt:'出牌',choices:['virtual:qixi:slash-1','use:peach','end_play_phase'],eligible_card_ids:[],allowed_player_ids:[],min_count:1,max_count:1,remaining_ms:60000}
    const {rerender}=render(<GamePage />)
    await userEvent.click(screen.getAllByRole('button',{name:'奇袭'})[0])
    await userEvent.click(screen.getByRole('button',{name:'杀 ♠7'}))
    await userEvent.click(screen.getByRole('button',{name:'杀 ♠7'}))
    expect(screen.getByRole('button',{name:'确定'})).toBeDisabled()
    await userEvent.click(screen.getByRole('button',{name:'杀 ♠7'}))
    expect(screen.getByRole('button',{name:'确定'})).toBeEnabled()
    await userEvent.click(screen.getByRole('button',{name:'取消选中'}))
    expect(screen.getByRole('button',{name:'桃 ♥7'})).toHaveAttribute('aria-disabled','false')
    await userEvent.click(screen.getByRole('button',{name:'桃 ♥7'}))
    await userEvent.click(screen.getByRole('button',{name:'确定'}))
    expect(submitDecision).toHaveBeenLastCalledWith('qixi-lifecycle','use:peach')
    request={...request,request_id:'changed-avatar',choices:['use:peach']};rerender(<GamePage />)
    expect(screen.getByRole('button',{name:'确定'})).toBeDisabled()
    Object.assign(players[0],original)
  })

  it('renders abolished equipment slots from authoritative projection', () => {
    ;(players[1] as any).abolished_equipment_slots=['weapon','armor']
    render(<GamePage />)
    expect(screen.getByText('已废除 武器栏')).toBeInTheDocument()
    expect(screen.getByText('已废除 防具栏')).toBeInTheDocument()
    delete (players[1] as any).abolished_equipment_slots
  })
  it('renders private Zongxuan cards and submits the selected top-placement order', async () => {
    ;(players[0] as any).special_piles = {'committed:zongxuan:cost':[
      {...card,card_id:'reserved-1'},
      {...card,card_id:'reserved-2',name:'闪',definition_id:'basic.dodge'},
    ]}
    request = {request_id:'zongxuan',player_id:'p1',request_type:'choose_cards',subject_player_id:'p1',
      prompt:'【纵玄】依次选择要置于牌堆顶的牌，最后一张在最上方（可空选）',choices:[],allowed_player_ids:[],eligible_card_ids:['reserved-1','reserved-2'],min_count:0,max_count:2,remaining_ms:60000}
    render(<GamePage />)
    const panel=within(screen.getByRole('dialog',{name:'纵玄'}))
    expect(panel.getByText('待置顶牌')).toBeInTheDocument()
    await userEvent.click(panel.getByRole('button',{name:/^闪 /}))
    await userEvent.click(panel.getByRole('button',{name:/^杀 /}))
    await userEvent.click(panel.getByRole('button',{name:'确定'}))
    expect(submitDecision).toHaveBeenCalledWith('zongxuan',['reserved-2','reserved-1'])
    delete (players[0] as any).special_piles
  })
  it('shows public counter cards in the Xiansi modal and requires exactly two', async () => {
    ;(players[1] as any).special_piles = {counter:[
      {...card,card_id:'counter-1'},
      {...card,card_id:'counter-2',name:'闪',definition_id:'basic.dodge'},
    ]}
    request = {request_id:'xiansi',player_id:'p1',request_type:'choose_cards',subject_player_id:'p2',
      prompt:'【陷嗣】移去两张逆，视为对其使用杀',choices:[],allowed_player_ids:[],eligible_card_ids:['counter-1','counter-2'],min_count:2,max_count:2,remaining_ms:60000}
    render(<GamePage />)
    const panel=within(screen.getByRole('dialog',{name:'陷嗣'}))
    expect(panel.getByText('逆')).toBeInTheDocument()
    await userEvent.click(panel.getByRole('button',{name:/^杀 /}))
    expect(panel.getByRole('button',{name:'确定'})).toBeDisabled()
    await userEvent.click(panel.getByRole('button',{name:/^闪 /}))
    await userEvent.click(panel.getByRole('button',{name:'确定'}))
    expect(submitDecision).toHaveBeenCalledWith('xiansi',['counter-1','counter-2'])
    delete (players[1] as any).special_piles
  })
  it('shows authorized Poxi hand faces and rejects four cards with duplicate suits', async () => {
    extraCards = [
      { ...card, card_id: 'dodge-2', name: '闪', suit: '♥', definition_id: 'basic.dodge' },
      { ...card, card_id: 'wine-3', name: '酒', suit: '♣', definition_id: 'basic.wine' },
    ]
    ;(players[1] as any).revealed_hand = [
      { ...card, card_id: 'fire-4', name: '火攻', suit: '♠', definition_id: 'trick.fire_attack' },
      { ...card, card_id: 'thunder-5', name: '雷杀', suit: '♦', definition_id: 'basic.thunder_slash' },
    ]
    request = { request_id: 'poxi', player_id: 'p1', request_type: 'choose_cards',
      subject_player_id: 'p2', prompt: '【魄袭】选择四张花色各异的牌，或空选放弃', choices: [],
      allowed_player_ids: [], eligible_card_ids: ['slash-1','dodge-2','wine-3','fire-4','thunder-5'],
      min_count: 0, max_count: 4, minimum_nonempty_count: 4, remaining_ms: 60000,
      exclusive_card_groups: [['slash-1','fire-4'],['dodge-2'],['wine-3'],['thunder-5']] }
    render(<GamePage />)
    const panel = within(screen.getByRole('dialog', { name: '魄袭' }))
    for (const name of ['杀','闪','火攻','雷杀']) await userEvent.click(panel.getByRole('button', { name: new RegExp('^'+name+' ') }))
    expect(panel.getByRole('button', { name: '确定' })).toBeDisabled()
    await userEvent.click(panel.getByRole('button', { name: /^火攻 / }))
    await userEvent.click(panel.getByRole('button', { name: /^酒 / }))
    expect(panel.getByRole('button', { name: '确定' })).toBeEnabled()
    await userEvent.click(panel.getByRole('button', { name: '确定' }))
    expect(submitDecision).toHaveBeenCalledWith('poxi', ['slash-1','dodge-2','thunder-5','wine-3'])
  })
  it('permits declining Fencheng but rejects undersized nonempty card selections', async () => {
    extraCards = [
      { ...card, card_id: 'dodge-2', name: '闪', definition_id: 'basic.dodge' },
      { ...card, card_id: 'wine-3', name: '酒', definition_id: 'basic.wine' },
    ]
    request = { request_id: 'fencheng', player_id: 'p1', request_type: 'choose_cards',
      prompt: '【焚城】弃置至少三张牌，否则受到两点火焰伤害', choices: [],
      allowed_player_ids: [], eligible_card_ids: ['slash-1', 'dodge-2', 'wine-3'],
      min_count: 0, max_count: 3, minimum_nonempty_count: 3, remaining_ms: 60000 }
    render(<GamePage />)
    expect(screen.getByRole('button', { name: '确定' })).toBeEnabled()
    await userEvent.click(screen.getByRole('button', { name: /杀/ }))
    expect(screen.getByRole('button', { name: '确定' })).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: /闪/ }))
    expect(screen.getByRole('button', { name: '确定' })).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: /酒/ }))
    expect(screen.getByRole('button', { name: '确定' })).toBeEnabled()
    await userEvent.click(screen.getByRole('button', { name: '确定' }))
    expect(submitDecision).toHaveBeenCalledWith('fencheng', ['slash-1', 'dodge-2', 'wine-3'])
  })
  it('binds a public remote response timer to one seat and restores its server remaining fraction', () => {
    request = null
    waiting = {key:'reconnected',player_id:'p2',responding:true,thinking:false,remaining_ms:12000,total_ms:60000}
    const {container,rerender}=render(<GamePage />)
    expect(container.querySelectorAll('.responding')).toHaveLength(1)
    expect(container.querySelector('[data-player-id="p1"]')).toHaveClass('active')
    expect(container.querySelector('[data-player-id="p2"]')).toHaveClass('responding')
    expect(container.querySelector('[data-player-id="p2"] .seat-timer .timer i')).toHaveStyle({width:'20%'})
    expect(container.querySelectorAll('.seat-timer')).toHaveLength(1)
    expect(container.querySelector('.decision-prompt')).toBeNull()
    waiting=null
    rerender(<GamePage />)
    expect(container.querySelector('.seat-timer')).toBeNull()
    expect(container.querySelector('.responding')).toBeNull()
  })
  it('highlights only the real decision actor while thinking and clears for a human request', () => {
    request = null
    publicEvents = [{ event_id: 'thinking', kind: 'AIThinkingEvent', source_id: 'p2', complexity: 'ordinary' }]
    const { container, rerender } = render(<GamePage />)
    expect(screen.getByText('思考中…')).toBeInTheDocument()
    expect(container.querySelectorAll('.player-panel.thinking')).toHaveLength(1)
    expect(container.querySelector('[data-player-id="p2"]')).toHaveClass('thinking')
    request = { request_id: 'human', player_id: 'p1', request_type: 'yes_no', prompt: '真人响应', choices: [], eligible_card_ids: [], allowed_player_ids: [], min_count: 0, max_count: 0, remaining_ms: 60000 }
    rerender(<GamePage />)
    expect(screen.getByText('真人响应')).toBeInTheDocument()
    expect(container.querySelectorAll('.player-panel.thinking')).toHaveLength(0)
  })
  beforeEach(() => { players.forEach((p) => delete (p as any).revealed_hand); extraCards = []; submitDecision.mockClear(); request = null; waiting = undefined; combat=undefined; generals = {}; publicEvents = []; card.name = '杀'; card.definition_id = 'basic.slash'; players[0].character_id = 'caocao'; players[0].skill_labels = ['奸雄']; delete (players[0] as any).special_piles; delete (players[0] as any).active_transformation; delete (players[0] as any).transformation_pool })

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

  it('shows power pile count without exposing hidden card faces', () => {
    ;(players[0] as any).special_piles = { quan: [
      { card_id: 'hidden:quan:0', name: 'UNKNOWN', suit: '', rank: '' },
      { card_id: 'hidden:quan:1', name: 'UNKNOWN', suit: '', rank: '' },
    ] }
    render(<GamePage />)
    expect(screen.getByText('权 2')).toBeInTheDocument()
    expect(screen.queryByText('UNKNOWN')).not.toBeInTheDocument()
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
    await userEvent.click(screen.getByRole('button', { name: '杀 ♠7' }))
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

describe('T18A.7 response semantics',()=>{
  it('keeps turn phase and binds response description, thinking and countdown to one seat',()=>{
    request=null; publicEvents=[]; waiting={key:'slash',player_id:'p2',responding:true,thinking:true,remaining_ms:8700,total_ms:60000,required_definition_id:'basic.dodge',response_to:'basic.slash'}
    const {container,rerender}=render(<GamePage />)
    expect(container.querySelector('[data-player-id="p1"] .turn-badge')).toHaveTextContent('当前回合 · 出牌')
    const responder=container.querySelector('[data-player-id="p2"] .responder-state')!
    expect(responder).toHaveTextContent('响应【杀】请出【闪】')
    expect(responder).toHaveTextContent('思考中')
    expect(responder.querySelector('.timer')).not.toBeNull()
    waiting=null;rerender(<GamePage />)
    expect(container.querySelector('.responder-state')).toBeNull()
  })
  it('submits distinct current-request and root-trick commands',async()=>{
    waiting=undefined;publicEvents=[]
    request={allow_root_trick_pass:true,request_id:'counter',player_id:'p1',request_type:'respond_with_card',prompt:'无懈可击',choices:[],eligible_card_ids:[],allowed_player_ids:[],min_count:0,max_count:1,allow_pass:true,remaining_ms:60000,required_definition_id:'trick.nullification'}
    render(<GamePage />)
    expect(screen.getByRole('button',{name:'使用无懈'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'不响应'}))
    expect(submitDecision).toHaveBeenLastCalledWith('counter',{pass:true})
    await userEvent.click(screen.getByRole('button',{name:'本轮不再询问'}))
    expect(submitDecision).toHaveBeenLastCalledWith('counter',{pass:true,scope:'root_trick'})
  })
})

it('renders the authoritative AOE targets, root trick and top counter without a second stack UI',()=>{
  request=null;publicEvents=[];waiting={key:'counter',player_id:'p3',responding:true,thinking:false,remaining_ms:8000,required_definition_id:'trick.nullification',response_to:'trick.savage_assault'}
  combat={root_id:'root',source_id:'p1',definition_id:'trick.savage_assault',target_ids:['p2','p3'],resolved_target_ids:['p2'],current_target_id:'p3',nullification_count:2,cancelled:false,top_response:{source_id:'p2',definition_id:'trick.nullification'}}
  const {container}=render(<GamePage />)
  expect(container.querySelector('[data-player-id="p2"]')).toHaveClass('aoe-resolved')
  expect(container.querySelector('[data-player-id="p3"]')).toHaveClass('aoe-current','responding')
  expect(container.querySelector('[data-player-id="p4"]')!.className).not.toContain('aoe-')
  expect(container.querySelector('.base-card img')).toHaveAttribute('alt','南蛮入侵')
  expect(container.querySelector('.response-card img')).toHaveAttribute('alt','无懈可击')
  expect(container.querySelector('.nullification-status')).toHaveTextContent('无懈×2 · 当前锦囊有效')
  combat=undefined;waiting=undefined
})

it('never duplicates opponents while reconnect seat confirmation is pending',()=>{
 seatId='unconfirmed-seat'
 const view=render(<GamePage />)
 const ids=Array.from(view.container.querySelectorAll('.game-board > .player-panel')).map(n=>n.getAttribute('data-player-id'))
 expect(ids).toHaveLength(players.length-1)
 expect(new Set(ids).size).toBe(ids.length)
 seatId='p1';view.rerender(<GamePage />)
})


it('restores delayed outcome text from projection history without live events',()=>{
 publicHistory=[{kind:'DelayedResultEvent',source_id:'p1',message:'\u3010\u95ea\u7535\u3011\u672a\u751f\u6548\uff1a\u4f20\u9012\u81f3\u4e0b\u4e00\u5408\u6cd5\u89d2\u8272'}]
 publicEvents=[]
 try {
  const {container}=render(<GamePage />)
  expect(container.querySelector('.public-card-history')).toHaveTextContent('\u4f20\u9012\u81f3\u4e0b\u4e00\u5408\u6cd5\u89d2\u8272')
 } finally { publicHistory=[] }
})


it('shows signed horse faces and authoritative abolished slots',()=>{
 const player=players[0] as any
 const oldEquipment=player.equipment;const oldSlots=player.abolished_equipment_slots
 const offensive={...card,card_id:'horse-hand',name:'\u8d64\u5154',definition_id:'equipment.horse.chitu',category:'equipment',equipment_slot:'offensive_horse'}
 const defensive={...card,card_id:'horse-equipped',name:'\u7edd\u5f71',definition_id:'equipment.horse.jueying',category:'equipment',equipment_slot:'defensive_horse'}
 extraCards=[offensive];player.equipment=[defensive];player.abolished_equipment_slots=['weapon']
 try {
  const {container}=render(<GamePage />)
  expect(container.querySelector('.equipment-token')).toHaveTextContent('\u7edd\u5f71 +1')
  expect(screen.getByText('\u8d64\u5154 -1')).toBeInTheDocument()
  expect(screen.getByText('\u5df2\u5e9f\u9664 \u6b66\u5668\u680f')).toBeInTheDocument()
 } finally {extraCards=[];player.equipment=oldEquipment;player.abolished_equipment_slots=oldSlots}
})


it('shows each public pindian card beside its original owner', () => {
  request=null;waiting=undefined;combat=undefined
  publicEvents=[{kind:'CardRevealedEvent',event_id:'pindian-public',reason:'pindian',source_id:'p1',target_ids:['p2'],card_owner_ids:['p1','p2'],cards:[card,{...card,name:'闪',definition_id:'basic.dodge'}]}]
  const {container}=render(<GamePage />)
  const faces=container.querySelectorAll('.public-resolution-card')
  expect(faces).toHaveLength(2)
  expect(faces[0]).toHaveTextContent('曹操 · 拼点')
  expect(faces[1]).toHaveTextContent('刘备 · 拼点')
})


it('lets 榻谟 order every nonlord including self and clear a cancelled selection', async () => {
  const original = { identity: players[0].identity_label, name: players[0].character_name }
  players[0].identity_label = '未知'
  players[0].character_name = '神鲁肃'
  const ids = players.map(p => p.player_id)
  request = { request_id: 'tamo-order', player_id: 'p1', request_type: 'choose_players',
    prompt: '榻谟：按新座次顺序选择全部非主公角色', choices: [], allowed_player_ids: ids,
    eligible_card_ids: [], min_count: ids.length, max_count: ids.length, remaining_ms: 60000 }
  try {
    render(<GamePage />)
    await userEvent.click(screen.getByRole('button', { name: '选择目标神鲁肃' }))
    expect(screen.getByRole('button', { name: '确定' })).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: '取消选中' }))
    for (const name of ['刘备', '武将', '神鲁肃']) {
      const buttons = screen.getAllByRole('button', { name: '选择目标' + name })
      for (const button of buttons) await userEvent.click(button)
    }
    expect(screen.getByRole('button', { name: '确定' })).toBeEnabled()
    await userEvent.click(screen.getByRole('button', { name: '确定' }))
    expect(submitDecision).toHaveBeenLastCalledWith('tamo-order', ['p2', 'p3', 'p4', 'p5', 'p1'])
  } finally {
    players[0].identity_label = original.identity
    players[0].character_name = original.name
  }
})
it.each([
  { count: 5, chosen: ['p5', 'p4', 'p2', 'p3'], positions: ['east', 'north-east', 'north-west', 'west'] },
  { count: 8, chosen: ['p5', 'p4', 'p8', 'p2', 'p7', 'p3', 'p6'], positions: ['east-lower', 'east-upper', 'north-east', 'north', 'north-west', 'west-upper', 'west-lower'] },
])('rearranges the $count-player table from the confirmed Tamo projection and restores its local view', async ({ count, chosen, positions }) => {
  const originalPlayers = [...players]
  const originalSeatId = seatId
  const table = Array.from({ length: count }, (_, index) => ({
    ...originalPlayers[index % originalPlayers.length],
    player_id: `p${index + 1}`, name: `玩家${index + 1}`,
    character_id: index === 3 ? 'mobile_god_lusu' : `general-${index + 1}`,
    character_name: index === 3 ? '神鲁肃' : `武将${index + 1}`,
    identity_label: index === 0 ? '主公' : index === 3 ? '忠臣' : '未知',
    hp: index % 3 + 1, active: false, equipment: [], judgments: [], skill_labels: [],
  }))
  const byId = new Map(table.map(player => [player.player_id, player]))
  players.splice(0, players.length, ...table)
  seatId = 'p4'
  publicEvents = []; publicHistory = []; waiting = undefined; combat = undefined
  submitDecision.mockClear()
  request = { request_id: `tamo-table-${count}`, player_id: seatId, request_type: 'choose_players',
    prompt: '榻谟：按新座次顺序选择全部非主公角色', choices: [], allowed_player_ids: chosen,
    eligible_card_ids: [], min_count: count - 1, max_count: count - 1, remaining_ms: 60000 }

  function expectLayout(container: HTMLElement, viewer: string) {
    const selfIndex = players.findIndex(player => player.player_id === viewer)
    const relative = [...players.slice(selfIndex + 1), ...players.slice(0, selfIndex)]
    const opponents = [...container.querySelectorAll<HTMLElement>('.game-board > .player-panel')]
    expect(opponents.map(panel => panel.dataset.playerId)).toEqual(relative.map(player => player.player_id))
    opponents.forEach((panel, index) => expect(panel).toHaveClass(`player-${positions[index]}`))
    expect(container.querySelector('.self-area > .player-panel')).toHaveAttribute('data-player-id', viewer)
    expect(container.querySelector('.self-area > .player-panel')).toHaveClass('player-self')
    expect(container.querySelectorAll('.player-panel')).toHaveLength(count)
    for (const player of players) {
      const panel = container.querySelector(`[data-player-id="${player.player_id}"]`)!
      expect(panel).toHaveAttribute('data-character-id', player.character_id)
      expect(within(panel as HTMLElement).getByLabelText(`${player.hp} / ${player.max_hp} 体力`)).toBeInTheDocument()
    }
  }

  try {
    const view = render(<GamePage />)
    expectLayout(view.container, seatId)
    const originalPanels = new Map([...view.container.querySelectorAll<HTMLElement>('.player-panel')].map(panel => [panel.dataset.playerId, panel]))
    const originalSelfIndex = players.findIndex(player => player.player_id === seatId)
    for (const id of chosen) await userEvent.click(screen.getByRole('button', { name: `选择目标${byId.get(id)!.character_name}` }))
    await userEvent.click(screen.getByRole('button', { name: '确定' }))
    expect(submitDecision).toHaveBeenLastCalledWith(`tamo-table-${count}`, chosen)

    // The next server projection supplies the authoritative order, independent of the original room slots.
    players.splice(0, players.length, table[0], ...chosen.map(id => byId.get(id)!))
    request = null
    view.rerender(<GamePage />)
    expect(players.findIndex(player => player.player_id === seatId)).not.toBe(originalSelfIndex)
    expectLayout(view.container, seatId)
    for (const panel of view.container.querySelectorAll<HTMLElement>('.player-panel')) {
      expect(panel).toBe(originalPanels.get(panel.dataset.playerId))
    }
    expect(view.container.querySelector('.selected-target')).toBeNull()

    view.unmount()
    const restored = render(<GamePage />)
    expectLayout(restored.container, seatId)
    restored.unmount()
    seatId = 'p2'
    const otherClient = render(<GamePage />)
    expectLayout(otherClient.container, seatId)
    otherClient.unmount()
  } finally {
    players.splice(0, players.length, ...originalPlayers)
    seatId = originalSeatId
    request = null
  }
})

it('T20.3 HUD separates many hand cards from skill and equipment selection', async()=>{
 const equipment={...card,card_id:'cost-eq',name:'诸葛连弩',definition_id:'equipment.weapon.crossbow',equipment_slot:'weapon'}
 ;(players[0] as any).equipment=[equipment]
 extraCards=Array.from({length:24},(_,i)=>({...card,card_id:'many-'+i}))
 request={request_id:'equip-cost',player_id:'p1',request_type:'choose_cards',prompt:'【制衡】选择牌',choices:[],eligible_card_ids:['cost-eq','slash-1'],allowed_player_ids:[],min_count:1,max_count:2,remaining_ms:60000}
 try {
  const {container}=render(<GamePage/>)
  expect(container.querySelector('.skill-area .hand-card')).toBeNull()
  expect(container.querySelectorAll('.hand .hand-card')).toHaveLength(25)
  const equip=screen.getByRole('button',{name:'装备 诸葛连弩'})
  await userEvent.click(equip);expect(equip).toHaveAttribute('aria-pressed','true')
  await userEvent.click(equip);expect(equip).toHaveAttribute('aria-pressed','false')
  await userEvent.click(equip);await userEvent.click(screen.getAllByRole('button',{name:'杀 ♠7'})[0])
  await userEvent.click(screen.getByRole('button',{name:'确定'}))
  expect(submitDecision).toHaveBeenLastCalledWith('equip-cost',['cost-eq','slash-1'])
 } finally { players[0].equipment=[];extraCards=[] }
})
it('T20.3 separates physical chain use from zero-target recast', async()=>{
 extraCards=[{...card,card_id:'chain',name:'铁索连环',definition_id:'trick.iron_chain'}]
 request={request_id:'chain-play',player_id:'p1',request_type:'choose_option',prompt:'出牌',choices:['use:chain'],eligible_card_ids:[],allowed_player_ids:[],min_count:1,max_count:1,remaining_ms:60000,play_card_targets:{'use:chain':{targets:['p1','p2','p3'],min:0,max:2}}}
 render(<GamePage/>);await userEvent.click(screen.getByRole('button',{name:'铁索连环 ♠7'}))
 expect(screen.getByRole('button',{name:'使用'})).toBeDisabled()
 await userEvent.click(screen.getByRole('button',{name:'选择目标刘备'}))
 expect(screen.getByRole('button',{name:'使用'})).toBeEnabled()
 await userEvent.click(screen.getByRole('button',{name:'重铸'}))
 expect(submitDecision).toHaveBeenLastCalledWith('chain-play',{option:'use:chain',targets:[]})
})
