# T9.2 free capacity and local measurements

The Worker enforces five players and five WebSocket connections per room, a 256 KiB protocol message limit, a per-connection rate limit, a 7,200 second idle lease, and a global active-room lease cap of 100 in the SQLite-backed `RoomIndex` Durable Object.

| Simultaneous users | Suggested room mix | Local conclusion |
| ---: | --- | --- |
| 5 | one full room | within configured per-room limits |
| 10 | two full rooms | covered by the local runtime smoke path |
| 20 | four full rooms | covered by the local 20-game adapter; watch CPU and snapshot writes |
| 30 | six full rooms | plausible for friends-only traffic; validate current account quota |

These are planning estimates, not a billing guarantee. Cloudflare plan limits and pricing can change.

## Snapshot bytes

Measured with the authoritative Python snapshot serializer:

| State | Bytes |
| --- | ---: |
| lobby | 727 |
| early game | 57,447 |
| mid game | 66,571 |
| late game | 85,317 |

All measured snapshots remain below the 256 KiB protocol message limit. The limit applies to wire messages; storage writes use the Durable Object SQLite value store.

## Local load measurements

The local Wrangler load script opened independent rooms and sent application heartbeats:

| Connected clients | Messages | Elapsed seconds | Messages/second |
| ---: | ---: | ---: | ---: |
| 5 | 600 | 57.69 | 10.40 |
| 10 | 684 | 13.77 | 49.68 |
| 20 | 1,361 | 14.66 | 92.86 |
| 30 | 1,173 | 18.61 | 63.03 |

These figures are local development observations, not a promise of production latency or free-tier capacity.
