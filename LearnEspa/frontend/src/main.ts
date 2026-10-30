import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

/* 样式引入顺序不可颠倒：
   theme.css 定义 CSS 变量 → components.css 使用变量 → pages.css 页面级排版 */
import '@/assets/styles/theme.css'
import '@/assets/styles/components.css'
import '@/assets/styles/pages.css'

const app = createApp(App)

app.use(createPinia()) // 必须在 use(router) 之前，路由里若用到 store 才不会报错
app.use(router)

app.mount('#app')
