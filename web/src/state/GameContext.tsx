import { createContext, useCallback, useContext, useEffect, useMemo, useReducer, useRef, type ReactNode } from 'react'
import { GameConnection } from '../connection/GameConnection'
import type { ClientState, DraftState, GeneralInfo, LobbyState, PendingRequest, Projection, PublicEvent, SessionRecord } from '../types'

const SESSION_KEY = 'sanguosha.web.session.v1'

const initialState: ClientState = {
  page: 'home',
  connection: 'connecting',
  roomCode: '',
  playerName: '',
  seatId: '',
  reconnectToken: '',
  lobby: null,
  draft: null,
  projection: null,
  pendingRequest: null,
  publicEvents: [],
  generals: {},
  error: '',
  result: null,
  selectedGeneral: '',
}

type Action = { type: string; payload?: unknown }

function reducer(state: ClientState, action: Action): ClientState {
  switch (action.type) {
    case 'connection':
      return { ...state, connection: action.payload as ClientState['connection'] }
    case 'catalog':
      return { ...state, generals: action.payload as Record<string, GeneralInfo> }
    case 'room-created':
      return { ...state, roomCode: action.payload as string, error: '' }
    case 'welcome': {
      const payload = action.payload as Record<string, string>
      return {
        ...state,
        roomCode: payload.room_code ?? state.roomCode,
        seatId: payload.seat_id ?? state.seatId,
        reconnectToken: payload.reconnect_token ?? state.reconnectToken,
        error: '',
      }
    }
    case 'lobby': {
      const lobby = action.payload as LobbyState
      const page = lobby.phase === 'DRAFT'
        ? 'pregame'
        : lobby.phase === 'IN_GAME' || lobby.phase === 'FINISHED'
          ? state.page
          : 'lobby'
      return { ...state, lobby, page }
    }
    case 'draft':
      return { ...state, draft: action.payload as DraftState, page: 'pregame', selectedGeneral: '', error: '' }
    case 'projection':
      return { ...state, projection: action.payload as Projection, page: 'game', draft: null, error: '' }
    case 'pending':
      return { ...state, pendingRequest: action.payload as PendingRequest }
    case 'decision-result':
      return { ...state, pendingRequest: null, error: '' }
    case 'event':
      return { ...state, publicEvents: [...state.publicEvents.slice(-39), action.payload as PublicEvent] }
    case 'result':
      return { ...state, result: action.payload as string, page: 'game', pendingRequest: null }
    case 'select-general':
      return { ...state, selectedGeneral: action.payload as string }
    case 'error':
      return { ...state, error: action.payload as string }
    case 'set-name':
      return { ...state, playerName: action.payload as string }
    case 'home':
      return { ...initialState, connection: state.connection, generals: state.generals }
    default:
      return state
  }
}

interface GameActions {
  createRoom(name: string, singlePlayer?: boolean): void
  joinRoom(name: string, roomCode: string): void
  setReady(ready: boolean): void
  startGame(): void
  selectGeneral(id: string): void
  confirmGeneral(): void
  submitDecision(requestId: string, value: unknown): void
  clearError(): void
  returnHome(): void
}

const Context = createContext<{ state: ClientState; actions: GameActions; connection: GameConnection } | null>(null)

function friendlyError(message: string) {
  if (message.includes('room not found')) return '未找到该房间，请检查房间码。'
  if (message.includes('room is full')) return '房间已满。'
  if (message.includes('incompatible')) return '客户端版本与服务器不兼容，请刷新页面。'
  if (message.includes('invalid reconnect')) return '原对局已失效，请重新加入。'
  if (message.includes('already connected')) return '该座位已在其他页面连接。'
  if (message.includes('all guests must be ready')) return '所有来宾准备后才能开始。'
  return message || '发生未知错误。'
}

export function GameProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState)
  const connectionRef = useRef(new GameConnection())
  const reconnectAttempted = useRef(false)
  const playerNameRef = useRef('玩家')

  useEffect(() => {
    const connection = connectionRef.current
    const offStatus = connection.subscribeStatus((status) => dispatch({ type: 'connection', payload: status }))
    const offMessage = connection.subscribe((message) => {
      const kind = String(message.type ?? '')
      if (kind === 'WELCOME') {
        dispatch({ type: 'welcome', payload: message })
        if (message.seat_id && message.reconnect_token && message.room_code) {
          const record: SessionRecord = {
            roomCode: String(message.room_code),
            playerName: playerNameRef.current,
            seatId: String(message.seat_id),
            reconnectToken: String(message.reconnect_token),
          }
          localStorage.setItem(SESSION_KEY, JSON.stringify(record))
        } else if (!reconnectAttempted.current) {
          reconnectAttempted.current = true
          const saved = localStorage.getItem(SESSION_KEY)
          if (saved) {
            try {
              const session = JSON.parse(saved) as SessionRecord
              playerNameRef.current = session.playerName
              dispatch({ type: 'set-name', payload: session.playerName })
              connection.send('RECONNECT', {
                room_code: session.roomCode,
                name: session.playerName,
                token: session.reconnectToken,
              })
            } catch {
              localStorage.removeItem(SESSION_KEY)
            }
          }
        }
      } else if (kind === 'ROOM_CREATED') {
        dispatch({ type: 'room-created', payload: String(message.room_code) })
      } else if (kind === 'LOBBY_STATE') {
        dispatch({ type: 'lobby', payload: message as unknown as LobbyState })
      } else if (kind === 'DRAFT_REQUEST') {
        dispatch({ type: 'draft', payload: message as unknown as DraftState })
      } else if (kind === 'PROJECTION_UPDATE') {
        dispatch({ type: 'projection', payload: message.projection as Projection })
      } else if (kind === 'PENDING_REQUEST') {
        dispatch({ type: 'pending', payload: message.request as PendingRequest })
      } else if (kind === 'DECISION_RESULT') {
        dispatch({ type: 'decision-result' })
      } else if (kind === 'PUBLIC_EVENT') {
        dispatch({ type: 'event', payload: message.event as PublicEvent })
      } else if (kind === 'GAME_OVER') {
        dispatch({ type: 'result', payload: String(message.result ?? '') })
      } else if (kind === 'ERROR') {
        const friendly = friendlyError(String(message.message ?? ''))
        dispatch({ type: 'error', payload: friendly })
        if (friendly.includes('原对局已失效')) localStorage.removeItem(SESSION_KEY)
      }
    })

    connection.connect()
    fetch('/api/catalog/generals')
      .then((response) => {
        if (!response.ok) throw new Error('catalog unavailable')
        return response.json()
      })
      .then((items: GeneralInfo[]) => {
        dispatch({ type: 'catalog', payload: Object.fromEntries(items.map((item) => [item.id, item])) })
      })
      .catch(() => undefined)

    return () => {
      offStatus()
      offMessage()
      connection.disconnect()
    }
  }, [])

  const sendWhenConnected = useCallback((type: string, fields: Record<string, unknown>) => {
    if (!connectionRef.current.send(type, fields)) {
      dispatch({ type: 'error', payload: '正在连接服务器，请稍候。' })
    }
  }, [])

  const actions = useMemo<GameActions>(() => ({
    createRoom(name, singlePlayer = false) {
      const clean = name.trim() || '玩家'
      playerNameRef.current = clean
      dispatch({ type: 'set-name', payload: clean })
      localStorage.removeItem(SESSION_KEY)
      sendWhenConnected('CREATE_ROOM', { name: clean, single_player: singlePlayer })
    },
    joinRoom(name, roomCode) {
      const clean = name.trim() || '玩家'
      playerNameRef.current = clean
      dispatch({ type: 'set-name', payload: clean })
      localStorage.removeItem(SESSION_KEY)
      sendWhenConnected('JOIN_ROOM', { name: clean, room_code: roomCode.trim().toUpperCase() })
    },
    setReady(ready) {
      sendWhenConnected('READY', { ready })
    },
    startGame() {
      sendWhenConnected('START_GAME', {})
    },
    selectGeneral(id) {
      dispatch({ type: 'select-general', payload: id })
    },
    confirmGeneral() {
      if (!state.draft || !state.selectedGeneral) return
      sendWhenConnected('SUBMIT_DECISION', {
        decision: { request_id: state.draft.request.request_id, value: state.selectedGeneral },
      })
    },
    submitDecision(requestId, value) {
      sendWhenConnected('SUBMIT_DECISION', { decision: { request_id: requestId, value } })
    },
    clearError() {
      dispatch({ type: 'error', payload: '' })
    },
    returnHome() {
      connectionRef.current.send('LEAVE_ROOM')
      localStorage.removeItem(SESSION_KEY)
      reconnectAttempted.current = true
      dispatch({ type: 'home' })
    },
  }), [sendWhenConnected, state.draft, state.selectedGeneral])

  return <Context.Provider value={{ state, actions, connection: connectionRef.current }}>{children}</Context.Provider>
}

export function useGame() {
  const value = useContext(Context)
  if (!value) throw new Error('useGame must be used inside GameProvider')
  return value
}
