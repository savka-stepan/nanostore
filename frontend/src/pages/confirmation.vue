<template>
  <VCard class="mx-auto my-8 pa-6" max-width="900" elevation="10">
    <VCardTitle class="d-flex align-center mb-4">
      <VIcon icon="tabler-rosette-discount-check" color="primary" class="me-2" size="32" />
      <span class="text-h5 font-weight-bold">{{ confirmationMessage }}</span>
    </VCardTitle>
    <VCardText>
      <VAlert type="info" variant="tonal" class="mb-4">
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
import { useRouter } from 'vue-router'
import { createWebSocket } from '@/utils/helpers'

const router = useRouter()
const confirmationMessage = ref('Vielen Dank!')
let redirectTimeout = null

const handleWSOpen = () => {
  // Optionally log or handle open
}

const handleWSClose = () => {
  // Optionally log or handle close
}

function handleWSMessage(event) {
  try {
    const msg = JSON.parse(event.data)
    if (
      msg.type === 'confirmation' &&
      msg.confirmation === 'confirmation-h1' &&
      msg.value
    ) {
      confirmationMessage.value = msg.value
    }
  } catch (err) {
    // Optionally handle error
  }
}

const { connectWS, sendWS, closeWS } = createWebSocket(
  'ws://localhost:8765/',
  handleWSMessage,
  handleWSOpen,
  handleWSClose
)

function goToWelcome() {
  sendWS({ type: 'end_session' })
  router.push('/')
}

onMounted(() => {
  connectWS()
  sendWS({ type: 'get_confirmation', key: 'confirmation-h1' })
  redirectTimeout = setTimeout(goToWelcome, 10000)
})

onBeforeUnmount(() => {
  closeWS()
  if (redirectTimeout) clearTimeout(redirectTimeout)
})
</script>