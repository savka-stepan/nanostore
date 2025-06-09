<template>
  <VCard class="mx-auto my-12" max-width="500">
    <VCardTitle>
      <span class="text-h5">🎉 {{ confirmationMessage }}</span>
    </VCardTitle>
    <VCardText>
      <VAlert type="success" class="mb-4">
        Ihr Einkauf war erfolgreich.<br>
        Sie können jetzt ein neues Einkauf starten.
      </VAlert>
      <div class="text-center mt-6">
        <VBtn color="primary" @click="goToWelcome">
          Zurück zum Start
        </VBtn>
      </div>
    </VCardText>
  </VCard>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'

const confirmationMessage = ref('Vielen Dank!')

let ws = null
let redirectTimeout = null

function connectWS() {
  if (ws) ws.close()
  ws = new window.WebSocket('ws://localhost:8765/')
  ws.onopen = () => {
    ws.send(JSON.stringify({ type: 'get_confirmation', key: 'confirmation-h1' }))
    ws.send(JSON.stringify({ type: 'confirmation_shown' }))
  }
  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      if (msg.type === 'confirmation' && msg.confirmation === 'confirmation-h1' && msg.value) {
        confirmationMessage.value = msg.value
      }
    } catch (err) {
      // Optionally handle error
    }
  }
  ws.onclose = () => { ws = null }
}

function goToWelcome() {
  if (ws && ws.readyState === 1) {
    ws.send(JSON.stringify({ type: 'end_session' }))
  }
  window.location.href = '/'
}

onMounted(() => {
  connectWS()
  redirectTimeout = setTimeout(goToWelcome, 10000)
})

onBeforeUnmount(() => {
  if (ws) ws.close()
  if (redirectTimeout) clearTimeout(redirectTimeout)
})
</script>