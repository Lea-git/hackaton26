import './bootstrap'
import { createApp } from 'vue'
import Upload from './components/Upload.vue'
import Dashboard from './components/Dashboard.vue'

const app = createApp({})

app.component('file-upload', Upload)
app.component('dashboard', Dashboard)

app.mount('#app')