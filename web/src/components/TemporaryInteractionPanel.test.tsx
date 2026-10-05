import { render, screen, fireEvent } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { TemporaryInteractionPanel } from './TemporaryInteractionPanel'
import type { Projection, PendingRequest } from '../types'
const card={card_id:'public',definition_id:'basic.slash',name:'杀',suit:'♠',rank:'A',category:'basic',equipment_slot:'',details:''}
const projection={players:[{player_id:'p1',name:'你',character_name:'赵云',active:true},{player_id:'p2',name:'目标',character_name:'曹丕',equipment:[card],judgments:[]}],shared_cards:[],combat:{definition_id:'trick.snatch'}} as unknown as Projection
const request={request_id:'r',player_id:'p1',request_type:'choose_card',subject_player_id:'p2',eligible_card_ids:['hidden-hand:1','public'],remaining_ms:10000,allow_pass:false} as PendingRequest
it('shows only a back for hidden choices and requires confirmation without fake cancel',()=>{
 const select=vi.fn(),confirm=vi.fn();const view=render(<TemporaryInteractionPanel projection={projection} request={request} seatId="p1" connected processing={false} selected={[]} canConfirm={false} onSelect={select} onConfirm={confirm} onPass={vi.fn()} />)
 const back=screen.getByRole('button',{name:'暗置手牌 1'});expect(back.querySelector('img')).toHaveAttribute('alt','牌背')
 expect(screen.queryByRole('button',{name:'取消'})).toBeNull();expect(screen.getByRole('button',{name:'确认'})).toBeDisabled()
 fireEvent.click(back);expect(select).toHaveBeenCalledWith('hidden-hand:1');expect(confirm).not.toHaveBeenCalled()
 view.rerender(<TemporaryInteractionPanel projection={projection} request={request} seatId="p1" connected processing={false} selected={['hidden-hand:1']} canConfirm onSelect={select} onConfirm={confirm} onPass={vi.fn()} />)
 fireEvent.click(screen.getByRole('button',{name:'确认'}));expect(confirm).toHaveBeenCalledOnce()
})
it('public harvest remains visible to observers while selection is restricted',()=>{
 const select=vi.fn();render(<TemporaryInteractionPanel projection={{...projection,shared_cards:[card],waiting:{key:'r',player_id:'p1',remaining_ms:9000,responding:true,thinking:false}}} request={null} seatId="p2" connected processing={false} selected={[]} canConfirm={false} onSelect={select} onConfirm={vi.fn()} onPass={vi.fn()} />)
 fireEvent.click(screen.getByRole('button',{name:'杀 ♠A'}));expect(select).not.toHaveBeenCalled();expect(screen.queryByRole('button',{name:'确认'})).toBeNull()
 expect(screen.getByRole('dialog',{name:'五谷丰登'})).toBeVisible()
})
