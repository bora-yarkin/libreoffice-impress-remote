function slideLabel(currentSlide, slideCount){
  if(!slideCount){
    return 'Slide -- / --';
  }
  return `Slide ${currentSlide + 1} / ${slideCount}`;
}

function hashParams(){
  return new URLSearchParams(window.location.hash.replace(/^#/, ''));
}

function relaySocketUrl(session){
  const url = new URL('/ws', window.location.href);
  url.protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  url.searchParams.set('role', 'phone');
  url.searchParams.set('session', session);
  return url.toString();
}

const state = {
  session: '',
  socket: null,
  reconnectTimer: null,
};

function setStatus(message){
  document.getElementById('status').textContent = message;
}

function setSocketState(message){
  document.getElementById('socket-state').textContent = message;
}

function renderState(payload){
  setStatus(payload.statusMessage || (payload.running ? 'Presentation running' : 'Connected to relay.'));
  document.getElementById('slide').textContent = slideLabel(payload.currentSlide, payload.slideCount);
  document.getElementById('current-title').textContent = payload.currentTitle || 'Untitled slide';
  document.getElementById('notes').textContent = payload.notes || 'No presenter notes detected.';

  const nextSlide = typeof payload.nextSlide === 'number' ? `Slide ${payload.nextSlide + 1}` : 'No next slide';
  document.getElementById('next-slide').textContent = nextSlide;
  document.getElementById('next-title').textContent = payload.nextTitle || 'No next slide';
  document.getElementById('next-preview').textContent = payload.nextPreview || 'The current slide is the last slide in the deck.';
}

function updateHash(session){
  const params = new URLSearchParams();
  if(session){
    params.set('mode', 'relay');
    params.set('s', session);
  }
  window.location.hash = params.toString();
}

function closeSocket(){
  if(state.socket){
    state.socket.onclose = null;
    state.socket.close();
    state.socket = null;
  }
}

function scheduleReconnect(){
  if(state.reconnectTimer || !state.session){
    return;
  }
  state.reconnectTimer = window.setTimeout(() => {
    state.reconnectTimer = null;
    connectRelay();
  }, 1500);
}

function connectRelay(){
  closeSocket();
  if(!state.session){
    setStatus('Enter a session code to connect.');
    setSocketState('Idle');
    return;
  }

  setStatus('Connecting to relay...');
  setSocketState('Connecting');
  const socket = new WebSocket(relaySocketUrl(state.session));
  state.socket = socket;

  socket.addEventListener('open', () => {
    setStatus('Connected to relay. Waiting for presentation state...');
    setSocketState('Connected');
  });

  socket.addEventListener('message', event => {
    try{
      const payload = JSON.parse(event.data);
      if(payload.type === 'state' && payload.state){
        renderState(payload.state);
      }
    }catch(error){
      setStatus(String(error));
    }
  });

  socket.addEventListener('close', () => {
    setSocketState('Disconnected');
    setStatus('Relay connection lost. Reconnecting...');
    scheduleReconnect();
  });

  socket.addEventListener('error', () => {
    setSocketState('Error');
    setStatus('Relay connection failed.');
  });
}

function sendCommand(command, payload = {}){
  if(!state.socket || state.socket.readyState !== WebSocket.OPEN){
    return;
  }
  state.socket.send(JSON.stringify({type: 'command', command, ...payload}));
}

document.getElementById('relay-origin').textContent = window.location.origin;
document.querySelectorAll('[data-command]').forEach(button => {
  button.addEventListener('click', () => sendCommand(button.dataset.command));
});

document.getElementById('goto-form').addEventListener('submit', event => {
  event.preventDefault();
  const input = document.getElementById('goto-slide');
  const value = Number.parseInt(input.value, 10);
  if(Number.isNaN(value) || value < 1){
    return;
  }
  sendCommand('goto_slide', {index: value - 1});
});

document.getElementById('session-form').addEventListener('submit', event => {
  event.preventDefault();
  const nextSession = document.getElementById('session-input').value.trim();
  if(!nextSession){
    return;
  }
  state.session = nextSession;
  document.getElementById('session-display').textContent = nextSession;
  updateHash(nextSession);
  connectRelay();
});

const initialSession = hashParams().get('s') || '';
state.session = initialSession;
document.getElementById('session-input').value = initialSession;
document.getElementById('session-display').textContent = initialSession || '----------';
connectRelay();
