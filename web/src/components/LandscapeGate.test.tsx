import { render, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { LandscapeGate, tryLandscape } from './LandscapeGate'

it('keeps a CSS orientation prompt available without rebuilding game state',()=>{
 render(<LandscapeGate/>);expect(screen.getByText('请横屏游玩')).toBeInTheDocument()
})
it('absorbs fullscreen denial after a coarse-pointer start gesture',async()=>{
 const original=window.matchMedia
 window.matchMedia=vi.fn().mockReturnValue({matches:true})
 const start=vi.fn().mockRejectedValue(new Error('unsupported'))
 Object.defineProperty(document.documentElement,'requestFullscreen',{value:start,configurable:true})
 await expect(tryLandscape()).resolves.toBeUndefined()
 expect(start).toHaveBeenCalledTimes(1)
 window.matchMedia=original
})
