import { mergeConfig } from 'vite'
import original from './vite.config'
export default mergeConfig(original, {server:{port:5178,strictPort:true,proxy:{'/api':{target:'http://127.0.0.1:8008',ws:true},'/health':{target:'http://127.0.0.1:8008'},'/ws':{target:'ws://127.0.0.1:8008',ws:true}}}})
