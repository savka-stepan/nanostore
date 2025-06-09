<script setup>
import paypal from '@images/cards/paypal-rounded.png'

const notifications = ref([
  {
    id: 2,
    text: 'Tom Holland',
    title: 'New user registered.',
    subtitle: '5 hours ago',
    time: 'Yesterday',
    isSeen: false,
  },
  {
    id: 4,
    img: paypal,
    title: 'PayPal',
    subtitle: 'Received Payment',
    time: '25 May',
    isSeen: false,
    color: 'error',
  },
])

const removeNotification = notificationId => {
  notifications.value.forEach((item, index) => {
    if (notificationId === item.id)
      notifications.value.splice(index, 1)
  })
}

const markRead = notificationId => {
  notifications.value.forEach(item => {
    notificationId.forEach(id => {
      if (id === item.id)
        item.isSeen = true
    })
  })
}

const markUnRead = notificationId => {
  notifications.value.forEach(item => {
    notificationId.forEach(id => {
      if (id === item.id)
        item.isSeen = false
    })
  })
}

const handleNotificationClick = notification => {
  if (!notification.isSeen)
    markRead([notification.id])
}
</script>

<template>
  <Notifications :notifications="notifications" @remove="removeNotification" @read="markRead" @unread="markUnRead"
    @click:notification="handleNotificationClick" />
</template>
