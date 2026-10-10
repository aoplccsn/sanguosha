import { defineConfig } from '@playwright/test'
// T21 visual review: PYTHON may point at any interpreter with the backend dependencies.
const python = process.env.PYTHON ?? (process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python')
export default defineConfig({
 testDir:'./e2e',testMatch:process.env.T21_MATCH ?? 't21*.spec.ts',timeout:90000,workers:1,reporter:'line',
 use:{baseURL:'http://127.0.0.1:5221',trace:'retain-on-failure',screenshot:'only-on-failure'},
 webServer:[
  {command:`"${python}" -m uvicorn t203_fixture:app --app-dir tests --host 127.0.0.1 --port 8021`,cwd:'..',env:{PYTHONPATH:'src'},url:'http://127.0.0.1:8021/health',reuseExistingServer:true,timeout:120000},
  {command:'npx vite --config vite.t21.config.ts --host 127.0.0.1 --port 5221',url:'http://127.0.0.1:5221',reuseExistingServer:true,timeout:120000},
 ],
})
