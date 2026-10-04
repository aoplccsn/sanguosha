import config from './playwright.config'
export default { ...config, projects: [{ name: 'installed-edge', use: { ...config.projects![0].use, channel: 'msedge', launchOptions: { ignoreDefaultArgs: ['--disable-backgrounding-occluded-windows', '--disable-background-timer-throttling', '--disable-renderer-backgrounding'] } } }] }
