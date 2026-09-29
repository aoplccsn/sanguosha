const base = process.env.GAME_ROOM_URL ?? 'http://127.0.0.1:8793';
const version = 2;

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
host.send('SUBMIT_DECISION', { decision: { request_id: hostDraft.request.request_id, value: hostDraft.request.choices[0] } });
guest.send('SUBMIT_DECISION', { decision: { request_id: guestDraft.request.request_id, value: guestDraft.request.choices[0] } });
await host.wait('PROJECTION_UPDATE');
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

const status = await (await fetch(`${base}/room/${code}`)).json();
assert(status.phase === 'IN_GAME', 'SQLite snapshot reports active game');

host.ws.close();
restored.ws.close();
console.log(JSON.stringify({ code, phase: status.phase, hostMessages: host.messages.length, guestMessages: guest.messages.length, reconnectMessages: restored.messages.length }));
