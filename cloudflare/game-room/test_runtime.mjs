const base = process.env.GAME_ROOM_URL ?? 'http://127.0.0.1:8793';
const version = 2;

const catalogResponse = await fetch(`${base}/api/catalog/generals`);
if (!catalogResponse.ok) throw new Error(`general catalog: HTTP ${catalogResponse.status}`);
const catalog = await catalogResponse.json();
if (catalog.length !== 65 || catalog.filter((item) => item.id.includes('_god_')).length !== 8)
  throw new Error('general catalog must contain 65 entries including 8 gods');
for (const item of catalog) {
  if (!item.name || !/[\u3400-\u9fff]/u.test(item.name) || !item.portrait.endsWith('.webp') || !item.max_hp)
    throw new Error(`incomplete general metadata: ${item.id}`);
  if ('choices' in item || 'request' in item)
    throw new Error(`catalog leaked private draft data: ${item.id}`);
}
if (process.env.FAST_METRICS !== '1') {
  const portraits = await Promise.all(catalog.map((item) => fetch(`${base}${item.portrait}`, { method: 'HEAD' })));
  if (portraits.some((response) => !response.ok)) throw new Error('missing production general portrait');
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
  console.log(`PASS ${message}`);
}

async function createRoom() {
  const response = await fetch(`${base}/api/rooms`, { method: 'POST' });
  if (!response.ok) throw new Error(`create room: HTTP ${response.status} ${await response.text()}`);
  return (await response.json()).room_code;
}

function client(code, name, reconnectToken = '') {
  const url = base.replace(/^http/, 'ws') + `/room/${code}`;
  const ws = new WebSocket(url);
  const messages = [];
  const waiters = [];
  ws.addEventListener('message', (event) => {
    const message = JSON.parse(String(event.data));
    messages.push(message);
    for (const waiter of [...waiters]) {
      if (waiter.type === message.type && waiter.predicate(message)) {
        waiters.splice(waiters.indexOf(waiter), 1);
        waiter.resolve(message);
      }
    }
  });
  const opened = new Promise((resolve, reject) => {
    ws.addEventListener('open', resolve, { once: true });
    ws.addEventListener('error', reject, { once: true });
  });
  function send(type, fields = {}) {
    ws.send(JSON.stringify({ type, version, ...fields }));
  }
  function wait(type, timeoutMs = 120000, predicate = () => true) {
    const existing = messages.find((item) => item.type === type && predicate(item));
    if (existing) return Promise.resolve(existing);
    return new Promise((resolve, reject) => {
      let timer;
      const waiter = {
        type,
        predicate,
        resolve(message) {
          clearTimeout(timer);
          resolve(message);
        },
      };
      waiters.push(waiter);
      timer = setTimeout(() => {
        const index = waiters.indexOf(waiter);
        if (index >= 0) waiters.splice(index, 1);
        reject(new Error(`${name}: timeout waiting for ${type}; seen=${messages.map((m) => m.type).join(',')}`));
      }, timeoutMs);
    });
  }
  return { ws, messages, opened, send, wait, name, reconnectToken };
}

const code = await createRoom();
assert(/^[23456789ABCDEFGHJKLMNPQRSTUVWXYZ]{6}$/.test(code), 'secure room code');

const host = client(code, 'host');
await host.opened;
await host.wait('WELCOME');
host.send('HELLO');
host.send('JOIN_ROOM', { room_code: code, name: 'host', created: true });
const hostIdentity = await host.wait('ROOM_CREATED');
await host.wait('LOBBY_STATE');
assert(hostIdentity.seat_id === 'p1' && Boolean(hostIdentity.reconnect_token), 'host joins GameRoom');

const guest = client(code, 'guest');
await guest.opened;
await guest.wait('WELCOME');
guest.send('HELLO');
guest.send('JOIN_ROOM', { room_code: code, name: 'guest' });
const guestIdentity = await guest.wait('WELCOME', 120000, (message) => Boolean(message.seat_id));
await guest.wait('LOBBY_STATE');
assert(guestIdentity.seat_id === 'p2' && Boolean(guestIdentity.reconnect_token), 'guest joins same GameRoom');

guest.send('READY', { ready: true });
await host.wait('LOBBY_STATE', 120000, (message) =>
  message.seats?.some((seat) => seat.seat_id === 'p2' && seat.ready === true));
host.send('START_GAME');
const hostDraft = await host.wait('DRAFT_REQUEST');
const guestDraft = await guest.wait('DRAFT_REQUEST');
assert(hostDraft.request.choices.length === 10 && guestDraft.request.choices.length === 10, 'private general drafts delivered');
assert(JSON.stringify(hostDraft.request.choices) !== JSON.stringify(guestDraft.request.choices), 'general candidates remain per-player');
assert(hostDraft.request.remaining_ms > 58000 && hostDraft.request.remaining_ms <= 60000,
  'human draft deadline is 60 seconds');
const hostSentAt = performance.now();
host.send('SUBMIT_DECISION', { decision: { request_id: hostDraft.request.request_id, value: hostDraft.request.choices[0] } });
const hostAck = await host.wait('DECISION_ACCEPTED', 120000,
  (message) => message.request_id === hostDraft.request.request_id);
const hostAckAt = performance.now();
const guestSentAt = performance.now();
guest.send('SUBMIT_DECISION', { decision: { request_id: guestDraft.request.request_id, value: guestDraft.request.choices[0] } });
const guestAck = await guest.wait('DECISION_ACCEPTED', 120000,
  (message) => message.request_id === guestDraft.request.request_id);
const guestAckAt = performance.now();
await guest.wait('PROJECTION_UPDATE', 120000,
  (message) => message.after_request_id === guestDraft.request.request_id);
const projectionAt = performance.now();
assert(hostAck.server_timing_ms && guestAck.server_timing_ms,
  'non-sensitive server decision timing is included in ACK');
assert(guestAckAt <= projectionAt, 'ACK arrives before resulting projection');
assert(host.messages.some((m) => m.type === 'PROJECTION_UPDATE'), 'authoritative GameSession started');

guest.ws.close();
await new Promise((resolve) => setTimeout(resolve, 250));
const restored = client(code, 'guest-reconnect');
await restored.opened;
await restored.wait('WELCOME');
restored.send('HELLO');
restored.send('RECONNECT', { room_code: code, name: 'guest', token: guestIdentity.reconnect_token });
const reconnectWelcome = await restored.wait('WELCOME', 120000, (message) => Boolean(message.seat_id));
await restored.wait('PROJECTION_UPDATE');
assert(reconnectWelcome.seat_id === guestIdentity.seat_id, 'reconnect restores same seat');
assert(restored.messages.some((m) => m.type === 'PROJECTION_UPDATE'), 'reconnect restores projection');

const status = await (await fetch(`${base}/api/rooms/${code}`)).json();
assert(status.phase === 'IN_GAME', 'SQLite snapshot reports active game');

host.ws.close();
restored.ws.close();
console.log(JSON.stringify({ code, phase: status.phase, hostMessages: host.messages.length,
  guestMessages: guest.messages.length, reconnectMessages: restored.messages.length,
  localDecisionTimingMs: {
    hostSendToAck: +(hostAckAt - hostSentAt).toFixed(2),
    guestSendToAck: +(guestAckAt - guestSentAt).toFixed(2),
    guestAckToProjection: +(projectionAt - guestAckAt).toFixed(2),
    hostServer: hostAck.server_timing_ms,
    guestServer: guestAck.server_timing_ms,
  } }));
