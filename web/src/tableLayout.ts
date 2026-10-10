// Explicit seat anchors, listed in the server's clockwise order after the local seat.
// Pixel positions live in table.css (one block per anchor set); this only names the slots.
const anchors: Record<number, string[]> = {
  2: ['north'],
  4: ['east', 'north', 'west'],
  5: ['east', 'north-east', 'north-west', 'west'],
  8: ['east-lower', 'east-upper', 'north-east', 'north', 'north-west', 'west-upper', 'west-lower'],
}

export function seatAnchors(playerCount: number): string[] {
  return anchors[playerCount] ?? anchors[5]
}

export const boardClass = (playerCount: number) =>
  'game-board' + (playerCount === 8 ? ' eight-seats' : playerCount <= 4 ? ' small-party-seats' : '')
