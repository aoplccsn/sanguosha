import {render,screen} from '@testing-library/react'
import {it,expect} from 'vitest'
import {SuitText} from './SuitText'
import {battlePrompt} from '../labels'
import type {PendingRequest} from '../types'
it('uses one ink family for each pair of suits',()=>{
 render(<><SuitText suit="♥"/><SuitText suit="♦"/><SuitText suit="♠"/><SuitText suit="♣"/></>)
 expect(screen.getByText('♥')).toHaveClass('suit-red');expect(screen.getByText('♦')).toHaveClass('suit-red')
 expect(screen.getByText('♠')).toHaveClass('suit-black');expect(screen.getByText('♣')).toHaveClass('suit-black')
})
it('shows precise Chinese responses and masks request enums',()=>{
 const r={prompt:'Respond with a card or pass',request_type:'respond_with_card',required_definition_id:'basic.slash'} as PendingRequest
 expect(battlePrompt(r,{'basic.slash':'杀','trick.savage_assault':'南蛮入侵'},{},'trick.savage_assault')).toBe('请打出一张【杀】响应【南蛮入侵】')
 expect(battlePrompt({...r,request_type:'choose_players',required_definition_id:null,prompt:'choose target request_type',min_count:1,max_count:2},{},{})).toBe('请选择 1～2 名目标角色')
 expect(battlePrompt({...r,request_type:'choose_option',required_definition_id:null,prompt:'神司马懿【极略】：请选择 skill_id jilue'},{},{jilue:'极略'})).not.toMatch(/skill_id|jilue/)
})
