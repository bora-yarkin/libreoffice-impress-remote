const RELAY_PROTOCOL_VERSION = 1
const RELAY_KIND_STATE = 'state'
const RELAY_KIND_COMMAND = 'command'
const RELAY_KIND_ERROR = 'error'
const RELAY_KIND_ASSET = 'asset'
const REPLAY_CACHE_SIZE = 1024

const DEFAULT_LOCALE = 'en'
let supportedLocales = new Set([DEFAULT_LOCALE])
let activeLocale = DEFAULT_LOCALE
let messages = {}

let lastState = null
let connectionPhase = 'connecting'
let hasEverConnected = false
let transportErrorMessage = ''
let eventSource = null
let pollTimer = null
let lastImageUrl = ''
let lastNextImageUrl = ''
let currentImageObjectUrl = ''
let nextImageObjectUrl = ''
let previousSlideForTimer = null
let totalTimerBaseSeconds = 0
let totalTimerBaseMs = Date.now()
let totalTimerRunning = false
let slideTimerBaseMs = Date.now()
let frozenTotalTimerSeconds = 0
let frozenSlideTimerSeconds = 0
let timerPaused = false
let presentationFullscreen = false
const nextImagePreload = new Image()

const routeParams = hashParams()
const routeMode = routeParams.get('mode') || 'local'
const routeSession = routeParams.get('s') || ''
const pairingSecret = routeParams.get('k') || ''
const relayAdmissionToken = routeParams.get('a') || ''

const secureState = {
  codec: null,
}

const relayState = {
  session: routeSession,
  pairingSecret,
  admissionToken: relayAdmissionToken,
  socket: null,
  reconnectTimer: null,
  codec: null,
  assets: {
    current: {revision: '', url: ''},
    next: {revision: '', url: ''},
  },
}

function normalizeLocale(value){
  const language = String(value || '').trim().replace('-', '_').split(/[._]/)[0].toLowerCase()
  return supportedLocales.has(language) ? language : ''
}

function preferredLocale(){
  const params = new URLSearchParams(window.location.search)
  return normalizeLocale(params.get('lang'))
    || normalizeLocale(routeParams.get('lang'))
    || normalizeLocale(navigator.language)
    || DEFAULT_LOCALE
}

async function loadLocalization(){
  await loadLocalizationManifest()
  activeLocale = preferredLocale()
  messages = await fetchLocalization(DEFAULT_LOCALE)
  if(activeLocale !== DEFAULT_LOCALE){
    messages = {...messages, ...await fetchLocalization(activeLocale)}
  }
  document.documentElement.lang = activeLocale
  applyDocumentLocalization()
}

async function loadLocalizationManifest(){
  try{
    const response = await fetch('/localizations/manifest.json', {cache: 'no-store'})
    if(!response.ok){
      return
    }
    const payload = await response.json()
    if(!payload || typeof payload !== 'object' || !Array.isArray(payload.locales)){
      return
    }
    const locales = payload.locales
      .map(locale => String(locale || '').trim().replace('-', '_').split(/[._]/)[0].toLowerCase())
      .filter(Boolean)
    if(locales.includes(DEFAULT_LOCALE)){
      supportedLocales = new Set(locales)
    }
  }catch(_error){
  }
}

async function fetchLocalization(locale){
  try{
    const response = await fetch(`/localizations/${locale}.json`, {cache: 'no-store'})
    if(!response.ok){
      return {}
    }
    const payload = await response.json()
    return payload && typeof payload === 'object' && !Array.isArray(payload) ? payload : {}
  }catch(_error){
    return {}
  }
}

function t(key, values = {}){
  const template = typeof messages[key] === 'string' ? messages[key] : key
  return template.replace(/\{([A-Za-z0-9_]+)\}/g, (_match, name) => {
    return Object.prototype.hasOwnProperty.call(values, name) ? String(values[name]) : `{${name}}`
  })
}

function localizedMessage(message){
  return typeof messages[message] === 'string' ? t(message) : message
}

function applyDocumentLocalization(){
  document.querySelectorAll('[data-i18n]').forEach(node => {
    node.textContent = t(node.dataset.i18n)
  })
  document.querySelectorAll('[data-i18n-attr]').forEach(node => {
    node.dataset.i18nAttr.split(',').forEach(pair => {
      const [attribute, key] = pair.split(':').map(value => value.trim())
      if(attribute && key){
        node.setAttribute(attribute, t(key))
      }
    })
  })
  document.title = t('app.title')
}

function hashParams(){
  return new URLSearchParams(window.location.hash.replace(/^#/, ''))
}

function isRelayMode(){
  return routeMode === 'relay'
}

function isLocalMode(){
  return routeMode === 'local'
}

function hasWebCrypto(){
  return !!(window.crypto && window.crypto.subtle)
}

function isLocalFallbackMode(){
  return isLocalMode() && !hasWebCrypto()
}

function isSecureDirectMode(){
  return !isRelayMode() && !isLocalFallbackMode()
}

function relaySocketUrl(session, admissionToken){
  const url = new URL('/ws', window.location.href)
  url.protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  url.searchParams.set('role', 'phone')
  url.searchParams.set('session', session)
  if(admissionToken){
    url.searchParams.set('a', admissionToken)
  }
  return url.toString()
}

function directSessionUrl(path){
  const url = new URL(path, window.location.href)
  url.searchParams.set('s', routeSession)
  return `${url.pathname}${url.search}`
}

function setConnectionPhase(nextPhase){
  connectionPhase = nextPhase
  if(nextPhase !== 'offline'){
    transportErrorMessage = ''
  }
  document.body.dataset.connectionState = nextPhase
  const commandsEnabled = nextPhase === 'live'
  document.querySelectorAll('[data-command]').forEach(button => {
    button.disabled = !commandsEnabled
  })
  syncNavigationButtons(lastState)
  const gotoButton = document.getElementById('goto-button')
  const timerButton = document.getElementById('timer-toggle-button')
  if(gotoButton){
    gotoButton.disabled = !commandsEnabled
  }
  if(timerButton){
    timerButton.disabled = !commandsEnabled
  }
  renderBanner()
}

function syncNavigationButtons(state){
  const previousDisabled = connectionPhase !== 'live' || !state || !state.canGoPrevious
  const nextDisabled = connectionPhase !== 'live' || !state || !state.canGoNext
  document.querySelectorAll('[data-command="previous_slide"]').forEach(button => {
    button.disabled = previousDisabled
  })
  document.querySelectorAll('[data-command="next_slide"]').forEach(button => {
    button.disabled = nextDisabled
  })
}

function messageFromError(error){
  if(error && typeof error === 'object' && typeof error.message === 'string'){
    return error.message
  }
  return String(error || t('web.errorUnknown'))
}

function connectionCopy(){
  if(connectionPhase === 'connecting'){
    return {
      title: isRelayMode() ? t('web.connection.connectingRelayTitle') : t('web.connection.connectingTitle'),
      detail: isRelayMode() ? t('web.connectingRelay') : t('web.connecting'),
      actions: false,
    }
  }
  if(connectionPhase === 'reconnecting'){
    return {
      title: t('web.connection.reconnectingTitle'),
      detail: isRelayMode() ? t('web.reconnectingRelay') : t('web.reconnecting'),
      actions: true,
    }
  }
  if(connectionPhase === 'offline'){
    return {
      title: t('web.connection.offlineTitle'),
      detail: transportErrorMessage || (isRelayMode() ? t('web.offlineRelay') : t('web.offline')),
      actions: true,
    }
  }
  return {
    title: '',
    detail: '',
    actions: false,
  }
}

function renderConnectionPanel(){
  const panel = document.getElementById('connection-panel')
  if(!panel){
    return
  }
  const title = document.getElementById('connection-title')
  const detail = document.getElementById('connection-detail')
  const retryButton = document.getElementById('retry-button')
  const reloadButton = document.getElementById('reload-button')
  const copy = connectionCopy()
  const shouldShow = connectionPhase !== 'live'
  panel.hidden = !shouldShow
  if(title){
    title.textContent = copy.title
  }
  if(detail){
    detail.textContent = copy.detail
  }
  if(retryButton){
    retryButton.hidden = !copy.actions
  }
  if(reloadButton){
    reloadButton.hidden = !copy.actions
  }
}

function renderBanner(){
  const target = document.getElementById('status')
  if(!target){
    return
  }
  renderConnectionPanel()
  if(connectionPhase === 'offline' && transportErrorMessage){
    target.textContent = transportErrorMessage
    return
  }
  if(connectionPhase === 'connecting'){
    target.textContent = isRelayMode()
      ? t('web.connectingRelay')
      : t('web.connecting')
    return
  }
  if(connectionPhase === 'reconnecting'){
    target.textContent = isRelayMode()
      ? t('web.reconnectingRelay')
      : t('web.reconnecting')
    return
  }
  if(connectionPhase === 'offline'){
    target.textContent = isRelayMode()
      ? t('web.offlineRelay')
      : t('web.offline')
    return
  }
  if(!lastState){
    target.textContent = t('web.connectedWaiting')
    return
  }
  target.textContent = lastState.statusMessage || (lastState.running ? t('web.presentationRunning') : t('web.waitingSlideshow'))
}

function slideLabel(currentSlide, slideCount){
  if(typeof currentSlide !== 'number' || !slideCount){
    return '-- / --'
  }
  return `${currentSlide + 1} / ${slideCount}`
}

function formatElapsed(seconds){
  const normalized = Number.isFinite(seconds) && seconds > 0 ? Math.floor(seconds) : 0
  const hours = Math.floor(normalized / 3600)
  const minutes = Math.floor((normalized % 3600) / 60)
  const remainingSeconds = normalized % 60
  const two = value => String(value).padStart(2, '0')
  if(hours > 0){
    return `${hours}:${two(minutes)}:${two(remainingSeconds)}`
  }
  return `${two(minutes)}:${two(remainingSeconds)}`
}

function currentTimerValues(state = lastState){
  if(!state || !state.running){
    return {total: 0, slide: 0}
  }
  if(timerPaused){
    return {
      total: frozenTotalTimerSeconds,
      slide: frozenSlideTimerSeconds,
    }
  }
  const now = Date.now()
  return {
    total: totalTimerBaseSeconds + Math.floor((now - totalTimerBaseMs) / 1000),
    slide: Math.floor((now - slideTimerBaseMs) / 1000),
  }
}

function renderTimers(state){
  const stack = document.getElementById('timer-stack')
  const totalTimer = document.getElementById('total-timer-chip')
  const slideTimer = document.getElementById('slide-timer-chip')
  if(!stack || !totalTimer || !slideTimer){
    return
  }
  const shouldShow = !!(state && state.running)
  stack.hidden = !shouldShow
  if(shouldShow){
    const values = currentTimerValues(state)
    totalTimer.textContent = `Σ ${formatElapsed(values.total)}`
    slideTimer.textContent = `↻ ${formatElapsed(values.slide)}`
  }
}

function syncTimerState(state){
  if(!state || !state.running){
    previousSlideForTimer = null
    totalTimerBaseSeconds = 0
    totalTimerBaseMs = Date.now()
    totalTimerRunning = false
    slideTimerBaseMs = Date.now()
    frozenTotalTimerSeconds = 0
    frozenSlideTimerSeconds = 0
    timerPaused = false
    renderTimers(state)
    syncTimerButton()
    return
  }
  const currentSlide = typeof state.currentSlide === 'number' ? state.currentSlide : null
  if(!totalTimerRunning){
    const elapsedSeconds = Number(state.elapsedSeconds || 0)
    totalTimerBaseSeconds = Number.isFinite(elapsedSeconds) ? Math.max(0, elapsedSeconds) : 0
    totalTimerBaseMs = Date.now()
    totalTimerRunning = true
  }
  if(previousSlideForTimer !== currentSlide){
    previousSlideForTimer = currentSlide
    slideTimerBaseMs = Date.now()
    frozenSlideTimerSeconds = 0
  }
  renderTimers(state)
  syncTimerButton()
}

function toggleTimers(){
  if(!lastState || !lastState.running){
    return
  }
  if(timerPaused){
    timerPaused = false
    totalTimerBaseSeconds = frozenTotalTimerSeconds
    totalTimerBaseMs = Date.now()
    slideTimerBaseMs = Date.now() - frozenSlideTimerSeconds * 1000
  }else{
    const values = currentTimerValues(lastState)
    frozenTotalTimerSeconds = values.total
    frozenSlideTimerSeconds = values.slide
    timerPaused = true
  }
  renderTimers(lastState)
  syncTimerButton()
}

function setDrawerOpen(open){
  const drawer = document.getElementById('command-drawer')
  const button = document.getElementById('more-button')
  if(!drawer || !button){
    return
  }
  drawer.hidden = !open
  button.setAttribute('aria-expanded', open ? 'true' : 'false')
}

function drawerOpen(){
  const drawer = document.getElementById('command-drawer')
  return !!drawer && !drawer.hidden
}

function closeDrawer(){
  setDrawerOpen(false)
}

function toggleDrawer(){
  setDrawerOpen(!drawerOpen())
}

function fullscreenElement(){
  return document.fullscreenElement || document.webkitFullscreenElement || null
}

async function requestFullscreenMode(){
  const root = document.documentElement
  try{
    if(root.requestFullscreen){
      await root.requestFullscreen()
    }else if(root.webkitRequestFullscreen){
      root.webkitRequestFullscreen()
    }
  }catch(_error){
  }
  try{
    if(screen.orientation && screen.orientation.lock){
      await screen.orientation.lock('landscape')
    }
  }catch(_error){
  }
  setPresentationFullscreen(true)
}

async function exitFullscreenMode(){
  try{
    if(screen.orientation && screen.orientation.unlock){
      screen.orientation.unlock()
    }
  }catch(_error){
  }
  try{
    if(document.exitFullscreen && fullscreenElement()){
      await document.exitFullscreen()
    }else if(document.webkitExitFullscreen && fullscreenElement()){
      document.webkitExitFullscreen()
    }
  }catch(_error){
  }
  setPresentationFullscreen(false)
}

function setPresentationFullscreen(enabled){
  presentationFullscreen = !!enabled
  document.body.classList.toggle('presentation-fullscreen', presentationFullscreen)
  document.querySelectorAll('.side-controls').forEach(node => {
    node.setAttribute('aria-hidden', presentationFullscreen ? 'false' : 'true')
  })
  syncFullscreenButton()
  syncNavigationButtons(lastState)
}

function syncFullscreenButton(){
  const button = document.getElementById('fullscreen-button')
  if(!button){
    return
  }
  const label = presentationFullscreen ? t('aria.exitFullscreen') : t('aria.enterFullscreen')
  button.setAttribute('aria-label', label)
  button.title = label
  button.classList.toggle('drawer-button-active', presentationFullscreen)
}

function togglePresentationFullscreen(){
  closeDrawer()
  if(presentationFullscreen){
    exitFullscreenMode()
    return
  }
  requestFullscreenMode()
}

function syncTimerButton(){
  const button = document.getElementById('timer-toggle-button')
  if(!button){
    return
  }
  const label = timerPaused ? t('aria.resumeTimer') : t('aria.pauseTimer')
  button.setAttribute('aria-label', label)
  button.title = label
  button.classList.toggle('drawer-button-active', !timerPaused)
  button.innerHTML = timerPaused
    ? '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M9 5v14l10-7z"/></svg>'
    : '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M9 6v12M15 6v12"/></svg>'
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

async function updateSlideImage(state){
  if(isRelayMode()){
    syncCurrentSlideAsset()
    return
  }
  const image = document.getElementById('slide-image')
  const placeholder = document.getElementById('slide-placeholder')
  const nextUrl = state.currentSlideImageUrl || ''
  if(!nextUrl){
    image.hidden = true
    placeholder.hidden = false
    lastImageUrl = ''
    revokeObjectUrl(currentImageObjectUrl)
    currentImageObjectUrl = ''
    return
  }
  if(nextUrl !== lastImageUrl){
    const blobUrl = isLocalFallbackMode()
      ? await fetchLocalFallbackSlideObjectUrl(nextUrl)
      : await fetchSecureSlideObjectUrl(nextUrl)
    if((lastState && lastState.currentSlideImageUrl) !== nextUrl){
      revokeObjectUrl(blobUrl)
      return
    }
    revokeObjectUrl(currentImageObjectUrl)
    currentImageObjectUrl = blobUrl
    image.src = blobUrl
    lastImageUrl = nextUrl
  }
  image.hidden = false
  placeholder.hidden = true
}

async function preloadNextSlide(state){
  if(isRelayMode()){
    syncNextSlideAsset()
    return
  }
  const nextUrl = state.nextSlideImageUrl || ''
  if(!nextUrl){
    lastNextImageUrl = ''
    revokeObjectUrl(nextImageObjectUrl)
    nextImageObjectUrl = ''
    return
  }
  if(nextUrl === lastNextImageUrl){
    return
  }
  const blobUrl = isLocalFallbackMode()
    ? await fetchLocalFallbackSlideObjectUrl(nextUrl)
    : await fetchSecureSlideObjectUrl(nextUrl)
  if((lastState && lastState.nextSlideImageUrl) !== nextUrl){
    revokeObjectUrl(blobUrl)
    return
  }
  revokeObjectUrl(nextImageObjectUrl)
  nextImageObjectUrl = blobUrl
  nextImagePreload.src = blobUrl
  lastNextImageUrl = nextUrl
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
  if(!isRelayMode()){
    return
  }
  syncCurrentSlideAsset()
  syncNextSlideAsset()
}

function showPlaceholderMessage(message){
  document.getElementById('current-title').textContent = message
  document.getElementById('notes').textContent = ''
  document.querySelectorAll('.slide-label').forEach(node => {
    node.textContent = '-- / --'
  })
  syncTimerState(null)
  clearSlideImage()
}

function showTransportError(error){
  transportErrorMessage = messageFromError(error)
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
  syncNavigationButtons(state)
  syncTimerState(state)
  updateSlideImage(state).catch(showTransportError)
  preloadNextSlide(state).catch(showTransportError)
  if(isRelayMode()){
    syncRenderedAssets()
  }
  renderBanner()
}

async function fetchJson(url, options){
  const response = await fetch(url, options)
  let data = {}
  try{
    data = await response.json()
  }catch(_error){
    data = {}
  }
  if(!response.ok){
    throw new Error(data.error || `${response.status} ${response.statusText}`)
  }
  return data
}

function localFallbackHeaders(extra = {}){
  return {
    ...extra,
    'X-Impress-Remote-Session': routeSession,
    'X-Impress-Remote-Secret': pairingSecret,
  }
}

async function fetchLocalFallbackJson(url, options = {}){
  return fetchJson(url, {
    ...options,
    headers: localFallbackHeaders(options.headers || {}),
  })
}

async function refreshLocalFallbackStateSnapshot(){
  const state = await fetchLocalFallbackJson('/api/local/state')
  hasEverConnected = true
  setConnectionPhase('live')
  renderState(state)
}

async function sendLocalFallbackCommand(commandName, payload = {}){
  await fetchLocalFallbackJson('/api/local/command', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({command: commandName, ...payload}),
  })
  await refreshLocalFallbackStateSnapshot()
}

async function fetchLocalFallbackSlideObjectUrl(url){
  const response = await fetch(url, {
    headers: localFallbackHeaders(),
  })
  if(!response.ok){
    throw new Error(`${response.status} ${response.statusText}`)
  }
  const blob = await response.blob()
  return URL.createObjectURL(blob)
}

async function refreshStateSnapshot(){
  if(isRelayMode()){
    return
  }
  if(isLocalFallbackMode()){
    return refreshLocalFallbackStateSnapshot()
  }
  if(isSecureDirectMode()){
    return refreshSecureDirectStateSnapshot()
  }
}

function connectEvents(){
  if(isRelayMode()){
    connectRelay().catch(showTransportError)
    return
  }
  if(isLocalFallbackMode()){
    startPollingFallback()
    return
  }
  if(isSecureDirectMode()){
    connectSecureDirectEvents().catch(showTransportError)
    return
  }
}

function startPollingFallback(){
  if(pollTimer){
    window.clearInterval(pollTimer)
  }
  const poll = async () => {
    try{
      await refreshStateSnapshot()
    }catch(_error){
      setConnectionPhase(hasEverConnected ? 'reconnecting' : 'connecting')
    }
  }
  poll().catch(() => {})
  pollTimer = window.setInterval(() => {
    poll().catch(() => {})
  }, 1500)
}

async function command(name, payload = {}){
  if(isRelayMode()){
    await sendRelayCommand(name, payload)
    return
  }
  if(isLocalFallbackMode()){
    await sendLocalFallbackCommand(name, payload)
    return
  }
  if(isSecureDirectMode()){
    await sendSecureDirectCommand(name, payload)
    return
  }
}

function stopTransports(){
  if(eventSource){
    eventSource.close()
    eventSource = null
  }
  if(pollTimer){
    window.clearInterval(pollTimer)
    pollTimer = null
  }
  if(relayState.reconnectTimer){
    window.clearTimeout(relayState.reconnectTimer)
    relayState.reconnectTimer = null
  }
  closeSocket()
}

function retryConnection(){
  stopTransports()
  transportErrorMessage = ''
  setConnectionPhase(hasEverConnected ? 'reconnecting' : 'connecting')
  connectEvents()
}

document.querySelectorAll('[data-command]').forEach(button => {
  button.addEventListener('click', () => {
    command(button.dataset.command).then(closeDrawer).catch(showTransportError)
  })
})

document.getElementById('more-button').addEventListener('click', event => {
  event.stopPropagation()
  toggleDrawer()
})

document.getElementById('fullscreen-button').addEventListener('click', event => {
  event.stopPropagation()
  togglePresentationFullscreen()
})

document.addEventListener('fullscreenchange', () => {
  if(!fullscreenElement()){
    setPresentationFullscreen(false)
  }
})

document.addEventListener('webkitfullscreenchange', () => {
  if(!fullscreenElement()){
    setPresentationFullscreen(false)
  }
})

document.getElementById('timer-toggle-button').addEventListener('click', () => {
  toggleTimers()
})

document.getElementById('goto-button').addEventListener('click', () => {
  const input = document.getElementById('goto-input')
  const value = Number.parseInt(input.value, 10)
  if(!Number.isFinite(value) || value < 1){
    input.focus()
    return
  }
  const maxSlide = lastState && typeof lastState.slideCount === 'number'
    ? Math.max(lastState.slideCount, 1)
    : value
  input.value = ''
  command('goto_slide', {index: Math.min(value, maxSlide) - 1})
    .then(closeDrawer)
    .catch(showTransportError)
})

window.setInterval(() => {
  renderTimers(lastState)
}, 1000)

document.getElementById('goto-input').addEventListener('keydown', event => {
  if(event.key !== 'Enter'){
    return
  }
  event.preventDefault()
  document.getElementById('goto-button').click()
})

document.addEventListener('click', event => {
  if(!drawerOpen()){
    return
  }
  const drawer = document.getElementById('command-drawer')
  const moreButton = document.getElementById('more-button')
  if(drawer.contains(event.target) || moreButton.contains(event.target)){
    return
  }
  closeDrawer()
})

document.getElementById('retry-button').addEventListener('click', () => {
  retryConnection()
})

document.getElementById('reload-button').addEventListener('click', () => {
  window.location.reload()
})

function canAdvanceWithSlideTap(){
  return connectionPhase === 'live' && !!lastState && !!lastState.canGoNext
}

function handleSlideAdvance(){
  if(!canAdvanceWithSlideTap()){
    return
  }
  command('next_slide').catch(showTransportError)
}

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

async function deriveRelayCodec(session, secretText, hello){
  const pairingVerifier = base64UrlToBytes(secretText)
  const pluginNonce = base64UrlToBytes(hello.pluginNonce)
  const pluginPublicKey = base64UrlToBytes(hello.publicKey)
  const phoneKeyPair = await crypto.subtle.generateKey(
    {name: 'ECDH', namedCurve: 'P-256'},
    false,
    ['deriveBits'],
  )
  const phonePublicKey = new Uint8Array(await crypto.subtle.exportKey('raw', phoneKeyPair.publicKey))
  const importedPluginPublicKey = await crypto.subtle.importKey(
    'raw',
    pluginPublicKey,
    {name: 'ECDH', namedCurve: 'P-256'},
    false,
    [],
  )
  const sharedSecret = await crypto.subtle.deriveBits(
    {
      name: 'ECDH',
      public: importedPluginPublicKey,
    },
    phoneKeyPair.privateKey,
    256,
  )
  const baseKey = await crypto.subtle.importKey('raw', new Uint8Array(sharedSecret), 'HKDF', false, ['deriveBits'])
  const salt = concatBytes(utf8('impress-remote-relay/v1'), new Uint8Array([0]), utf8(session), new Uint8Array([0]), pairingVerifier)
  const info = concatBytes(
    utf8('relay-keys'),
    new Uint8Array([0]),
    utf8(hello.keyId),
    new Uint8Array([0]),
    pluginNonce,
    new Uint8Array([0]),
    pluginPublicKey,
    new Uint8Array([0]),
    phonePublicKey,
  )
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
  const keySet = {
    stateKey: await crypto.subtle.importKey('raw', material.slice(0, 32), {name: 'AES-GCM'}, false, ['decrypt']),
    commandKey: await crypto.subtle.importKey('raw', material.slice(32, 64), {name: 'AES-GCM'}, false, ['encrypt']),
    pluginReplay: {values: new Set(), order: []},
  }
  return {
    keyId: hello.keyId,
    keySet,
    responseHello: {
      type: 'hello',
      v: RELAY_PROTOCOL_VERSION,
      s: session,
      k: hello.keyId,
      nonce: hello.pluginNonce,
      role: 'phone',
      pub: bytesToBase64Url(phonePublicKey),
      suite: 'ECDH-P256+HKDF-SHA256+AES-256-GCM',
      rotate: hello.keyRotationMessages,
      features: [RELAY_KIND_STATE, RELAY_KIND_COMMAND, RELAY_KIND_ERROR, RELAY_KIND_ASSET],
    },
  }
}

function parseHello(payload){
  if(
    payload.type !== 'hello'
    || payload.v !== RELAY_PROTOCOL_VERSION
    || typeof payload.s !== 'string'
    || typeof payload.k !== 'string'
    || typeof payload.nonce !== 'string'
    || payload.role !== 'plugin'
    || typeof payload.pub !== 'string'
  ){
    return null
  }
  return {
    sessionId: payload.s,
    keyId: payload.k,
    pluginNonce: payload.nonce,
    publicKey: payload.pub,
    keyRotationMessages: typeof payload.rotate === 'number' ? payload.rotate : 300,
  }
}

function storeNegotiatedCodec(existingCodec, negotiated){
  const codec = existingCodec || {activeKeyId: '', keys: {}}
  codec.keys[negotiated.keyId] = negotiated.keySet
  codec.activeKeyId = negotiated.keyId
  return codec
}

async function applySecureHelloPayload(payload, responseHandler = null){
  const hello = parseHello(payload)
  if(!hello){
    throw new Error(t('web.directHandshakeInvalid'))
  }
  if(hello.sessionId !== routeSession){
    throw new Error(t('web.directHandshakeMismatch'))
  }
  const negotiated = await deriveRelayCodec(routeSession, pairingSecret, hello)
  secureState.codec = storeNegotiatedCodec(secureState.codec, negotiated)
  if(responseHandler){
    await responseHandler(negotiated.responseHello)
  }
}

async function establishSecureDirectHandshake(){
  if(secureState.codec){
    return
  }
  const hello = await fetchJson(directSessionUrl('/api/direct/handshake'))
  await applySecureHelloPayload(hello, responseHello => {
    return fetchJson(directSessionUrl('/api/direct/handshake'), {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(responseHello),
    })
  })
}

async function decryptSecureFramePayload(payload){
  if(!secureState.codec){
    throw new Error(t('web.secureDirectHandshakeWaiting'))
  }
  if(
    payload.type !== 'frame'
    || payload.v !== RELAY_PROTOCOL_VERSION
    || payload.s !== routeSession
    || typeof payload.k !== 'string'
    || typeof payload.kind !== 'string'
    || typeof payload.n !== 'string'
    || typeof payload.ct !== 'string'
  ){
    return null
  }
  const keySet = secureState.codec.keys[payload.k]
  if(!keySet){
    return null
  }
  if(!rememberReplay(keySet.pluginReplay, payload.n)){
    throw new Error(t('web.secureDirectReplay'))
  }
  const blob = base64UrlToBytes(payload.ct)
  if(blob.length < 16){
    throw new Error(t('web.directPayloadTruncated'))
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
      additionalData: frameAad(routeSession, payload.k, payload.kind, payload.n),
      tagLength: 128,
    },
    keySet.stateKey,
    combined,
  )
  return {
    kind: payload.kind,
    payload: JSON.parse(new TextDecoder().decode(new Uint8Array(plaintext))),
  }
}

async function refreshSecureDirectStateSnapshot(){
  await establishSecureDirectHandshake()
  const payload = await fetchJson(directSessionUrl('/api/direct/state'))
  if(payload.hello){
    await applySecureHelloPayload(payload.hello, responseHello => {
      return fetchJson(directSessionUrl('/api/direct/handshake'), {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(responseHello),
      })
    })
  }
  const decrypted = await decryptSecureFramePayload(payload.frame)
  if(!decrypted || decrypted.kind !== RELAY_KIND_STATE){
    throw new Error(t('web.directStateInvalid'))
  }
  hasEverConnected = true
  setConnectionPhase('live')
  renderState(decrypted.payload)
}

async function connectSecureDirectEvents(){
  if(!pairingSecret || !routeSession){
    throw new Error(t('web.directLinkRequired'))
  }
  if(!hasWebCrypto()){
    throw new Error(t('web.webCryptoDirectUnsupported'))
  }
  if(!('EventSource' in window)){
    startPollingFallback()
    return
  }
  await establishSecureDirectHandshake()
  if(eventSource){
    eventSource.close()
  }
  eventSource = new EventSource(directSessionUrl('/api/direct/events'))
  eventSource.addEventListener('open', () => {
    setConnectionPhase(hasEverConnected ? 'live' : 'connecting')
  })
  eventSource.addEventListener('hello', event => {
    applySecureHelloPayload(JSON.parse(event.data), responseHello => {
      return fetchJson(directSessionUrl('/api/direct/handshake'), {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(responseHello),
      })
    })
      .then(() => {
        hasEverConnected = true
        if(connectionPhase !== 'offline'){
          setConnectionPhase('live')
        }
      })
      .catch(showTransportError)
  })
  eventSource.addEventListener('state', event => {
    decryptSecureFramePayload(JSON.parse(event.data))
      .then(decrypted => {
        if(!decrypted || decrypted.kind !== RELAY_KIND_STATE){
          return
        }
        hasEverConnected = true
        setConnectionPhase('live')
        renderState(decrypted.payload)
      })
      .catch(showTransportError)
  })
  eventSource.onerror = () => {
    setConnectionPhase(hasEverConnected ? 'reconnecting' : 'connecting')
  }
}

async function buildSecureCommandFrame(commandName, payload = {}){
  await establishSecureDirectHandshake()
  const nonce = crypto.getRandomValues(new Uint8Array(12))
  const nonceText = bytesToBase64Url(nonce)
  const plaintext = utf8(JSON.stringify({command: commandName, ...payload}))
  const encrypted = await crypto.subtle.encrypt(
    {
      name: 'AES-GCM',
      iv: nonce,
      additionalData: frameAad(routeSession, secureState.codec.activeKeyId, RELAY_KIND_COMMAND, nonceText),
      tagLength: 128,
    },
    secureState.codec.keys[secureState.codec.activeKeyId].commandKey,
    plaintext,
  )
  return {
    type: 'frame',
    v: RELAY_PROTOCOL_VERSION,
    s: routeSession,
    k: secureState.codec.activeKeyId,
    kind: RELAY_KIND_COMMAND,
    n: nonceText,
    ct: bytesToBase64Url(new Uint8Array(encrypted)),
  }
}

async function sendSecureDirectCommand(commandName, payload = {}){
  const frame = await buildSecureCommandFrame(commandName, payload)
  await fetchJson(directSessionUrl('/api/direct/command'), {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(frame),
  })
  if(!eventSource){
    await refreshSecureDirectStateSnapshot()
  }
}

async function fetchSecureSlideObjectUrl(url){
  const payload = await fetchJson(url)
  if(payload.hello){
    await applySecureHelloPayload(payload.hello, responseHello => {
      return fetchJson(directSessionUrl('/api/direct/handshake'), {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(responseHello),
      })
    })
  }
  const decrypted = await decryptSecureFramePayload(payload.frame)
  if(!decrypted || decrypted.kind !== RELAY_KIND_ASSET){
    throw new Error(t('web.directSlideInvalid'))
  }
  const contentType = decrypted.payload.contentType
  const encoding = decrypted.payload.encoding
  const data = decrypted.payload.data
  if(
    typeof contentType !== 'string'
    || typeof encoding !== 'string'
    || typeof data !== 'string'
    || encoding !== 'base64url'
  ){
    throw new Error(t('web.directPayloadMalformed'))
  }
  const blob = new Blob([base64UrlToBytes(data)], {type: contentType})
  return URL.createObjectURL(blob)
}

async function decryptRelayFrame(payload){
  if(!relayState.codec){
    throw new Error(t('web.relayHandshakeWaiting'))
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
  const keySet = relayState.codec.keys[payload.k]
  if(!keySet){
    return null
  }
  if(!rememberReplay(keySet.pluginReplay, payload.n)){
    throw new Error(t('web.relayReplay'))
  }
  const blob = base64UrlToBytes(payload.ct)
  if(blob.length < 16){
    throw new Error(t('web.relayFrameTruncated'))
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
    keySet.stateKey,
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
    throw new Error(t('web.relayAssetMalformed'))
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
    const negotiated = await deriveRelayCodec(relayState.session, relayState.pairingSecret, hello)
    relayState.codec = storeNegotiatedCodec(relayState.codec, negotiated)
    if(relayState.socket && relayState.socket.readyState === WebSocket.OPEN){
      relayState.socket.send(JSON.stringify(negotiated.responseHello))
    }
    renderBanner()
    return
  }
  if(payload.type === 'error' && typeof payload.message === 'string'){
    throw new Error(localizedMessage(payload.message))
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
    throw new Error(localizedMessage(decrypted.payload.message))
  }
}

async function sendRelayCommand(commandName, payload = {}){
  if(!relayState.socket || relayState.socket.readyState !== WebSocket.OPEN || !relayState.codec){
    throw new Error(t('web.relayNotReady'))
  }
  const nonce = crypto.getRandomValues(new Uint8Array(12))
  const nonceText = bytesToBase64Url(nonce)
  const plaintext = utf8(JSON.stringify({command: commandName, ...payload}))
  const encrypted = await crypto.subtle.encrypt(
    {
      name: 'AES-GCM',
      iv: nonce,
      additionalData: frameAad(relayState.session, relayState.codec.activeKeyId, RELAY_KIND_COMMAND, nonceText),
      tagLength: 128,
    },
    relayState.codec.keys[relayState.codec.activeKeyId].commandKey,
    plaintext,
  )
  relayState.socket.send(JSON.stringify({
    type: 'frame',
    v: RELAY_PROTOCOL_VERSION,
    s: relayState.session,
    k: relayState.codec.activeKeyId,
    kind: RELAY_KIND_COMMAND,
    n: nonceText,
    ct: bytesToBase64Url(new Uint8Array(encrypted)),
  }))
}

async function connectRelay(){
  closeSocket()
  relayState.codec = null
  if(!relayState.session || !relayState.pairingSecret || !relayState.admissionToken){
    const message = t('web.relayOpenFullLink')
    showPlaceholderMessage(message)
    transportErrorMessage = message
    setConnectionPhase('offline')
    return
  }
  if(!hasWebCrypto()){
    const message = t('web.secureRelayUnsupported')
    showPlaceholderMessage(message)
    transportErrorMessage = message
    setConnectionPhase('offline')
    return
  }
  if(relayState.reconnectTimer){
    window.clearTimeout(relayState.reconnectTimer)
    relayState.reconnectTimer = null
  }

  showPlaceholderMessage(t('web.relayConnecting'))
  setConnectionPhase(hasEverConnected ? 'reconnecting' : 'connecting')
  const socket = new WebSocket(relaySocketUrl(relayState.session, relayState.admissionToken))
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
    showTransportError(t('web.relayConnectionFailed'))
  })
}

async function bootstrap(){
  await loadLocalization()
  setConnectionPhase('connecting')
  if(isRelayMode() || isSecureDirectMode() || isLocalFallbackMode()){
    if(!pairingSecret || !routeSession){
      throw new Error(
        isRelayMode()
          ? t('web.relayLinkRequired')
          : t('web.directLinkRequired')
      )
    }
    if((isRelayMode() || isSecureDirectMode()) && !hasWebCrypto()){
      throw new Error(t('web.webCryptoTransportUnsupported'))
    }
    if(isRelayMode() && !relayAdmissionToken){
      throw new Error(t('web.relayLinkRequired'))
    }
  }
  connectEvents()
}

bootstrap().catch(showTransportError)
