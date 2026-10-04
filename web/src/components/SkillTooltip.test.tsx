import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { SkillTooltip, optionMetadata } from './SkillTooltip'
const general = {id:'caocao',name:'曹操',kingdom:'wei',max_hp:4,gender:'male',portrait:'',skills:[{id:'jianxiong',name:'奸雄',type:'trigger',description:'当你受到伤害后，你可以获得造成此伤害的牌。'}]}
it('resolves incarnation, skill and general choices from the same catalog',()=>{
  expect(optionMetadata('caocao:jianxiong',{caocao:general}).skills[0]).toBe(general.skills[0])
  expect(optionMetadata('skill:jianxiong',{caocao:general}).skills[0]).toBe(general.skills[0])
  expect(optionMetadata('caocao',{caocao:general}).general).toBe(general)
})
it('shows Chinese details for hover, focus and touch/info without consuming choice clicks',async()=>{
 const click=vi.fn();const user=userEvent.setup()
 render(<SkillTooltip general={general} skills={general.skills}><button onClick={click}>曹操 · 奸雄</button></SkillTooltip>)
 const choice=screen.getByRole('button',{name:'曹操 · 奸雄'})
 await user.hover(choice);expect(screen.getByRole('tooltip')).toHaveTextContent(general.skills[0].description)
 await user.click(choice);expect(click).toHaveBeenCalledOnce()
 await user.unhover(choice);await user.tab();expect(screen.getByRole('tooltip')).toBeInTheDocument()
 await user.keyboard('{Escape}');expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
 await user.click(screen.getByRole('button',{name:'查看曹操技能说明'}));expect(screen.getByRole('tooltip')).toHaveTextContent('魏 · 4 体力')
})
