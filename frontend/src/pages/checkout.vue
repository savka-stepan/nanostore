<template>
  <VCard class="mx-auto my-8" max-width="900">
    <VCardTitle>
      <span class="text-h5">💳 Kasse</span>
    </VCardTitle>
    <VCardText>
      <VAlert v-if="loading" type="info" variant="tonal" class="mb-4">
        Lade Bestelldaten...
      </VAlert>
      <VAlert v-if="error" type="error" variant="tonal" class="mb-4">
        {{ error }}
      </VAlert>
      <div v-if="order && order.customer">
        <div class="mb-2">
          <label>Name</label>
          <input class="form-control" type="text" :value="order.customer.name" disabled>
        </div>
        <div class="mb-2">
          <label>Email</label>
          <input class="form-control" type="text" :value="order.customer.email" disabled>
        </div>
      </div>
      <div v-if="order">
        <VTable class="mb-4">
          <thead>
            <tr>
              <th>Produkt</th>
              <th>Menge</th>
              <th>Preis</th>
              <th>Summe</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in order.items" :key="item.id">
              <td>{{ item.name }}</td>
              <td>{{ item.quantity }}</td>
              <td>{{ formatPrice(item.price) }}</td>
              <td>{{ formatPrice(item.price * item.quantity) }}</td>
            </tr>
          </tbody>
        </VTable>
        <div class="mb-2">
          <label>IBAN</label>
          <div v-if="stripeLoading" class="d-flex align-center mb-2">
            <VProgressCircular indeterminate color="primary" size="24" class="me-2" />
            <span>Stripe wird initialisiert...</span>
          </div>
          <div v-show="!stripeLoading" id="iban-element" class="form-control"></div>
        </div>
        <div class="mb-4">
          <div class="text-h6">Summe: <strong>{{ formatPrice(order.total) }}</strong></div>
        </div>
        <div class="mt-6 text-end">
          <VProgressCircular v-if="paying" indeterminate color="primary" size="32" class="me-2 mb-2" />
          <VBtn color="success" :loading="paying" @click="pay" :disabled="stripeLoading">
            <VIcon icon="tabler-credit-card" class="me-2" /> Bestätigen und kaufe
          </VBtn>
          <VBtn color="error" class="ms-2" @click="cancel" :disabled="stripeLoading">
            <VIcon icon="tabler-x" class="me-2" /> Kauf abbrechen und beenden
          </VBtn>
        </div>
        <VAlert v-if="success" type="success" variant="tonal" class="mb-4">
          Zahlung erfolgreich! Die Bestätigung kann einen Moment dauern. Vielen Dank für Ihren Einkauf.
        </VAlert>
      </div>
    </VCardText>
  </VCard>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { createWebSocket, formatPrice } from '@/utils/helpers'

const order = ref(null)
const loading = ref(true)
const error = ref('')
const paying = ref(false)
const success = ref(false)
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
  stripe = window.Stripe(import.meta.env.STRIPE_PUBLISHABLE_KEY)
  elements = stripe.elements()
  if (!ibanElement) {
    ibanElement = elements.create('iban', { supportedCountries: ['SEPA'] })
    ibanElement.mount('#iban-element')
    ibanElement.on('ready', () => {
      stripeLoading.value = false
    })
  } else {
    stripeLoading.value = false
  }
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
          name: order.value.customer.name,
          email: order.value.customer.email,
        },
      },
    }
  )
  if (stripeError) {
    error.value = stripeError.message
    paying.value = false
  } else if (paymentIntent && paymentIntent.status === 'succeeded') {
    success.value = true
    paying.value = false
  }
}

async function pay() {
  if (stripeLoading.value) return
  paying.value = true
  error.value = ''
  try {
    // Get clientSecret from backend
    const response = await fetch('https://ofn.hof-homann.de/api/create-payment-intent/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ order_id: order.value.id, total: order.value.total })
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
  window.location.href = '/'
}

onMounted(() => {
  connectWS()
})

onBeforeUnmount(() => {
  closeWS()
})
</script>