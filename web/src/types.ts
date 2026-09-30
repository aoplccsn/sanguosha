export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'reconnecting'
export type Page = 'home' | 'lobby' | 'pregame' | 'game'

export interface Seat {
  seat_id: string
  player_name: string
  controller_type: 'EMPTY' | 'HUMAN' | 'AI'
  ready: boolean
  connected: boolean
}

export interface LobbyState {
  phase: 'OPEN' | 'READY' | 'DRAFT' | 'IN_GAME' | 'FINISHED'
  host_id: string | null
  seats: Seat[]
}

export interface SkillInfo {
  id: string
  name: string
  description: string
  type: string
}

export interface GeneralInfo {
  id: string
  name: string
  kingdom: string
  max_hp: number
  gender: string
  portrait: string
  skills: SkillInfo[]
}

export interface PendingRequest {
  request_id: string
  player_id: string
  request_type: string
  prompt: string
  choices: string[]
  allowed_player_ids: string[]
  required_definition_id: string | null
  eligible_card_ids: string[]
  allow_pass: boolean
  min_count: number
  max_count: number
  subject_player_id: string | null
  remaining_ms: number
}

export interface DraftState {
  request: PendingRequest
  identity: string
  lord_id: string
}

export interface CardView {
  card_id: string
  name: string
  suit: string
  rank: string
  definition_id: string
  category: string
  equipment_slot: string
  details: string
}

export interface PlayerView {
  player_id: string
  name: string
  character_name: string
  identity_label: string
  hp: number
  max_hp: number
  hand_count: number
  alive: boolean
  active: boolean
  character_id: string
  faction: string
  chained: boolean
  equipment: CardView[]
  judgments: CardView[]
  base_distance: number | null
  effective_distance: number | null
  attack_range: number
  skill_labels: string[]
  face_up?: boolean
  marks?: Record<string, number>
}

export interface PortraitState {
  currentTurn: boolean
  selectableTarget: boolean
  selectedTarget: boolean
  waitingResponse: boolean
  damaged: boolean
  healing: boolean
  dying: boolean
  dead: boolean
  chained: boolean
  faceDown: boolean
  judgment: boolean
  skillName?: string
}

export interface Projection {
  players: PlayerView[]
  hand: CardView[]
  current_phase: string
  turn_number: number
  deck_count: number
  discard_count: number
  result: string | null
  discard_top: CardView | null
  shared_cards: CardView[]
}

export interface PublicEvent {
  kind: string
  [key: string]: unknown
}

export interface SessionRecord {
  roomCode: string
  playerName: string
  seatId: string
  reconnectToken: string
}

export interface ServerVersion {
  app_version: string
  build_commit: string
  protocol_version: number
}

export interface ClientState {
  page: Page
  connection: ConnectionStatus
  roomCode: string
  playerName: string
  seatId: string
  reconnectToken: string
  lobby: LobbyState | null
  draft: DraftState | null
  projection: Projection | null
  pendingRequest: PendingRequest | null
  publicEvents: PublicEvent[]
  generals: Record<string, GeneralInfo>
  error: string
  result: string | null
  selectedGeneral: string
  serverVersion: ServerVersion | null
  updateAvailable: boolean
}
