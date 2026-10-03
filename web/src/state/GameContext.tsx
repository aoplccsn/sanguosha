import { createContext, useCallback, useContext, useEffect, useMemo, useReducer, useRef, type ReactNode } from 'react'
import { GameConnection } from '../connection/GameConnection'
import type { ClientState, DraftState, GeneralInfo, LobbyState, PendingRequest, Projection, PublicEvent, ServerVersion, SessionRecord } from '../types'

const SESSION_KEY = 'sanguosha.web.session.v1'

const initialState: ClientState = {
  page: 'home',
  connection: 'idle',
  roomCode: '',
  playerName: '',
  seatId: '',
  reconnectToken: '',
  lobby: null,
  draft: null,
  projection: null,
  pendingRequest: null,
  requestEpoch: 0,
  decisionProcessing: null,
  notice: '',
  resumeSession: null,
  publicEvents: [],
  generals: {},
  error: '',
  result: null,
  selectedGeneral: '',
  serverVersion: null,
  updateAvailable: false,
}

type Action = { type: string; payload?: unknown }

function reducer(state: ClientState, action: Action): ClientState {
  switch (action.type) {
    case 'connection':
      return { ...state, connection: action.payload as ClientState['connection'],
        pendingRequest: action.payload === 'reconnecting' || action.payload === 'offline' ? null : state.pendingRequest,
        requestEpoch: action.payload === 'reconnecting' || action.payload === 'offline' ? state.requestEpoch + 1 : state.requestEpoch,
        decisionProcessing: action.payload === 'reconnecting' || action.payload === 'offline' ? null : state.decisionProcessing,
        notice: action.payload === 'connected' && state.connection === 'reconnecting' ? '连接已恢复' : state.notice }
    case 'catalog':
      return { ...state, generals: action.payload as Record<string, GeneralInfo> }
    case 'server-version': {
      const version = action.payload as ServerVersion
      const local = __APP_VERSION__.split('.').map(Number)
      const remote = version.app_version.split('.').map(Number)
      const updateAvailable = remote.some((part, index) => part > (local[index] ?? 0)
        && remote.slice(0, index).every((earlier, earlierIndex) => earlier === (local[earlierIndex] ?? 0)))
      return { ...state, serverVersion: version, updateAvailable }
    }
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
      return { ...state, draft: action.payload as DraftState, page: 'pregame', selectedGeneral: '', decisionProcessing: null, error: '' }
    case 'projection': {
      const { projection, activeRequestId } = action.payload as { projection: Projection; activeRequestId: string | null }
      const keepsRequest = !!activeRequestId && state.pendingRequest?.request_id === activeRequestId
      return { ...state, projection, page: 'game', draft: null, error: '',
        pendingRequest: keepsRequest ? state.pendingRequest : null,
        requestEpoch: keepsRequest || !state.pendingRequest ? state.requestEpoch : state.requestEpoch + 1 }
    }
    case 'pending':
      return { ...state, pendingRequest: action.payload as PendingRequest, decisionProcessing: null,
        requestEpoch: state.pendingRequest?.request_id === (action.payload as PendingRequest).request_id ? state.requestEpoch : state.requestEpoch + 1,
        notice: state.pendingRequest?.request_id !== (action.payload as PendingRequest).request_id ? '当前响应已更新' : state.notice }
    case 'decision-result':
      return state.decisionProcessing === action.payload
        ? { ...state, pendingRequest: state.pendingRequest?.request_id === action.payload ? null : state.pendingRequest,
            decisionProcessing: null, notice: '操作已提交', error: '' } : state
    case 'decision-begin':
      return { ...state, decisionProcessing: action.payload as string, notice: '处理中…', error: '' }
    case 'decision-rejected':
      return { ...state, decisionProcessing: null, notice: action.payload as string }
    case 'notice':
      return { ...state, notice: action.payload as string }
    case 'resume-session':
      return { ...state, resumeSession: action.payload as SessionRecord | null }
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
      return { ...initialState, connection: 'idle', generals: state.generals }
    case 'server-restarted':
      return { ...initialState, connection: 'fatal', generals: state.generals,
        error: '服务器已重新启动，本局已结束。请返回首页创建新房间。' }
    default:
      return state
  }
}

interface GameActions {
  createRoom(name: string, singlePlayer?: boolean, modeId?: string, allowGods?: boolean): void
  joinRoom(name: string, roomCode: string): void
  setReady(ready: boolean): void
  startGame(): void
  configureRoom(modeId: string, allowGods: boolean): void
  kickPlayer(seatId: string): void
  selectGeneral(id: string): void
  confirmGeneral(): void
  submitDecision(requestId: string, value: unknown): void
  continueSession(): void
  discardSession(): void
  notify(message: string): void
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
  if (/stale|expired|duplicate/i.test(message)) return '当前响应已更新，请重新选择。'
  if (message.includes('all guests must be ready')) return '所有来宾准备后才能开始。'
  return message || '发生未知错误。'
}

export function GameProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState)
  const connectionRef = useRef(new GameConnection())
  const recovering = useRef(false)
  const playerNameRef = useRef('玩家')
  const activeRequestRef = useRef<string | null>(null)
  const submittingRef = useRef<string | null>(null)

  useEffect(() => {
    if (!state.notice || state.notice === '处理中…') return
    const timer = window.setTimeout(() => dispatch({ type: 'notice', payload: '' }), 2800)
    return () => window.clearTimeout(timer)
  }, [state.notice])

  useEffect(() => {
    const connection = connectionRef.current
    const offStatus = connection.subscribeStatus((status) => {
      dispatch({ type: 'connection', payload: status })
      if (status === 'reconnecting' || status === 'offline') {
        activeRequestRef.current = null
        submittingRef.current = null
      }
    })
    const offMessage = connection.subscribe((message) => {
      const kind = String(message.type ?? '')
      if (kind === 'WELCOME') {
        dispatch({ type: 'welcome', payload: message })
        if (message.app_version && message.build_commit && message.protocol_version) {
          dispatch({ type: 'server-version', payload: {
            app_version: String(message.app_version),
            build_commit: String(message.build_commit),
            protocol_version: Number(message.protocol_version),
          } })
        }
        if (message.seat_id && message.reconnect_token && message.room_code) {
          recovering.current = false
          const record: SessionRecord = {
            roomCode: String(message.room_code),
            playerName: playerNameRef.current,
            seatId: String(message.seat_id),
            reconnectToken: String(message.reconnect_token),
          }
          localStorage.setItem(SESSION_KEY, JSON.stringify(record))
          dispatch({ type: 'resume-session', payload: null })
        } else if (!__CLOUDFLARE_ROOMS__ && recovering.current) {
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
              recovering.current = true
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
        activeRequestRef.current = (message as unknown as DraftState).request.request_id
        dispatch({ type: 'draft', payload: message as unknown as DraftState })
      } else if (kind === 'PROJECTION_UPDATE') {
        const activeRequestId = String(message.active_request_id ?? '') || null
        activeRequestRef.current = activeRequestId
        dispatch({ type: 'projection', payload: { projection: message.projection as Projection, activeRequestId } })
      } else if (kind === 'PENDING_REQUEST') {
        const next = message.request as PendingRequest
        if (import.meta.env.DEV) console.debug('[game] request replaced', next.request_id)
        activeRequestRef.current = next.request_id
        submittingRef.current = null
        dispatch({ type: 'pending', payload: next })
      } else if (kind === 'DECISION_RESULT') {
        const requestId = String(message.request_id ?? '')
        if (submittingRef.current === requestId) submittingRef.current = null
        if (activeRequestRef.current === requestId) activeRequestRef.current = null
        if (import.meta.env.DEV) console.debug('[game] submit success', requestId)
        dispatch({ type: 'decision-result', payload: requestId })
      } else if (kind === 'PUBLIC_EVENT') {
        dispatch({ type: 'event', payload: message.event as PublicEvent })
      } else if (kind === 'GAME_OVER') {
        dispatch({ type: 'result', payload: String(message.result ?? '') })
      } else if (kind === 'KICKED') {
        connection.send('LEAVE_ROOM')
        connection.disconnect()
        localStorage.removeItem(SESSION_KEY)
        dispatch({ type: 'home' })
        dispatch({ type: 'error', payload: String(message.reason ?? '已离开房间') })
      } else if (kind === 'ERROR') {
        const rejectedRequest = String(message.request_id ?? '')
        if (rejectedRequest && (submittingRef.current ?? activeRequestRef.current)
            && rejectedRequest !== (submittingRef.current ?? activeRequestRef.current)) {
          dispatch({ type: 'notice', payload: '此前的响应已更新' })
          return
        }
        const wasSubmitting = submittingRef.current !== null
        submittingRef.current = null
        if (recovering.current && /room not found|invalid reconnect/i.test(String(message.message ?? ''))) {
          localStorage.removeItem(SESSION_KEY)
          recovering.current = false
          dispatch({ type: 'server-restarted' })
          return
        }
        const friendly = friendlyError(String(message.message ?? ''))
        if (import.meta.env.DEV) console.debug('[game] submit rejected', friendly)
        dispatch({ type: 'decision-rejected', payload: /stale|expired|duplicate/i.test(String(message.message ?? '')) ? '当前响应已更新' : friendly })
        if (!wasSubmitting) dispatch({ type: 'error', payload: friendly })
        if (friendly.includes('原对局已失效')) localStorage.removeItem(SESSION_KEY)
      }
    })

    const savedSession = localStorage.getItem(SESSION_KEY)
    if (savedSession) {
      try {
        const session = JSON.parse(savedSession) as SessionRecord
        playerNameRef.current = session.playerName
        dispatch({ type: 'set-name', payload: session.playerName })
        dispatch({ type: 'resume-session', payload: session })
      } catch {
        localStorage.removeItem(SESSION_KEY)
      }
    }
    if (!__CLOUDFLARE_ROOMS__) {
      connection.connect()
    }
    fetch('/api/catalog/generals')
      .then((response) => {
        if (!response.ok) throw new Error('catalog unavailable')
        return response.json()
      })
      .then((items: GeneralInfo[]) => {
        dispatch({ type: 'catalog', payload: Object.fromEntries(items.map((item) => [item.id, item])) })
      })
      .catch(() => undefined)
    fetch('/api/version')
      .then((response) => {
        if (!response.ok) throw new Error('version unavailable')
        return response.json()
      })
      .then((version: ServerVersion) => dispatch({ type: 'server-version', payload: version }))
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
    createRoom(name, singlePlayer = false, modeId = 'military-five', allowGods = false) {
      const clean = name.trim() || '玩家'
      playerNameRef.current = clean
      dispatch({ type: 'set-name', payload: clean })
      localStorage.removeItem(SESSION_KEY)
      dispatch({ type: 'resume-session', payload: null })
      const seedParameter = new URLSearchParams(window.location.search).get('seed')
      const requestedSeed = seedParameter === null ? NaN : Number(seedParameter)
      const fields = {
        name: clean,
        single_player: singlePlayer,
        mode_id: modeId,
        allow_gods: allowGods,
        review_god_lvbu: new URLSearchParams(window.location.search).get('t11_lvbu') === '1',
        ...(Number.isInteger(requestedSeed) && requestedSeed >= 0 ? { seed: requestedSeed } : {}),
      }
      if (__CLOUDFLARE_ROOMS__) {
        fetch('/api/rooms', { method: 'POST' })
          .then((response) => {
            if (!response.ok) throw new Error('room creation failed')
            return response.json() as Promise<{ room_code: string }>
          })
          .then(({ room_code }) => {
            dispatch({ type: 'room-created', payload: room_code })
            connectionRef.current.openRoom(room_code, 'JOIN_ROOM', {
              ...fields, room_code, created: true,
            })
          })
          .catch(() => dispatch({ type: 'error', payload: '无法创建房间，请稍后重试。' }))
      } else {
        sendWhenConnected('CREATE_ROOM', fields)
      }
    },
    joinRoom(name, roomCode) {
      const clean = name.trim() || '玩家'
      playerNameRef.current = clean
      dispatch({ type: 'set-name', payload: clean })
      localStorage.removeItem(SESSION_KEY)
      dispatch({ type: 'resume-session', payload: null })
      const normalized = roomCode.trim().toUpperCase()
      if (__CLOUDFLARE_ROOMS__) {
        connectionRef.current.openRoom(normalized, 'JOIN_ROOM', { name: clean, room_code: normalized })
      } else {
        sendWhenConnected('JOIN_ROOM', { name: clean, room_code: normalized })
      }
    },
    setReady(ready) {
      sendWhenConnected('READY', { ready })
    },
    startGame() {
      sendWhenConnected('START_GAME', {})
    },
    configureRoom(modeId, allowGods) {
      sendWhenConnected('CONFIGURE_ROOM', { mode_id: modeId, allow_gods: allowGods })
    },
    kickPlayer(seatId) {
      sendWhenConnected('KICK_PLAYER', { seat_id: seatId })
    },
    selectGeneral(id) {
      dispatch({ type: 'select-general', payload: id })
    },
    confirmGeneral() {
      if (!state.draft || !state.selectedGeneral) return
      const requestId = state.draft.request.request_id
      if (activeRequestRef.current !== requestId || submittingRef.current === requestId) return
      submittingRef.current = requestId
      dispatch({ type: 'decision-begin', payload: requestId })
      if (!connectionRef.current.send('SUBMIT_DECISION', {
        decision: { request_id: requestId, value: state.selectedGeneral },
      })) { submittingRef.current = null; dispatch({ type: 'decision-rejected', payload: '连接恢复中，请稍候重试' }) }
    },
    submitDecision(requestId, value) {
      if (activeRequestRef.current !== requestId || submittingRef.current === requestId) {
        dispatch({ type: 'notice', payload: activeRequestRef.current !== requestId ? '当前响应已更新' : '正在处理，请稍候' })
        return
      }
      submittingRef.current = requestId
      if (import.meta.env.DEV) console.debug('[game] submit begin', requestId)
      dispatch({ type: 'decision-begin', payload: requestId })
      if (!connectionRef.current.send('SUBMIT_DECISION', { decision: { request_id: requestId, value } })) {
        submittingRef.current = null
        dispatch({ type: 'decision-rejected', payload: '连接恢复中，请稍候重试' })
      }
    },
    continueSession() {
      const saved = localStorage.getItem(SESSION_KEY)
      if (!saved) { dispatch({ type: 'resume-session', payload: null }); return }
      try {
        const session = JSON.parse(saved) as SessionRecord
        playerNameRef.current = session.playerName
        recovering.current = true
        dispatch({ type: 'resume-session', payload: null })
        if (__CLOUDFLARE_ROOMS__) connectionRef.current.openRoom(session.roomCode, 'RECONNECT', {
          room_code: session.roomCode, name: session.playerName, token: session.reconnectToken,
        })
        else connectionRef.current.connect()
      } catch { localStorage.removeItem(SESSION_KEY); dispatch({ type: 'resume-session', payload: null }) }
    },
    discardSession() {
      localStorage.removeItem(SESSION_KEY)
      dispatch({ type: 'resume-session', payload: null })
    },
    notify(message) {
      dispatch({ type: 'notice', payload: message })
    },
    clearError() {
      dispatch({ type: 'error', payload: '' })
    },
    returnHome() {
      connectionRef.current.send('LEAVE_ROOM')
      connectionRef.current.disconnect()
      localStorage.removeItem(SESSION_KEY)
      activeRequestRef.current = null
      submittingRef.current = null
      recovering.current = false
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
