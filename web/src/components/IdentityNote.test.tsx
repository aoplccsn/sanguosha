import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it } from 'vitest'
import { IdentityNote } from './IdentityNote'
import type { PlayerView } from '../types'

const player={player_id:'p2',name:'玩家2',identity_label:'未知',alive:true} as PlayerView
beforeEach(()=>localStorage.clear())
it('persists private room/local/target notes and hides revealed identities',async()=>{
 const view=render(<IdentityNote roomId="room1" localId="p1" player={player}/>)
 await userEvent.click(screen.getByRole('button',{name:'我的身份猜测：玩家2'}))
 await userEvent.click(screen.getByRole('button',{name:'反贼'}))
 expect(localStorage.getItem('sanguosha.identity-note.v1:room1:p1:p2')).toBe('反')
 view.unmount()
 const next=render(<IdentityNote roomId="room1" localId="p1" player={player}/>)
 expect(screen.getByText('反？')).toBeInTheDocument()
 next.rerender(<IdentityNote roomId="room1" localId="p1" player={{...player,alive:false,identity_label:'忠臣'}}/>)
 expect(screen.queryByText('反？')).not.toBeInTheDocument()
})
it('excludes lord, self and public teams',()=>{
 const {rerender}=render(<IdentityNote roomId="r" localId="p2" player={player}/>)
 expect(screen.queryByRole('button')).toBeNull()
 rerender(<IdentityNote roomId="r" localId="p1" player={{...player,identity_label:'主公'}}/>)
 expect(screen.queryByRole('button')).toBeNull()
})
