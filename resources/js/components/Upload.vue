<!-- resources/js/components/FileUpload.vue -->
<template>
  <div class="p-6 bg-white rounded-lg shadow">
    <h2 class="text-xl font-bold mb-4">Upload de documents</h2>
    
    <!-- Zone de drop -->
    <div 
      @drop.prevent="handleDrop"
      @dragover.prevent
      @dragenter.prevent="setActive"
      @dragleave.prevent="setInactive"
      :data-active="active"
      class="border-2 border-dashed p-8 text-center cursor-pointer transition-colors"
      :class="active ? 'border-blue-500 bg-blue-50' : 'border-gray-300'"
    >
      <input 
        type="file" 
        multiple 
        @change="handleFileSelect" 
        class="hidden" 
        ref="fileInput"
        accept=".pdf,.jpg,.jpeg,.png"
      />
      
      <!-- Slot avec état partagé -->
      <div v-if="!files.length">
        <p class="mb-2">Glisse tes fichiers ici ou</p>
        <button 
          @click="$refs.fileInput.click()" 
          class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          Choisir des fichiers
        </button>
        <p class="text-sm text-gray-500 mt-2">PDF, JPG, PNG (max 10 Mo)</p>
      </div>
      
      <!-- Liste des fichiers sélectionnés -->
      <div v-else class="text-left">
        <p class="font-medium mb-2">Fichiers sélectionnés :</p>
        <ul class="space-y-2">
          <li v-for="(file, index) in files" :key="file.name" 
              class="flex justify-between items-center bg-gray-50 p-2 rounded">
            <span class="truncate max-w-xs">{{ file.name }}</span>
            <button @click="removeFile(index)" class="text-red-600 hover:text-red-800">
              Supprimer
            </button>
          </li>
        </ul>
      </div>
    </div>
    
    <!-- Barre de progression (optionnelle) -->
    <div v-if="uploading" class="mt-4">
      <div class="w-full bg-gray-200 rounded-full h-2.5">
        <div class="bg-blue-600 h-2.5 rounded-full" :style="{ width: progress + '%' }"></div>
      </div>
      <p class="text-sm text-center mt-1">{{ progress }}%</p>
    </div>
    
    <!-- Bouton d'upload -->
    <button 
      v-if="files.length"
      @click="uploadFiles"
      :disabled="uploading"
      class="mt-4 bg-green-600 text-white px-6 py-2 rounded hover:bg-green-700 disabled:bg-gray-400"
    >
      {{ uploading ? 'Upload en cours...' : 'Uploader les fichiers' }}
    </button>
    
    <!-- Message de retour -->
    <div v-if="message" class="mt-4 p-3 rounded" :class="messageType === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'">
      {{ message }}
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'

const files = ref([])
const active = ref(false)
const uploading = ref(false)
const progress = ref(0)
const message = ref('')
const messageType = ref('success')
let inactiveTimeout = null

// Gestion de l'état actif pour le drag & drop
const setActive = () => {
  active.value = true
  clearTimeout(inactiveTimeout)
}

const setInactive = () => {
  inactiveTimeout = setTimeout(() => {
    active.value = false
  }, 50)
}

// Sélection de fichiers
const handleFileSelect = (event) => {
  const selectedFiles = Array.from(event.target.files)
  files.value = [...files.value, ...selectedFiles]
}

// Drop de fichiers
const handleDrop = (event) => {
  setInactive()
  const droppedFiles = Array.from(event.dataTransfer.files)
  files.value = [...files.value, ...droppedFiles]
}

// Supprimer un fichier
const removeFile = (index) => {
  files.value.splice(index, 1)
}

// Upload des fichiers (VERSION MOCK POUR CE SOIR)
const uploadFiles = async () => {
  if (!files.value.length) return
  
  uploading.value = true
  progress.value = 0
  message.value = ''
  
  // Simulation d'upload (à remplacer par vraie API demain)
  for (let i = 0; i <= 100; i += 10) {
    progress.value = i
    await new Promise(resolve => setTimeout(resolve, 200))
  }
  
  // Succès simulé
  message.value = `${files.value.length} fichier(s) uploadé(s) avec succès !`
  messageType.value = 'success'
  files.value = [] // Vide la liste
  uploading.value = false
  
  // ICI DEMAIN : appel axios.post('/api/upload', formData)
}
</script>