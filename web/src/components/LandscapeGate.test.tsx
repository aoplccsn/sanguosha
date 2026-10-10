import { expect, it, vi } from 'vitest'
import { tryLandscape } from './LandscapeGate'

it('absorbs fullscreen and orientation-lock rejection after a coarse-pointer gesture',async()=>{
 const original=window.matchMedia
 window.matchMedia=vi.fn().mockReturnValue({matches:true})
 const start=vi.fn().mockRejectedValue(new Error('unsupported'))
 const lock=vi.fn().mockRejectedValue(new Error('NotSupportedError'))
 Object.defineProperty(document.documentElement,'requestFullscreen',{value:start,configurable:true})
 Object.defineProperty(screen,'orientation',{value:{lock},configurable:true})
 await expect(tryLandscape()).resolves.toBeUndefined()
 expect(start).toHaveBeenCalledTimes(1)
 expect(lock).toHaveBeenCalledWith('landscape')
 window.matchMedia=original
})
