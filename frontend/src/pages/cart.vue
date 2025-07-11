<template>
  <div>
    <VCard class="mx-auto my-8 pa-6" max-width="900" elevation="10">
      <VCardTitle class="d-flex align-center mb-4">
        <VIcon icon="tabler-shopping-cart" color="primary" class="me-2" size="32" />
        <span class="text-h5 font-weight-bold">Warenkorb</span>
      </VCardTitle>
      <VCardText>
        <VSnackbar v-model="showProductNameError" :timeout="3000" color="error" location="top end">
          {{ productNameError }}
        </VSnackbar>
        <VAlert v-if="cart.length === 0" type="error" variant="tonal" class="mb-4">
          Dein Warenkorb ist leer.
        </VAlert>
        <VTable v-else>
          <thead>
            <tr>
              <th></th>
              <th>Produkt</th>
              <th>Kategorie</th>
              <th>Menge</th>
              <th>Preis</th>
              <th>Summe</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in cart" :key="item.id">
              <td>
                <VAvatar v-if="item.img" size="40" class="me-3" rounded>
                  <img :src="item.img" alt="Produktbild" />
                </VAvatar>
              </td>
              <td>
                <div>{{ item.name }}</div>
                <div v-if="item.gramm" class="text-caption text-grey-darken-1">({{ item.gramm }})</div>
              </td>
              <td>
                {{ item.category_name || '' }}
              </td>
              <td>
                <VBtn icon size="small" variant="tonal" color="secondary"
                  @click="updateQuantity(item, item.quantity - 1)" :disabled="item.quantity <= 1">
                  <VIcon icon="tabler-minus" />
                </VBtn>
                <span class="mx-2">{{ item.quantity }}</span>
                <VBtn icon size="small" variant="tonal" color="secondary"
                  @click="updateQuantity(item, item.quantity + 1)">
                  <VIcon icon="tabler-plus" />
                </VBtn>
              </td>
              <td>{{ formatPrice(item.price) }}</td>
              <td>{{ formatPrice(item.price * item.quantity) }}</td>
              <td>
                <VBtn icon size="small" variant="tonal" color="error" @click="removeItem(item)">
                  <VIcon icon="tabler-trash" />
                </VBtn>
              </td>
            </tr>
          </tbody>
          <tfoot>
            <tr>
              <td colspan="4" class="text-end"><strong>Gesamt:</strong></td>
              <td colspan="2"><strong>{{ formatPrice(total) }}</strong></td>
            </tr>
          </tfoot>
        </VTable>
        <div class="mt-6 text-end">
          <VBtn color="success" :disabled="cart.length === 0" @click="checkout">
            <VIcon icon="tabler-credit-card" class="me-2" /> Zur Kasse
          </VBtn>
          <VBtn color="error" class="ms-2" @click="cancel">
            <VIcon icon="tabler-x" class="me-2" /> Abbrechen
          </VBtn>
        </div>
      </VCardText>
    </VCard>

    <!-- Weighted products list with Category Buttons -->
    <VCard class="mx-auto my-8 pa-6" max-width="900" elevation="10">
      <VCardTitle class="d-flex align-center mb-4">
        <VIcon icon="tabler-scale" color="primary" class="me-2" size="32" />
        <span class="text-h5 font-weight-bold">Produkte nach Gewicht</span>
      </VCardTitle>
      <VCardText>
        <div class="mb-4">
          <VBtn v-for="cat in Object.values(taxesArray)" :key="cat.id" class="me-2 mb-2"
            :color="selectedCategory === cat.id ? 'primary' : 'secondary'" @click="selectedCategory = cat.id"
            variant="outlined" size="small">
            {{ cat.name }}
          </VBtn>
          <VBtn class="mb-2" color="grey" variant="text" size="small" @click="selectedCategory = null"
            v-if="selectedCategory">
            Alle anzeigen
          </VBtn>
        </div>
        <VRow>
          <VCol v-for="product in filteredWeightedProducts" :key="product.id" cols="12" md="6" lg="4" class="mb-4">
            <VCard outlined>
              <VCardTitle class="d-flex align-center">
                <VAvatar v-if="product.image" size="40" class="me-3" rounded>
                  <img :src="product.image" alt="Produktbild" />
                </VAvatar>
                <span>{{ product.name }}</span>
              </VCardTitle>
              <VCardText>
                <div class="text-caption text-grey-darken-1 mb-2">
                  {{ product.description || '' }}
                </div>
                <VBtn size="small" color="primary" block @click="openWeightModal(product)">
                  <VIcon icon="tabler-scale" class="me-1" />
                  Wiegen & hinzufügen
                </VBtn>
              </VCardText>
            </VCard>
          </VCol>
        </VRow>
      </VCardText>
    </VCard>

    <!-- Weighted Product Modal -->
    <VDialog v-model="showWeightModal" @update:modelValue="val => { if (!val) closeWeightModal() }" max-width="400">
      <template #default>
        <VCard>
          <VCardTitle>
            {{ weightProduct?.name }}
          </VCardTitle>
          <VCardText>
            <img v-if="weightProduct?.image" :src="weightProduct.image" class="mb-2" style="max-width: 100px;" />
            <div>Gewicht: {{ gramm }}</div>
            <div>Preis: {{ formatPrice(weightPrice) }}</div>
          </VCardText>
          <div class="d-flex justify-end pa-4">
            <VBtn color="error" @click="closeWeightModal">Abbruch</VBtn>
            <VBtn color="primary" class="ms-2" @click="addWeightedProduct">Zum Warenkorb</VBtn>
          </div>
        </VCard>
      </template>
    </VDialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { createWebSocket, formatPrice } from '@/utils/helpers'

const router = useRouter()

const cart = ref([])
const code = ref('')
const taxesArray = ref({})
const selectedCategory = ref(null)
const productWeightArray = ref({})
const showWeightModal = ref(false)
const weightProduct = ref(null)
const gramm = ref('0.000 kg')
const weightPrice = ref(0)
const showProductNameError = ref(false)
const productNameError = ref('')
const weightInterval = ref(null)

const handleWSOpen = () => {
  console.log('WebSocket connection established')
}

const handleWSClose = () => {
  console.log('WebSocket connection failed')
}

function handleWSMessage(event) {
  try {
    const msg = JSON.parse(event.data)
    if (msg.type === 'cart') {
      cart.value = msg.cart || []
    }

    if (msg.type === 'load_products') {
      taxesArray.value = msg.taxes_array || {}
      productWeightArray.value = msg.product_weight_array || {}
    }

    if (msg.type === 'weight') {
      if (msg.value) {
        gramm.value = msg.value + ' kg'
        const weightNum = Number(msg.value.replace(',', '.'))
        const unitValue = Number(weightProduct.value.unit_value)
        const unit = weightProduct.value.unit || ''
        const pricePerUnit = Number(weightProduct.value.price)

        let weightInUnit = weightNum

        if (unit.toLowerCase().includes('kg')) {
          // If the unit is in kg, convert weightNum (kg) to the unit scale
          // Example: unitValue = 1 (for 1kg), weightNum = 0.156 (kg)
          weightInUnit = weightNum / unitValue
        } else if (unit.toLowerCase().includes('g')) {
          // If the unit is in g, convert weightNum (kg) to grams if needed
          // Assume weightNum is in kg, convert to grams
          weightInUnit = (weightNum * 1000) / unitValue
        } else {
          // Default: treat as grams
          weightInUnit = weightNum / unitValue
        }

        weightPrice.value = (weightInUnit * pricePerUnit).toFixed(2)
        if (showWeightModal.value) {
          sendWS({ type: 'weight' })
        }
      }
    }

    if (msg.type === 'session' && msg.session === false) {
      router.push('/')
    }

    if (msg.type === 'search_product_code') {
      if (msg.exist) {
        sendWS({
          type: 'add_to_cart',
          id: msg.id,
          name: msg.name,
          price: msg.price,
          img: msg.img,
          category_id: msg.category_id,
          category_name: msg.category_name,
        })
      }
    }

    if (msg.type === 'search_product_name') {
      if (msg.exist && msg.product) {
        openWeightModal(msg.product)
      } else {
        productNameError.value = `Kein Produkt mit dem Namen "${msg.name}" gefunden.`
        showProductNameError.value = true
      }
    }
    if (msg.type === 'cart_deleted') {
      cart.value = []
    }
    // handle other message types as needed
  } catch (err) {
    console.error('WebSocket message error:', err)
  }
}

const { connectWS, sendWS, closeWS } = createWebSocket(
  'ws://localhost:8765/',
  handleWSMessage,
  handleWSOpen,
  handleWSClose
)

const fetchCart = () => {
  sendWS({ type: 'get_cart' })
  sendWS({ type: 'load_products' })
}

const updateQuantity = (item, newQty) => {
  if (newQty < 1) return
  sendWS({ type: 'update_quantity', id: item.id, quantity: newQty })
}

const removeItem = (item) => {
  sendWS({ type: 'remove_item', id: item.id })
}

const total = computed(() =>
  cart.value.reduce((sum, item) => sum + item.price * item.quantity, 0)
)

const checkout = () => {
  if (total.value < 0.5) return
  router.push('/checkout')
}

const cancel = () => {
  sendWS({ type: 'delete_cart' })
  router.push('/')
}

const handleProductCode = (codeValue) => {
  sendWS({ type: 'check_product_code', code: codeValue })
}

const handleProductInput = (inputValue) => {
  handleProductCode(inputValue)
}

const filteredWeightedProducts = computed(() => {
  if (!selectedCategory.value) return Object.values(productWeightArray.value)
  return Object.values(productWeightArray.value).filter(
    p => String(p.category_id) === String(selectedCategory.value)
  )
})

// --- Weighted product modal logic ---
const openWeightModal = (product) => {
  weightProduct.value = product
  showWeightModal.value = true
  gramm.value = '0.000 kg'
  weightPrice.value = 0

  // Start polling for weight every 0.5 seconds
  sendWS({ type: 'weight' });
  weightInterval.value = setInterval(() => {
    sendWS({ type: 'weight' })
  }, 500)
}

const closeWeightModal = () => {
  showWeightModal.value = false
  if (weightInterval.value) {
    clearInterval(weightInterval.value)
    weightInterval.value = null
  }
}

const addWeightedProduct = () => {
  const grammNumber = Math.round(Number(gramm.value.replace('kg', '').replace(',', '.').trim()) * 1000)
  if (grammNumber <= 0) {
    productNameError.value = 'Bitte ein gültiges Gewicht eingeben.'
    showProductNameError.value = true
    return
  }

  sendWS({
    type: 'add_to_cart',
    id: weightProduct.value.id,
    name: weightProduct.value.name,
    price: Number(weightPrice.value),
    quantity: 1, // Always 1 for weighted products
    img: weightProduct.value.image,
    gramm: gramm.value,
    category_id: weightProduct.value.category_id,
    category_name: weightProduct.value.category_name,
  })
  closeWeightModal()
}

const handleKeydown = (evt) => {
  if (evt.key === 'Enter') {
    handleProductInput(code.value)
    code.value = ''
  } else {
    code.value += evt.key
  }
}

onMounted(() => {
  connectWS()
  fetchCart()
  window.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
  closeWS()
})
</script>