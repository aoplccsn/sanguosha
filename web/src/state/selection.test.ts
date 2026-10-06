import {describe,it,expect} from 'vitest'
import {effectiveSelection,emptySelection,materials} from './selection'
import type {PendingRequest} from '../types'
const ids=new Set(['a','b','normal'])
describe('authoritative ViewAs lifecycle',()=>{
 for (const skill of ['qixi','wusheng','longdan','serpent_spear','longnu','fuhun','longhun','luanji','huoji','kanpo']) {
  it(skill+' cancels, deselects and recovers normal legality',()=>{
   const option='virtual:'+skill+':a'
   const request={request_id:'r',choices:[option,'use:normal'],eligible_card_ids:[],allowed_player_ids:[],request_type:'choose_option'} as unknown as PendingRequest
   const active={...emptySelection('r'),mode:skill,cards:['a'],option}
   expect(effectiveSelection(active,'r',request,ids).cards).toEqual(['a'])
   expect(effectiveSelection({...active,cards:[],option:''},'r',request,ids).cards).toEqual([])
   expect(effectiveSelection(emptySelection('r'),'r',request,ids).mode).toBe('')
   expect(effectiveSelection(active,'new-request',request,ids).option).toBe('')
   expect(effectiveSelection(active,'r',{...request,choices:['use:normal']},ids).mode).toBe('')
   expect(effectiveSelection({...emptySelection('r'),cards:['normal'],option:'use:normal'},'r',request,ids).cards).toEqual(['normal'])
  })
 }
 it('keeps material combinations from server only',()=>expect(materials('virtual:longhun:fire:a:b',ids)).toEqual(['a','b']))
})


describe('request and snapshot transitions',()=>{
 const option='virtual:qixi:a'
 const request={request_id:'r',choices:[option,'virtual:wusheng:b','use:normal'],eligible_card_ids:[],allowed_player_ids:['enemy'],request_type:'choose_option',play_card_targets:{[option]:{targets:['enemy'],min:1,max:1}}} as unknown as PendingRequest
 const saved={...emptySelection('r'),mode:'qixi',cards:['a'],option,targets:['enemy']}
 for(const transition of ['timeout','reconnect','turn end','avatar switch'])it(transition+' rejects the previous epoch',()=>{
  expect(effectiveSelection(saved,'r:'+transition,request,ids)).toEqual(emptySelection('r:'+transition))
 })
 it('death and request removal clear all selection',()=>expect(effectiveSelection(saved,'r',null,ids)).toEqual(emptySelection('r')))
 it('skill switch rejects old materials and targets',()=>{
  const switched=effectiveSelection({...saved,mode:'wusheng'},'r',request,ids)
  expect(switched.cards).toEqual([]);expect(switched.option).toBe('');expect(switched.targets).toEqual([])
 })
 it('authoritative target change removes stale targets',()=>{
  expect(effectiveSelection(saved,'r',{...request,play_card_targets:{[option]:{targets:['other'],min:1,max:1}}} as PendingRequest,ids).targets).toEqual([])
 })
})
