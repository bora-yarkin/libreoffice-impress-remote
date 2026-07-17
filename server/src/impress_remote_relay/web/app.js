const RELAY_PROTOCOL_VERSION = 1
const RELAY_KIND_STATE = 'state'
const RELAY_KIND_COMMAND = 'command'
const RELAY_KIND_ERROR = 'error'
const REPLAY_CACHE_SIZE = 1024

function slideLabel(currentSlide, slideCount){
  if(!slideCount){
    return 'Slide -- / --'
  }
  return `Slide ${currentSlide + 1} / ${slideCount}`
}

function hashParams(){
  return new URLSearchParams(window.location.hash.replace(/^#/, ''))
}

function relaySocketUrl(session){
  const url = new URL('/ws', window.location.href)
  url.protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  url.searchParams.set('role', 'phone')
  url.searchParams.set('session', session)
  return url.toString()
}

function setStatus(message){
  document.getElementById('status').textContent = message
}

function setSocketState(message){
  document.getElementById('socket-state').textContent = message
}

function renderState(payload){
  setStatus(payload.statusMessage || (payload.running ? 'Presentation running' : 'Connected to relay.'))
  document.getElementById('slide').textContent = slideLabel(payload.currentSlide, payload.slideCount)
  document.getElementById('current-title').textContent = payload.currentTitle || 'Untitled slide'
  document.getElementById('notes').textContent = payload.notes || 'No presenter notes detected.'

  const nextSlide = typeof payload.nextSlide === 'number' ? `Slide ${payload.nextSlide + 1}` : 'No next slide'
  document.getElementById('next-slide').textContent = nextSlide
  document.getElementById('next-title').textContent = payload.nextTitle || 'No next slide'
  document.getElementById('next-preview').textContent = payload.nextPreview || 'The current slide is the last slide in the deck.'
}

function updateHash(session, pairingSecret){
  const params = new URLSearchParams()
  if(session){
    params.set('mode', 'relay')
    params.set('s', session)
  }
  if(pairingSecret){
    params.set('k', pairingSecret)
  }
  window.location.hash = params.toString()
}

function closeSocket(){
  if(state.socket){
    state.socket.onclose = null
    state.socket.close()
    state.socket = null
  }
}

function scheduleReconnect(){
  if(state.reconnectTimer || !state.session){
    return
  }
  state.reconnectTimer = window.setTimeout(() => {
    state.reconnectTimer = null
    connectRelay()
  }, 1500)
}

function utf8(text){
  return new TextEncoder().encode(text)
}

function concatBytes(...chunks){
  const total = chunks.reduce((sum, chunk) => sum + chunk.length, 0)
  const joined = new Uint8Array(total)
  let offset = 0
  for(const chunk of chunks){
    joined.set(chunk, offset)
    offset += chunk.length
  }
  return joined
}

function base64UrlToBytes(text){
  const padding = '='.repeat((4 - (text.length % 4 || 4)) % 4)
  const base64 = (text + padding).replace(/-/g, '+').replace(/_/g, '/')
  const binary = window.atob(base64)
  const bytes = new Uint8Array(binary.length)
  for(let index = 0; index < binary.length; index += 1){
    bytes[index] = binary.charCodeAt(index)
  }
  return bytes
}

function bytesToBase64Url(bytes){
  let binary = ''
  bytes.forEach(value => {
    binary += String.fromCharCode(value)
  })
  return window.btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '')
}

function rememberReplay(cache, nonceText){
  if(cache.values.has(nonceText)){
    return false
  }
  cache.values.add(nonceText)
  cache.order.push(nonceText)
  while(cache.order.length > REPLAY_CACHE_SIZE){
    const expired = cache.order.shift()
    cache.values.delete(expired)
  }
  return true
}

function frameAad(session, keyId, kind, nonceText){
  return utf8(JSON.stringify({
    kind,
    k: keyId,
    n: nonceText,
    s: session,
    v: RELAY_PROTOCOL_VERSION,
  }))
}

async function deriveRelayCodec(session, pairingSecret, hello){
  const secretBytes = base64UrlToBytes(pairingSecret)
  const pluginNonce = base64UrlToBytes(hello.pluginNonce)
  const baseKey = await crypto.subtle.importKey('raw', secretBytes, 'HKDF', false, ['deriveBits'])
  const salt = concatBytes(utf8('impress-remote-relay/v1'), new Uint8Array([0]), utf8(session))
  const info = concatBytes(utf8('relay-keys'), new Uint8Array([0]), utf8(hello.keyId), new Uint8Array([0]), pluginNonce)
  const bits = await crypto.subtle.deriveBits(
    {
      name: 'HKDF',
      hash: 'SHA-256',
      salt,
      info,
    },
    baseKey,
    512,
  )
  const material = new Uint8Array(bits)
  return {
    keyId: hello.keyId,
    stateKey: await crypto.subtle.importKey('raw', material.slice(0, 32), {name: 'AES-GCM'}, false, ['decrypt']),
    commandKey: await crypto.subtle.importKey('raw', material.slice(32, 64), {name: 'AES-GCM'}, false, ['encrypt']),
    pluginReplay: {values: new Set(), order: []},
  }
}

function parseHello(payload){
  if(
    payload.type !== 'hello'
    || payload.v !== RELAY_PROTOCOL_VERSION
    || typeof payload.s !== 'string'
    || typeof payload.k !== 'string'
    || typeof payload.nonce !== 'string'
  ){
    return null
  }
  return {
    sessionId: payload.s,
    keyId: payload.k,
    pluginNonce: payload.nonce,
  }
}

async function decryptRelayFrame(payload){
  if(!state.codec){
    throw new Error('Waiting for secure relay handshake.')
  }
  if(
    payload.type !== 'frame'
    || payload.v !== RELAY_PROTOCOL_VERSION
    || payload.s !== state.session
    || payload.k !== state.codec.keyId
    || typeof payload.kind !== 'string'
    || typeof payload.n !== 'string'
    || typeof payload.ct !== 'string'
  ){
    return null
  }
  if(payload.kind !== RELAY_KIND_STATE && payload.kind !== RELAY_KIND_ERROR){
    return null
  }
  if(!rememberReplay(state.codec.pluginReplay, payload.n)){
    throw new Error('Relay replay detected.')
  }
  const blob = base64UrlToBytes(payload.ct)
  if(blob.length < 16){
    throw new Error('Encrypted relay frame is truncated.')
  }
  const ciphertext = blob.slice(0, blob.length - 16)
  const tag = blob.slice(blob.length - 16)
  const combined = new Uint8Array(ciphertext.length + tag.length)
  combined.set(ciphertext, 0)
  combined.set(tag, ciphertext.length)
  const plaintext = await crypto.subtle.decrypt(
    {
      name: 'AES-GCM',
      iv: base64UrlToBytes(payload.n),
      additionalData: frameAad(state.session, state.codec.keyId, payload.kind, payload.n),
      tagLength: 128,
    },
    state.codec.stateKey,
    combined,
  )
  return {
    kind: payload.kind,
    payload: JSON.parse(new TextDecoder().decode(new Uint8Array(plaintext))),
  }
}

async function connectRelay(){
  closeSocket()
  state.codec = null
  if(!state.session){
    setStatus('Open the full pairing link from LibreOffice to connect.')
    setSocketState('Idle')
    return
  }
  if(!state.pairingSecret){
    setStatus('This relay route needs the full pairing link, not only the session code.')
    setSocketState('Missing key')
    return
  }
  if(!window.crypto || !window.crypto.subtle){
    setStatus('This browser does not expose Web Crypto, so encrypted relay mode is unavailable here.')
    setSocketState('Unsupported')
    return
  }

  setStatus('Connecting to relay...')
  setSocketState('Connecting')
  const socket = new WebSocket(relaySocketUrl(state.session))
  state.socket = socket

  socket.addEventListener('open', () => {
    setStatus('Connected to relay. Waiting for secure pairing data...')
    setSocketState('Connected')
  })

  socket.addEventListener('message', event => {
    handleIncoming(event.data).catch(error => {
      setStatus(String(error))
      setSocketState('Error')
    })
  })

  socket.addEventListener('close', () => {
    state.codec = null
    setSocketState('Disconnected')
    setStatus('Relay connection lost. Reconnecting...')
    scheduleReconnect()
  })

  socket.addEventListener('error', () => {
    setSocketState('Error')
    setStatus('Relay connection failed.')
  })
}

async function handleIncoming(raw){
  const payload = JSON.parse(raw)
  const hello = parseHello(payload)
  if(hello){
    if(hello.sessionId !== state.session){
      return
    }
    state.codec = await deriveRelayCodec(state.session, state.pairingSecret, hello)
    setSocketState('Encrypted')
    setStatus('Encrypted relay connected. Waiting for presentation state...')
    return
  }
  if(payload.type === 'error' && typeof payload.message === 'string'){
    setStatus(payload.message)
    return
  }
  const decrypted = await decryptRelayFrame(payload)
  if(!decrypted){
    return
  }
  if(decrypted.kind === RELAY_KIND_STATE && decrypted.payload){
    renderState(decrypted.payload)
    return
  }
  if(
    decrypted.kind === RELAY_KIND_ERROR
    && typeof decrypted.payload.message === 'string'
  ){
    setStatus(decrypted.payload.message)
  }
}

async function sendCommand(command, payload = {}){
  if(!state.socket || state.socket.readyState !== WebSocket.OPEN || !state.codec){
    return
  }
  const nonce = crypto.getRandomValues(new Uint8Array(12))
  const nonceText = bytesToBase64Url(nonce)
  const plaintext = utf8(JSON.stringify({command, ...payload}))
  const encrypted = await crypto.subtle.encrypt(
    {
      name: 'AES-GCM',
      iv: nonce,
      additionalData: frameAad(state.session, state.codec.keyId, RELAY_KIND_COMMAND, nonceText),
      tagLength: 128,
    },
    state.codec.commandKey,
    plaintext,
  )
  state.socket.send(JSON.stringify({
    type: 'frame',
    v: RELAY_PROTOCOL_VERSION,
    s: state.session,
    k: state.codec.keyId,
    kind: RELAY_KIND_COMMAND,
    n: nonceText,
    ct: bytesToBase64Url(new Uint8Array(encrypted)),
  }))
}

function parseSessionInput(value){
  const trimmed = value.trim()
  if(!trimmed){
    return {session: '', pairingSecret: ''}
  }
  if(trimmed.startsWith('#')){
    const params = new URLSearchParams(trimmed.replace(/^#/, ''))
    return {
      session: params.get('s') || '',
      pairingSecret: params.get('k') || '',
    }
  }
  try{
    const url = new URL(trimmed, window.location.href)
    const params = new URLSearchParams(url.hash.replace(/^#/, ''))
    const session = params.get('s') || ''
    const pairingSecret = params.get('k') || ''
    if(session || pairingSecret){
      return {session, pairingSecret}
    }
  }catch(_error){
  }
  return {session: trimmed, pairingSecret: state.pairingSecret}
}

const state = {
  session: '',
  pairingSecret: '',
  socket: null,
  reconnectTimer: null,
  codec: null,
}

document.getElementById('relay-origin').textContent = window.location.origin
document.querySelectorAll('[data-command]').forEach(button => {
  button.addEventListener('click', () => {
    sendCommand(button.dataset.command).catch(error => {
      setStatus(String(error))
      setSocketState('Error')
    })
  })
})

document.getElementById('goto-form').addEventListener('submit', event => {
  event.preventDefault()
  const input = document.getElementById('goto-slide')
  const value = Number.parseInt(input.value, 10)
  if(Number.isNaN(value) || value < 1){
    return
  }
  sendCommand('goto_slide', {index: value - 1}).catch(error => {
    setStatus(String(error))
    setSocketState('Error')
  })
})

document.getElementById('session-form').addEventListener('submit', event => {
  event.preventDefault()
  const parsed = parseSessionInput(document.getElementById('session-input').value)
  if(!parsed.session){
    return
  }
  state.session = parsed.session
  state.pairingSecret = parsed.pairingSecret
  document.getElementById('session-display').textContent = parsed.session
  updateHash(parsed.session, parsed.pairingSecret)
  connectRelay().catch(error => {
    setStatus(String(error))
    setSocketState('Error')
  })
})

const initialParams = hashParams()
state.session = initialParams.get('s') || ''
state.pairingSecret = initialParams.get('k') || ''
document.getElementById('session-input').value = state.session ? window.location.href : ''
document.getElementById('session-display').textContent = state.session || '----------'
connectRelay().catch(error => {
  setStatus(String(error))
  setSocketState('Error')
})
