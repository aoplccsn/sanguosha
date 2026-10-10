import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { resolve } from 'node:path'
import { spawnSync } from 'node:child_process'

const root = fileURLToPath(new URL('../../', import.meta.url))
const venv = resolve(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python')
// Explicit interpreter for worktrees/CI; otherwise prefer the project environment.
const python = process.env.PYTHON || (existsSync(venv) ? venv : 'python')
const args = process.argv.slice(2)
if (args.includes('--production')) {
  const probe = spawnSync(python, ['-c', 'from PIL import Image'], { encoding: 'utf8' })
  if (probe.status !== 0) {
    console.error('Production assets require Pillow in the project Python environment. Install .[web-build] in .venv, or set PYTHON to the project interpreter.')
    process.exit(1)
  }
}
const result = spawnSync(python, [resolve(root, 'scripts/sync_web_assets.py'), ...args], { stdio: 'inherit' })
if (result.error) console.error(result.error.message)
process.exit(result.status ?? 1)
