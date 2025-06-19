<template>
  <div>
    <VCard class="mx-auto my-8 pa-6" max-width="900" elevation="10">
      <VCardTitle class="d-flex align-center mb-4">
        <VIcon icon="tabler-heart-handshake" color="primary" class="me-2" size="32" />
        <span class="text-h5 font-weight-bold">{{ welcomeH1 }}</span>
      </VCardTitle>
      <VCardText class="d-flex justify-center my-4">{{ welcomeH2 }}</VCardText>
      <div class="d-flex justify-center my-4">
        <VIcon size="64" icon="tabler-app-window" />
      </div>
      <div class="d-flex justify-center my-4">
        <VBtn color="primary" @click="startCardScan">
          Karte scannen
        </VBtn>
      </div>
    </VCard>
    <VSnackbar v-model="webSocketSnackbar" :timeout="3000" :color="webSocketSnackbarColor" location="top end">
      {{ webSocketMessage }}
    </VSnackbar>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { createWebSocket } from '@/utils/helpers'

const router = useRouter()

const welcomeH1 = ref('Herzlich Willkommen')
const welcomeH2 = ref('Bitte lege deine Kundenkarte auf den Kartenleser rechts vom Bildschirm, um dich anzumelden und zu starten')

const webSocketSnackbar = ref(false)
const webSocketMessage = ref('')
const webSocketSnackbarColor = ref('primary')

const handleWSOpen = () => {
  webSocketMessage.value = 'WebSocket connection established'
  webSocketSnackbarColor.value = 'primary'
  webSocketSnackbar.value = true
}

const handleWSClose = () => {
  webSocketMessage.value = 'WebSocket connection failed'
  webSocketSnackbarColor.value = 'error'
  welcomeH1.value = '❌ WebSocket-Verbindung fehlgeschlagen'
  welcomeH2.value = 'Bitte lade die Seite neu, um es erneut zu versuchen.'
  webSocketSnackbar.value = true
}

function handleWSMessage(event) {
  try {
    const msg = JSON.parse(event.data)
    // Save session_id if received from backend
    if (msg.type === 'session_id' && msg.session_id) {
      localStorage.setItem('session_id', msg.session_id)
    } else if (msg.type === 'customer_code') {
      sendWS({ type: 'check_customer_code', code: msg.code })
    } else if (msg.type === 'customer_code_checked') {
      if (msg.exist) {
        webSocketMessage.value = 'Willkommen, ' + msg.full_name + '!'
        webSocketSnackbar.value = true
        sleep(2000).then(() => {
          router.push('/cart')
        })
      } else {
        welcomeH2.value = '❌ Kein gültiger Benutzer'
      }
    }
    else if (msg.type === 'cart_deleted') {
      webSocketMessage.value = '🗑️ Warenkorb gelöscht'
      webSocketSnackbar.value = true
    } else {
      webSocketMessage.value = 'Unbekannte WebSocket-Nachricht: ' + msg.type
      webSocketSnackbar.value = true
    }
  } catch (error) {
    webSocketMessage.value = 'WebSocket message error: ' + error.message
    webSocketSnackbar.value = true
  }
}

function startCardScan() {
  sendWS({ type: 'login' })
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

const { connectWS, sendWS, closeWS } = createWebSocket(
  'ws://localhost:8765/',
  handleWSMessage,
  handleWSOpen,
  handleWSClose
)

onMounted(() => {
  connectWS()
})

onBeforeUnmount(() => {
  closeWS()
})
</script>