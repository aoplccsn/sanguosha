import { defineConfig } from '@playwright/test'
export default defineConfig({
 testDir:'./e2e',testMatch:'t20-3*.spec.ts',timeout:60000,workers:1,reporter:'line',
 use:{baseURL:'http://127.0.0.1:5174',trace:'retain-on-failure',screenshot:'only-on-failure'},
 webServer:[
  {command:'.venv\\Scripts\\python.exe -m uvicorn t203_fixture:app --app-dir tests --host 127.0.0.1 --port 8004',cwd:'..',env:{PYTHONPATH:'src'},url:'http://127.0.0.1:8004/health',reuseExistingServer:true},
  {command:'npx vite --config vite.t203.config.ts --host 127.0.0.1 --port 5174',url:'http://127.0.0.1:5174',reuseExistingServer:true},
 ],
})
