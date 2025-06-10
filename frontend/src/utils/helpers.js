export function formatPrice(price) {
  return `${Number(price).toFixed(2)} €`
}

export function createWebSocket(url, handleWSMessage, handleWSOpen, handleWSClose) {
  let ws = null
  let wsQueue = []
  let wsReady = false

  function connectWS() {
    if (ws) ws.close()
    wsReady = false
    ws = new window.WebSocket(url)
    ws.onopen = () => {
      wsReady = true
      while (wsQueue.length > 0) {
        ws.send(JSON.stringify(wsQueue.shift()))
      }
      if (typeof handleWSOpen === 'function') handleWSOpen()
    }
    ws.onmessage = handleWSMessage
    ws.onclose = () => {
      ws = null
      wsReady = false
      if (typeof handleWSClose === 'function') handleWSClose()
    }
    ws.onerror = () => {
      if (typeof handleWSClose === 'function') handleWSClose()
    }
  }

  function sendWS(msg) {
    const session_id = localStorage.getItem('session_id')
    if (session_id) {
      msg.session_id = session_id
    }
    if (!ws || ws.readyState !== 1) {
      wsQueue.push(msg)
      if (!ws) connectWS()
    } else {
      ws.send(JSON.stringify(msg))
    }
  }

  function closeWS() {
    if (ws) ws.close()
  }

  return { connectWS, sendWS, closeWS }
}