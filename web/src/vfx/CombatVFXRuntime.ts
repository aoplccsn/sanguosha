export type VfxQuality = 'high' | 'medium' | 'low'
export type BeamMode = 'attack' | 'normal' | 'protect'
type Point = { x: number; y: number }
type Effect = { kind: 'slash' | 'god-slash' | 'dodge' | 'impact'; from: Point; to: Point; start: number; duration: number; color: string; style?: string }

const QUALITY_KEY = 'sanguosha.vfx.quality.v1'
export function readVfxQuality(): VfxQuality {
  try {
    const saved = localStorage.getItem(QUALITY_KEY)
    return saved === 'high' || saved === 'low' ? saved : 'medium'
  } catch { return 'medium' }
}
export function saveVfxQuality(value: VfxQuality) {
  try { localStorage.setItem(QUALITY_KEY, value) } catch { /* storage can be disabled */ }
}

export class CombatVFXRuntime {
  private ctx: CanvasRenderingContext2D | null
  private board: HTMLElement
  private canvas: HTMLCanvasElement
  private observer: ResizeObserver | null = null
  private raf = 0
  private hidden = document.hidden
  private motionQuery = matchMedia('(prefers-reduced-motion: reduce)')
  private reduced = this.motionQuery.matches
  private reducedOverride: boolean | null = null
  private quality: VfxQuality
  private beamIds: string[] = []
  private beamMode: BeamMode = 'normal'
  private beamPoints: Point[] = []
  private source: Point = { x: 0, y: 0 }
  private effects: Effect[] = []
  private effectPool: Effect[] = []
  private width = 0
  private height = 0

  constructor(canvas: HTMLCanvasElement, board: HTMLElement, quality: VfxQuality) {
    this.canvas = canvas
    this.board = board
    this.ctx = canvas.getContext('2d', { alpha: true })
    this.quality = quality
    this.resize()
    if (typeof ResizeObserver !== 'undefined') {
      this.observer = new ResizeObserver(() => this.resize())
      this.observer.observe(board)
      board.querySelectorAll<HTMLElement>('[data-player-id]').forEach((node) => this.observer?.observe(node))
    }
    window.addEventListener('resize', this.resize)
    window.addEventListener('scroll', this.resize, { passive: true })
    document.addEventListener('visibilitychange', this.visibility)
    this.motionQuery.addEventListener?.('change', this.motionChanged)
  }

  private motionChanged = () => { this.reduced = this.reducedOverride ?? this.motionQuery.matches }

  setReducedMotion(value: boolean | null) { this.reducedOverride = value; this.reduced = value ?? this.motionQuery.matches }

  private visibility = () => {
    this.hidden = document.hidden
    if (this.hidden) { cancelAnimationFrame(this.raf); this.raf = 0; this.effects = []; this.ctx?.clearRect(0, 0, this.width, this.height) }
    else this.ensureFrame()
  }

  private anchor(id: string): Point | null {
    const panel = Array.from(this.board.querySelectorAll<HTMLElement>('[data-player-id]')).find((node) => node.dataset.playerId === id)
    if (!panel) return null
    const rect = (panel.querySelector('.portrait-button') ?? panel).getBoundingClientRect()
    const boardRect = this.board.getBoundingClientRect()
    return { x: rect.left + rect.width / 2 - boardRect.left, y: rect.top + rect.height / 2 - boardRect.top }
  }

  private resize = () => {
    const rect = this.board.getBoundingClientRect()
    this.width = rect.width
    this.height = rect.height
    const dpr = Math.min(devicePixelRatio || 1, this.quality === 'high' ? 2 : this.quality === 'medium' ? 1.5 : 1)
    const backingWidth = Math.round(rect.width * dpr)
    const backingHeight = Math.round(rect.height * dpr)
    if (this.canvas.width !== backingWidth) this.canvas.width = backingWidth
    if (this.canvas.height !== backingHeight) this.canvas.height = backingHeight
    if (this.ctx) {
      this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      this.ctx.imageSmoothingEnabled = true
      this.ctx.imageSmoothingQuality = 'high'
    }
    this.refreshBeam()
  }

  private refreshBeam() {
    const self = this.board.querySelector<HTMLElement>('.player-self')?.dataset.playerId
    this.source = self ? this.anchor(self) ?? { x: this.width / 2, y: this.height * .85 } : { x: this.width / 2, y: this.height * .85 }
    this.beamPoints = this.beamIds.map((id) => this.anchor(id)).filter((point): point is Point => !!point)
    this.ensureFrame()
  }

  setBeam(ids: string[], mode: BeamMode) {
    this.beamIds = ids
    this.beamMode = mode
    this.refreshBeam()
  }

  setQuality(value: VfxQuality) { this.quality = value; this.resize() }

  trigger(kind: Effect['kind'], sourceId: string, targetId: string, color = '#f2b858', style?: string) {
    if (this.hidden || !this.ctx) return
    const to = this.anchor(targetId)
    if (!to) return
    const from = this.anchor(sourceId) ?? to
    if (this.effects.length >= 16) {
      const recycled = this.effects.shift()
      if (recycled) this.effectPool.push(recycled)
    }
    const duration = this.reduced ? 120 : kind === 'god-slash' ? 440 : kind === 'slash' ? 340 : kind === 'dodge' ? 260 : 300
    const effect = this.effectPool.pop() ?? { kind, from, to, color, start: 0, duration }
    Object.assign(effect, { kind, from, to, color, style, start: performance.now(), duration })
    this.effects.push(effect)
    this.ensureFrame()
  }

  clearEffects() {
    this.effectPool.push(...this.effects)
    this.effects.length = 0
    if (!this.beamPoints.length) { cancelAnimationFrame(this.raf); this.raf = 0; this.ctx?.clearRect(0, 0, this.width, this.height) }
  }

  private ensureFrame() {
    if (!this.raf && !this.hidden && this.ctx && (this.effects.length || this.beamPoints.length)) this.raf = requestAnimationFrame(this.frame)
  }

  private frame = (now: number) => {
    this.raf = 0
    const ctx = this.ctx
    if (!ctx || this.hidden) return
    ctx.clearRect(0, 0, this.width, this.height)
    const beamColor = this.beamMode === 'attack' ? '#f0804b' : this.beamMode === 'protect' ? '#78dfe4' : '#e8bb69'
    for (const to of this.beamPoints) {
      const dx = to.x - this.source.x, dy = to.y - this.source.y
      const length = Math.hypot(dx, dy) || 1
      const endX = to.x - dx / length * 20, endY = to.y - dy / length * 20
      ctx.lineCap = 'round'
      ctx.strokeStyle = beamColor
      ctx.globalAlpha = .14
      ctx.lineWidth = this.quality === 'low' ? 6 : 11
      ctx.beginPath(); ctx.moveTo(this.source.x, this.source.y); ctx.lineTo(endX, endY); ctx.stroke()
      ctx.globalAlpha = .78
      ctx.lineWidth = 2
      ctx.beginPath(); ctx.moveTo(this.source.x, this.source.y); ctx.lineTo(endX, endY); ctx.stroke()
      if (!this.reduced && this.quality !== 'low') {
        const t = ((now * .0012) % 1)
        ctx.globalAlpha = .85
        ctx.fillStyle = beamColor
        ctx.beginPath(); ctx.arc(this.source.x + dx * t, this.source.y + dy * t, 3.5, 0, Math.PI * 2); ctx.fill()
      }
    }
    for (let index = this.effects.length - 1; index >= 0; index--) {
      if (now - this.effects[index].start >= this.effects[index].duration) {
        this.effectPool.push(this.effects[index])
        this.effects.splice(index, 1)
      }
    }
    for (const effect of this.effects) this.drawEffect(ctx, effect, (now - effect.start) / effect.duration)
    ctx.globalAlpha = 1
    if (this.beamPoints.length || this.effects.length) this.ensureFrame()
  }

  private drawEffect(ctx: CanvasRenderingContext2D, effect: Effect, progress: number) {
    const { from, to, color, kind } = effect
    const fade = 1 - progress
    ctx.strokeStyle = color
    ctx.fillStyle = color
    ctx.lineCap = 'round'
    if (kind === 'slash' || kind === 'god-slash') {
      const eased = 1 - Math.pow(1 - Math.min(progress * 1.7, 1), 3)
      const x = from.x + (to.x - from.x) * eased
      const y = from.y + (to.y - from.y) * eased
      ctx.globalAlpha = .2 * fade; ctx.lineWidth = this.quality === 'low' ? 10 : kind === 'god-slash' ? 28 : 22
      ctx.beginPath(); ctx.moveTo(from.x, from.y); ctx.lineTo(x, y); ctx.stroke()
      ctx.globalAlpha = .95 * fade; ctx.lineWidth = 3
      ctx.beginPath(); ctx.moveTo(from.x, from.y); ctx.lineTo(x, y); ctx.stroke()
      if (progress > .35) {
        const radius = (progress - .35) * 75
        ctx.globalAlpha = Math.max(0, 1 - progress) * .8; ctx.lineWidth = 4
        ctx.beginPath(); ctx.arc(to.x, to.y, radius, -.85, 1.75); ctx.stroke()
      }
      if (kind === 'god-slash' && progress > .25 && this.quality !== 'low') this.drawGodAccent(ctx, effect, progress)
    } else {
      const radius = kind === 'dodge' ? 14 + progress * 55 : 8 + progress * 65
      ctx.globalAlpha = fade * (kind === 'dodge' ? .75 : .9)
      ctx.lineWidth = kind === 'dodge' ? 3 : 5
      ctx.beginPath(); ctx.ellipse(to.x, to.y, radius, radius * .55, -.45, 0, Math.PI * 2); ctx.stroke()
      if (kind === 'dodge' && this.quality !== 'low') {
        ctx.globalAlpha = fade * .32
        for (let i = 1; i <= 2; i++) { ctx.beginPath(); ctx.ellipse(to.x + i * 12, to.y - i * 7, radius, radius * .55, -.45, 0, Math.PI * 2); ctx.stroke() }
      }
    }
  }

  private drawGodAccent(ctx: CanvasRenderingContext2D, effect: Effect, progress: number) {
    const { to, style, color } = effect
    const radius = 18 + progress * 45
    ctx.strokeStyle = color
    ctx.globalAlpha = (1 - progress) * .8
    ctx.lineWidth = 2.5
    ctx.beginPath()
    if (style === 'wind_god_guanyu') {
      ctx.arc(to.x, to.y, radius, -2.5, .5)
    } else if (style === 'wind_god_lvmeng') {
      ctx.ellipse(to.x, to.y, radius * 1.15, radius * .4, -.3, 0, Math.PI * 2)
    } else if (style === 'fire_god_zhouyu') {
      ctx.arc(to.x, to.y, radius, 2.8, 5.9)
      ctx.moveTo(to.x - radius, to.y + radius * .3); ctx.lineTo(to.x + radius, to.y - radius * .3)
    } else if (style === 'fire_god_zhugeliang') {
      for (let i = 0; i < 8; i++) {
        const a = Math.PI * i / 4
        ctx.moveTo(to.x + Math.cos(a) * radius * .55, to.y + Math.sin(a) * radius * .55)
        ctx.lineTo(to.x + Math.cos(a) * radius, to.y + Math.sin(a) * radius)
      }
    } else if (style === 'forest_god_caocao') {
      for (let i = -1; i <= 1; i++) {
        ctx.moveTo(to.x + i * 9 - radius * .25, to.y - radius)
        ctx.lineTo(to.x + i * 9 + radius * .25, to.y + radius)
      }
    } else if (style === 'forest_god_lvbu') {
      ctx.moveTo(to.x - radius, to.y - radius)
      ctx.lineTo(to.x - radius * .3, to.y + radius * .2)
      ctx.lineTo(to.x + radius * .1, to.y - radius * .4)
      ctx.lineTo(to.x + radius, to.y + radius)
      ctx.moveTo(to.x - radius * .65, to.y + radius)
      ctx.lineTo(to.x + radius * .7, to.y - radius)
    } else if (style === 'mountain_god_zhaoyun') {
      ctx.moveTo(to.x - radius * 1.7, to.y + radius * .5)
      ctx.lineTo(to.x + radius * 1.7, to.y - radius * .5)
      ctx.moveTo(to.x + radius * .6, to.y - radius * .8)
      ctx.lineTo(to.x + radius * 1.7, to.y - radius * .5)
      ctx.lineTo(to.x + radius * .8, to.y + radius * .1)
    } else if (style === 'mountain_god_simayi') {
      ctx.ellipse(to.x, to.y, radius * .35, radius * 1.25, .35, 0, Math.PI * 2)
      ctx.moveTo(to.x + radius * .3, to.y - radius)
      ctx.lineTo(to.x - radius * .25, to.y)
      ctx.lineTo(to.x + radius * .2, to.y + radius)
    }
    ctx.stroke()
  }

  destroy() {
    cancelAnimationFrame(this.raf)
    this.raf = 0
    this.effects = []
    this.effectPool = []
    this.observer?.disconnect()
    window.removeEventListener('resize', this.resize)
    window.removeEventListener('scroll', this.resize)
    document.removeEventListener('visibilitychange', this.visibility)
    this.motionQuery.removeEventListener?.('change', this.motionChanged)
    this.ctx?.clearRect(0, 0, this.width, this.height)
  }
}
