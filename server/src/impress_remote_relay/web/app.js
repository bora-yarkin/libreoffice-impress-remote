const RELAY_PROTOCOL_VERSION = 1
const RELAY_KIND_STATE = 'state'
const RELAY_KIND_COMMAND = 'command'
const RELAY_KIND_ERROR = 'error'
const RELAY_KIND_ASSET = 'asset'
const REPLAY_CACHE_SIZE = 1024

let lastState = null
let connectionPhase = 'connecting'
let hasEverConnected = false
let currentImageObjectUrl = ''
let nextImageObjectUrl = ''
const nextImagePreload = new Image()

const relayState = {
  session: '',
  pairingSecret: '',
  socket: null,
  reconnectTimer: null,
  codec: null,
  assets: {
    current: {revision: '', url: ''},
    next: {revision: '', url: ''},
  },
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

function setConnectionPhase(nextPhase){
  connectionPhase = nextPhase
  document.body.dataset.connectionState = nextPhase
  const commandsEnabled = nextPhase === 'live'
  document.querySelectorAll('[data-command]').forEach(button => {
    button.disabled = !commandsEnabled
  })
  document.getElementById('prev-button').disabled = !commandsEnabled
  document.getElementById('next-button').disabled = !commandsEnabled
  renderBanner()
}

function renderBanner(){
  const target = document.getElementById('status')
  if(!target){
    return
  }
  if(connectionPhase === 'connecting'){
    target.textContent = 'Connecting to LibreOffice through the relay...'
    return
  }
  if(connectionPhase === 'reconnecting'){
    target.textContent = 'Relay connection lost. Reconnecting...'
    return
  }
  if(connectionPhase === 'offline'){
    target.textContent = 'Remote is offline. Open the full pairing link from LibreOffice again.'
    return
  }
  if(!lastState){
    target.textContent = 'Connected. Waiting for presenter state...'
    return
  }
  target.textContent = lastState.statusMessage || (lastState.running ? 'Presentation running' : 'Waiting for slideshow')
}

function slideLabel(currentSlide, slideCount){
  if(typeof currentSlide !== 'number' || !slideCount){
    return '-- / --'
  }
  return `${currentSlide + 1} / ${slideCount}`
}

function revokeObjectUrl(value){
  if(value){
    URL.revokeObjectURL(value)
  }
}

function clearSlideImage(){
  const image = document.getElementById('slide-image')
  const placeholder = document.getElementById('slide-placeholder')
  image.hidden = true
  placeholder.hidden = false
  image.removeAttribute('src')
}

function syncCurrentSlideAsset(){
  const image = document.getElementById('slide-image')
  const placeholder = document.getElementById('slide-placeholder')
  const expectedRevision = lastState && typeof lastState.currentSlideImageRevision === 'string'
    ? lastState.currentSlideImageRevision
    : ''
  const asset = relayState.assets.current
  if(!expectedRevision || asset.revision !== expectedRevision || !asset.url){
    clearSlideImage()
    currentImageObjectUrl = ''
    return
  }
  if(currentImageObjectUrl !== asset.url){
    const previousUrl = currentImageObjectUrl
    image.src = asset.url
    currentImageObjectUrl = asset.url
    if(previousUrl && previousUrl !== asset.url && previousUrl !== relayState.assets.next.url){
      revokeObjectUrl(previousUrl)
    }
  }
  image.hidden = false
  placeholder.hidden = true
}

function syncNextSlideAsset(){
  const expectedRevision = lastState && typeof lastState.nextSlideImageRevision === 'string'
    ? lastState.nextSlideImageRevision
    : ''
  const asset = relayState.assets.next
  if(!expectedRevision || asset.revision !== expectedRevision || !asset.url){
    nextImageObjectUrl = ''
    nextImagePreload.removeAttribute('src')
    return
  }
  if(nextImageObjectUrl !== asset.url){
    const previousUrl = nextImageObjectUrl
    nextImageObjectUrl = asset.url
    nextImagePreload.src = asset.url
    if(previousUrl && previousUrl !== asset.url && previousUrl !== currentImageObjectUrl){
      revokeObjectUrl(previousUrl)
    }
  }
}

function syncRenderedAssets(){
  syncCurrentSlideAsset()
  syncNextSlideAsset()
}

function showPlaceholderMessage(message){
  document.getElementById('current-title').textContent = message
  document.getElementById('notes').textContent = ''
  document.querySelectorAll('.slide-label').forEach(node => {
    node.textContent = '-- / --'
  })
  clearSlideImage()
}

function showTransportError(error){
  renderBanner()
  const status = document.getElementById('status')
  if(status){
    status.textContent = String(error)
  }
  setConnectionPhase('offline')
}

function renderState(state){
  lastState = state
  document.querySelectorAll('.slide-label').forEach(node => {
    node.textContent = slideLabel(state.currentSlide, state.slideCount)
  })
  document.getElementById('current-title').textContent = state.currentTitle || ''
  document.getElementById('notes').textContent = state.notes || ''
  document.getElementById('prev-button').disabled = connectionPhase !== 'live' || !state.canGoPrevious
  document.getElementById('next-button').disabled = connectionPhase !== 'live' || !state.canGoNext
  syncRenderedAssets()
  renderBanner()
}

function closeSocket(){
  if(relayState.socket){
    relayState.socket.onclose = null
    relayState.socket.close()
    relayState.socket = null
  }
}

function scheduleReconnect(){
  if(relayState.reconnectTimer || !relayState.session || !relayState.pairingSecret){
    return
  }
  relayState.reconnectTimer = window.setTimeout(() => {
    relayState.reconnectTimer = null
    connectRelay().catch(showTransportError)
  }, 1500)
}

function canAdvanceWithSlideTap(){
  return connectionPhase === 'live' && !!lastState && !!lastState.canGoNext
}

function handleSlideAdvance(){
  if(!canAdvanceWithSlideTap()){
    return
  }
  sendCommand('next_slide').catch(showTransportError)
}

document.querySelectorAll('[data-command]').forEach(button => {
  button.addEventListener('click', () => {
    sendCommand(button.dataset.command).catch(showTransportError)
  })
})

const slideFrame = document.getElementById('slide-frame')
slideFrame.addEventListener('click', () => {
  handleSlideAdvance()
})
slideFrame.addEventListener('keydown', event => {
  if(event.key !== 'Enter' && event.key !== ' '){
    return
  }
  event.preventDefault()
  handleSlideAdvance()
})

document.getElementById('slide-image').addEventListener('error', () => {
  clearSlideImage()
})

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
  if(!relayState.codec){
    throw new Error('Waiting for secure relay handshake.')
  }
  if(
    payload.type !== 'frame'
    || payload.v !== RELAY_PROTOCOL_VERSION
    || payload.s !== relayState.session
    || typeof payload.k !== 'string'
    || typeof payload.kind !== 'string'
    || typeof payload.n !== 'string'
    || typeof payload.ct !== 'string'
  ){
    return null
  }
  if(!rememberReplay(relayState.codec.pluginReplay, payload.n)){
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
      additionalData: frameAad(relayState.session, payload.k, payload.kind, payload.n),
      tagLength: 128,
    },
    relayState.codec.stateKey,
    combined,
  )
  return {
    kind: payload.kind,
    payload: JSON.parse(new TextDecoder().decode(new Uint8Array(plaintext))),
  }
}

async function applyAssetPayload(payload){
  const contentType = payload.contentType
  const encoding = payload.encoding
  const data = payload.data
  const slot = payload.slot
  const revision = payload.revision
  if(
    typeof contentType !== 'string'
    || typeof encoding !== 'string'
    || typeof data !== 'string'
    || typeof slot !== 'string'
    || typeof revision !== 'string'
    || encoding !== 'base64url'
    || !['current', 'next'].includes(slot)
  ){
    throw new Error('Relay asset payload is malformed.')
  }
  const blob = new Blob([base64UrlToBytes(data)], {type: contentType})
  const objectUrl = URL.createObjectURL(blob)
  const existing = relayState.assets[slot]
  if(existing.url && existing.url !== currentImageObjectUrl && existing.url !== nextImageObjectUrl){
    revokeObjectUrl(existing.url)
  }
  relayState.assets[slot] = {revision, url: objectUrl}
  syncRenderedAssets()
}

async function handleIncoming(raw){
  const payload = JSON.parse(raw)
  const hello = parseHello(payload)
  if(hello){
    if(hello.sessionId !== relayState.session){
      return
    }
    relayState.codec = await deriveRelayCodec(relayState.session, relayState.pairingSecret, hello)
    renderBanner()
    return
  }
  if(payload.type === 'error' && typeof payload.message === 'string'){
    throw new Error(payload.message)
  }
  const decrypted = await decryptRelayFrame(payload)
  if(!decrypted){
    return
  }
  if(decrypted.kind === RELAY_KIND_STATE && decrypted.payload){
    hasEverConnected = true
    setConnectionPhase('live')
    renderState(decrypted.payload)
    return
  }
  if(decrypted.kind === RELAY_KIND_ASSET && decrypted.payload){
    await applyAssetPayload(decrypted.payload)
    return
  }
  if(
    decrypted.kind === RELAY_KIND_ERROR
    && typeof decrypted.payload.message === 'string'
  ){
    throw new Error(decrypted.payload.message)
  }
}

async function sendCommand(command, payload = {}){
  if(!relayState.socket || relayState.socket.readyState !== WebSocket.OPEN || !relayState.codec){
    return
  }
  const nonce = crypto.getRandomValues(new Uint8Array(12))
  const nonceText = bytesToBase64Url(nonce)
  const plaintext = utf8(JSON.stringify({command, ...payload}))
  const encrypted = await crypto.subtle.encrypt(
    {
      name: 'AES-GCM',
      iv: nonce,
      additionalData: frameAad(relayState.session, relayState.codec.keyId, RELAY_KIND_COMMAND, nonceText),
      tagLength: 128,
    },
    relayState.codec.commandKey,
    plaintext,
  )
  relayState.socket.send(JSON.stringify({
    type: 'frame',
    v: RELAY_PROTOCOL_VERSION,
    s: relayState.session,
    k: relayState.codec.keyId,
    kind: RELAY_KIND_COMMAND,
    n: nonceText,
    ct: bytesToBase64Url(new Uint8Array(encrypted)),
  }))
}

async function connectRelay(){
  closeSocket()
  relayState.codec = null
  if(!relayState.session || !relayState.pairingSecret){
    showPlaceholderMessage('Open the full relay pairing link from LibreOffice.')
    setConnectionPhase('offline')
    return
  }
  if(!window.crypto || !window.crypto.subtle){
    showPlaceholderMessage('This browser does not support secure relay mode.')
    setConnectionPhase('offline')
    return
  }

  if(relayState.reconnectTimer){
    window.clearTimeout(relayState.reconnectTimer)
    relayState.reconnectTimer = null
  }

  showPlaceholderMessage('Connecting to the encrypted relay...')
  setConnectionPhase(hasEverConnected ? 'reconnecting' : 'connecting')
  const socket = new WebSocket(relaySocketUrl(relayState.session))
  relayState.socket = socket

  socket.addEventListener('open', () => {
    renderBanner()
  })

  socket.addEventListener('message', event => {
    handleIncoming(event.data).catch(showTransportError)
  })

  socket.addEventListener('close', () => {
    relayState.codec = null
    setConnectionPhase(hasEverConnected ? 'reconnecting' : 'connecting')
    scheduleReconnect()
  })

  socket.addEventListener('error', () => {
    showTransportError('Relay connection failed.')
  })
}

function bootstrap(){
  const params = hashParams()
  relayState.session = params.get('s') || ''
  relayState.pairingSecret = params.get('k') || ''
  setConnectionPhase('connecting')
  connectRelay().catch(showTransportError)
}

bootstrap()
