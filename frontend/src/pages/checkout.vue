<template>
  <VCard class="mx-auto my-8 pa-6" max-width="900" elevation="10">
    <VCardTitle class="d-flex align-center mb-4">
      <VIcon icon="tabler-credit-card" color="primary" class="me-2" size="32" />
      <span class="text-h5 font-weight-bold">Kasse</span>
    </VCardTitle>
    <VCardText>
      <VAlert v-if="loading" type="info" variant="tonal" class="mb-4">
        <VProgressCircular indeterminate color="primary" size="20" class="me-2" />
        Lade Bestelldaten...
      </VAlert>
      <VAlert v-if="error" type="error" variant="tonal" class="mb-4">
        {{ error }}
      </VAlert>

      <VRow v-if="order && order.customer" class="mb-4" dense>
        <VCol cols="12" md="4">
          <VTextField label="Name" :model-value="order.customer.full_name" prepend-inner-icon="tabler-user" readonly
            variant="outlined" density="compact" />
        </VCol>
        <VCol cols="12" md="4">
          <VTextField label="Email" :model-value="order.customer.email" prepend-inner-icon="tabler-mail" readonly
            variant="outlined" density="compact" />
        </VCol>
      </VRow>

      <VAlert type="info" variant="tonal" class="mb-4" v-if="order">
        Überprüfen Sie Ihre Bestellung und geben Sie Ihre Zahlungsdaten ein, um den Kauf abzuschließen.
      </VAlert>

      <div v-if="order">
        <VTable class="mb-4 elevation-1 rounded-lg">
          <thead>
            <tr>
              <th>Produkt</th>
              <th>Menge</th>
              <th>Preis</th>
              <th>Summe</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in order.cart" :key="item.id">
              <td>
                <div class="d-flex align-center">
                  <VAvatar v-if="item.img" :image="item.img" size="32" class="me-2" />
                  <span>{{ item.name }}</span>
                </div>
              </td>
              <td>{{ item.quantity }}</td>
              <td>{{ formatPrice(item.price) }}</td>
              <td>{{ formatPrice(item.price * item.quantity) }}</td>
            </tr>
          </tbody>
        </VTable>

        <VRow class="mb-2" align="center">
          <VCol cols="12" md="6">
            <VTextField label="IBAN" prepend-inner-icon="tabler-building-bank" readonly
              :model-value="order.customer.iban" variant="outlined" density="compact" class="mb-2" />
          </VCol>
          <VCol cols="12" md="6">
            <div>
              <label class="font-weight-medium mb-1">Zahlungsdaten eingeben</label>
              <div v-if="stripeLoading" class="d-flex align-center mb-2">
                <VProgressCircular indeterminate color="primary" size="24" class="me-2" />
                <span>Stripe wird initialisiert...</span>
              </div>
              <div v-show="!stripeLoading" id="iban-element" class="form-control rounded-lg border"
                style="min-height: 48px; padding: 8px;"></div>
            </div>
          </VCol>
        </VRow>

        <VDivider class="my-4" />

        <div class="d-flex justify-space-between align-center mb-4">
          <span class="text-h6"></span>
          <span class="text-h5 font-weight-bold text-primary">Summe: {{ formatPrice(order.total) }}</span>
        </div>

        <div class="d-flex justify-end align-center mt-4">
          <VBtn color="success" :loading="paying" @click="pay" :disabled="stripeLoading">
            <VIcon icon="tabler-credit-card" class="me-2" /> Bestätigen und kaufen
          </VBtn>
          <VBtn color="error" class="ms-2" @click="cancel" :disabled="stripeLoading">
            <VIcon icon="tabler-x" class="me-2" /> Kauf abbrechen und beenden
          </VBtn>
        </div>

      </div>
    </VCardText>
  </VCard>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { createWebSocket, formatPrice } from '@/utils/helpers'

const router = useRouter()
const order = ref(null)
const loading = ref(true)
const error = ref('')
const paying = ref(false)
const stripeLoading = ref(true)

let stripe = null
let elements = null
let ibanElement = null
let clientSecret = null

const handleWSOpen = () => {
  console.log('WebSocket connection established')
}

const handleWSClose = () => {
  console.log('WebSocket connection failed')
}

function handleWSMessage(event) {
  try {
    const msg = JSON.parse(event.data)
    if (msg.type === 'init_checkout') {
      order.value = msg.order
      loading.value = false
      setTimeout(initStripe, 100)
    }
  } catch (err) {
    error.value = 'WebSocket Fehler: ' + err.message
    loading.value = false
  }
}

const { connectWS, sendWS, closeWS } = createWebSocket(
  'ws://localhost:8765/',
  handleWSMessage,
  handleWSOpen,
  handleWSClose
)

function initStripe() {
  stripeLoading.value = true
  if (!window.Stripe) {
    stripeLoading.value = false
    return
  }
  stripe = window.Stripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY)
  elements = stripe.elements()
  // Remove previous IBAN element if remounting
  if (ibanElement) {
    try {
      ibanElement.unmount()
    } catch (e) { }
    ibanElement = null
  }
  ibanElement = elements.create('iban', { supportedCountries: ['SEPA'] })
  ibanElement.mount('#iban-element')
  ibanElement.on('ready', () => {
    stripeLoading.value = false
  })
}

async function confirmSepaPayment() {
  if (!stripe || !clientSecret) return
  paying.value = true
  error.value = ''
  const { error: stripeError, paymentIntent } = await stripe.confirmSepaDebitPayment(
    clientSecret,
    {
      payment_method: {
        sepa_debit: ibanElement,
        billing_details: {
          name: order.value.customer.full_name || '',
          email: order.value.customer.email || '',
        },
      },
    }
  )
  if (stripeError) {
    error.value = stripeError.message
    paying.value = false
  } else if (paymentIntent && (paymentIntent.status === 'succeeded' || paymentIntent.status === 'processing')) {
    paying.value = false
    router.push('/confirmation')
  } else {
    paying.value = false;
  }
}

async function pay() {
  if (stripeLoading.value) return
  paying.value = true
  error.value = ''
  try {
    // Get JWT token from localStorage
    const jwtToken = localStorage.getItem('jwtToken')
    // Get clientSecret from backend
    const response = await fetch('https://ofn.hof-homann.de/api/create-payment-intent/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'JWT ' + jwtToken
      },
      body: JSON.stringify({ order_id: order.value.order_id, total: order.value.total })
    })
    const data = await response.json()
    if (data.clientSecret) {
      clientSecret = data.clientSecret
      await confirmSepaPayment()
    } else {
      error.value = data.error || 'Fehler bei der Zahlungserstellung'
      paying.value = false
    }
  } catch (e) {
    error.value = e.message
    paying.value = false
  }
}

const cancel = () => {
  sendWS({ type: 'delete_cart' })
  router.push('/')
}

onMounted(() => {
  connectWS()
  sendWS({ type: 'checkout' })
})

onBeforeUnmount(() => {
  closeWS()
})
</script>