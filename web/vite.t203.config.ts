import { mergeConfig } from 'vite'
import base from './vite.config'
export default mergeConfig(base,{server:{port:5174,proxy:{'/api':{target:'http://127.0.0.1:8004'},'/health':{target:'http://127.0.0.1:8004'},'/ws':{target:'ws://127.0.0.1:8004',ws:true}}}})
