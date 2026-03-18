<!-- Dashboard.vue -->
<template>
  <div class="grid grid-cols-1 md:grid-cols-2 gap-6 p-6">
    <!-- CRM Fournisseurs -->
    <div class="bg-white rounded-lg shadow p-6">
      <h2 class="text-xl font-bold mb-4">CRM Fournisseurs</h2>
      <div v-if="loading.documents">Chargement...</div>
      <table v-else class="min-w-full">
        <thead>
          <tr class="border-b">
            <th class="text-left py-2">Type</th>
            <th class="text-left py-2">SIREN</th>
            <th class="text-left py-2">Montant</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="doc in documents" :key="doc.id" class="border-b hover:bg-gray-50">
            <td class="py-2">{{ doc.type }}</td>
            <td class="py-2">{{ doc.siren }}</td>
            <td class="py-2">{{ doc.montant }} €</td>
          </tr>
        </tbody>
      </table>
    </div>
    
    <!-- Conformité avec alertes -->
    <div class="bg-white rounded-lg shadow p-6">
      <h2 class="text-xl font-bold mb-4">Conformité</h2>
      <div v-if="loading.alertes">Chargement...</div>
      <div v-else class="space-y-3">
        <div v-for="alerte in alertes" :key="alerte.id" 
             :class="[
               'p-4 rounded-lg',
               alerte.niveau === 'rouge' ? 'bg-red-100 border-l-4 border-red-600' :
               alerte.niveau === 'orange' ? 'bg-orange-100 border-l-4 border-orange-600' :
               'bg-green-100 border-l-4 border-green-600'
             ]">
          <div class="font-medium mb-1">⚠️ {{ alerte.niveau | capitalize }}</div>
          <p>{{ alerte.message }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const documents = ref([])
const alertes = ref([])
const loading = ref({ documents: true, alertes: true })

onMounted(async () => {
  // pour appeler les fausses api
  try {
    const docsRes = await axios.get('/api/fake/documents?_count=5')
    documents.value = docsRes.data
    
    const alertRes = await axios.get('/api/fake/alertes?_count=3')
    alertes.value = alertRes.data
  } catch (error) {
    console.error('Erreur chargement données', error)
  } finally {
    loading.value.documents = false
    loading.value.alertes = false
  }
})
</script>