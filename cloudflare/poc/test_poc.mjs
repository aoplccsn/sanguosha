const base = process.env.POC_URL ?? "http://127.0.0.1:8787";
const wake = process.argv.includes("--wake");

async function json(path) {
  const response = await fetch(`${base}${path}`);
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  return response.json();
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
  console.log(`PASS ${message}`);
}

const health = await json("/health");
assert(health.python_worker === true, "Python Worker");
const fastapi = await json("/fastapi");
assert(fastapi.fastapi === true, "FastAPI ASGI");
const first = await json("/room/POC123");
const second = await json("/room/POC123");
assert(first.sqlite_ok === 1 && second.counter === first.counter + 1, "SQLite-backed Durable Object");
const html = await (await fetch(base)).text();
const hashed = html.match(/\/assets\/index-[\w-]+\.js/);
assert(Boolean(hashed), "Vite production index");
const script = await fetch(`${base}${hashed[0]}`);
assert(script.ok && script.headers.get("content-type")?.includes("javascript"), "Vite hashed asset");

const ws = new WebSocket(base.replace(/^http/, "ws") + "/room/POCWS1");
const messages = [];
const done = new Promise((resolve, reject) => {
  const timeout = setTimeout(() => reject(new Error("WebSocket timeout")), wake ? 190_000 : 20_000);
  ws.onopen = () => ws.send("before");
  ws.onerror = reject;
  ws.onclose = () => {
    if (messages.length < (wake ? 2 : 1)) reject(new Error("WebSocket closed early"));
  };
  ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    messages.push(message);
    if (messages.length === 1 && wake) {
      setTimeout(() => ws.send("after"), 155_000);
    } else {
      clearTimeout(timeout);
      ws.close();
      resolve();
    }
  };
});
await done;
assert(messages[0].player === "poc-player" && messages[0].message === "before", "Python DO WebSocket attachment");
if (wake) {
  assert(messages[1].player === "poc-player" && messages[1].message === "after", "WebSocket survives hibernation");
  assert(messages[1].instance_id !== messages[0].instance_id, "DO reconstructed after hibernation");
}
