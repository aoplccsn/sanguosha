import type { ReactNode } from 'react'
const symbols: Record<string,string> = {heart:'♥',diamond:'♦',spade:'♠',club:'♣'}
export function SuitText({suit,rank='',children}: {suit:string;rank?:string;children?:ReactNode}) {
  const symbol=symbols[suit] ?? suit
  return <span className={'suit-text '+(['♥','♦'].includes(symbol)?'suit-red':'suit-black')}>{symbol}{rank}{children}</span>
}

export function BattleText({text}:{text:string}) {
  return <>{text.split(/([♥♦♠♣])/).map((part,index)=>/^[♥♦♠♣]$/.test(part)?<SuitText key={index} suit={part}/>:part)}</>
}
