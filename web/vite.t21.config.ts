import { mergeConfig } from 'vite'
import base from './vite.config'
export default mergeConfig(base,{server:{port:5221,proxy:{'/api':{target:'http://127.0.0.1:8021'},'/health':{target:'http://127.0.0.1:8021'},'/ws':{target:'ws://127.0.0.1:8021',ws:true}}}})
