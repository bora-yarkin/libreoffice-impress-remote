let lastState = null
let connectionPhase = 'connecting'
let hasEverConnected = false
let eventSource = null
let pollTimer = null
let lastImageUrl = ''
let lastNextImageUrl = ''
const nextImagePreload = new Image()

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
  if(connectionPhase === 'connecting'){
    target.textContent = 'Connecting to LibreOffice...'
    return
  }
  if(connectionPhase === 'reconnecting'){
    target.textContent = 'Connection lost. Reconnecting to LibreOffice...'
    return
  }
  if(connectionPhase === 'offline'){
    target.textContent = 'Remote is offline. Start it again from LibreOffice.'
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
    return 'Slide -- / --'
  }
  return `Slide ${currentSlide + 1} / ${slideCount}`
}

function updateSlideImage(state){
  const image = document.getElementById('slide-image')
  const placeholder = document.getElementById('slide-placeholder')
  const nextUrl = state.currentSlideImageUrl || ''
  if(!nextUrl){
    image.hidden = true
    placeholder.hidden = false
    lastImageUrl = ''
    return
  }
  if(nextUrl !== lastImageUrl){
    image.src = nextUrl
    lastImageUrl = nextUrl
  }
  image.hidden = false
  placeholder.hidden = true
}

function preloadNextSlide(state){
  const nextUrl = state.nextSlideImageUrl || ''
  if(!nextUrl){
    lastNextImageUrl = ''
    return
  }
  if(nextUrl !== lastNextImageUrl){
    nextImagePreload.src = nextUrl
    lastNextImageUrl = nextUrl
  }
}

function renderState(state){
  lastState = state
  const slideText = slideLabel(state.currentSlide, state.slideCount)
  document.querySelectorAll('.slide-label').forEach(node => {
    node.textContent = slideText
  })
  document.getElementById('current-title').textContent = state.currentTitle || 'Untitled slide'
  document.getElementById('notes').textContent = state.notes || 'No presenter notes detected.'
  updateSlideImage(state)
  preloadNextSlide(state)
  document.getElementById('prev-button').disabled = connectionPhase !== 'live' || !state.canGoPrevious
  document.getElementById('next-button').disabled = connectionPhase !== 'live' || !state.canGoNext
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

async function refreshStateSnapshot(){
  const state = await fetchJson('/api/state')
  hasEverConnected = true
  setConnectionPhase('live')
  renderState(state)
}

function connectEvents(){
  if(!('EventSource' in window)){
    startPollingFallback()
    return
  }
  if(eventSource){
    eventSource.close()
  }
  eventSource = new EventSource('/api/events')
  eventSource.addEventListener('open', () => {
    hasEverConnected = true
    setConnectionPhase('live')
  })
  eventSource.addEventListener('state', event => {
    hasEverConnected = true
    setConnectionPhase('live')
    renderState(JSON.parse(event.data))
  })
  eventSource.onerror = () => {
    setConnectionPhase(hasEverConnected ? 'reconnecting' : 'connecting')
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
  await fetchJson('/api/command', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({command: name, ...payload}),
  })
  if(!eventSource){
    await refreshStateSnapshot()
  }
}

document.querySelectorAll('[data-command]').forEach(button => {
  button.addEventListener('click', () => {
    command(button.dataset.command).catch(error => {
      document.getElementById('status').textContent = String(error)
      setConnectionPhase('offline')
    })
  })
})
document.getElementById('slide-image').addEventListener('error', () => {
  document.getElementById('slide-image').hidden = true
  document.getElementById('slide-placeholder').hidden = false
})

async function bootstrap(){
  setConnectionPhase('connecting')
  connectEvents()
}

bootstrap().catch(error => {
  document.getElementById('status').textContent = String(error)
  setConnectionPhase('offline')
})
