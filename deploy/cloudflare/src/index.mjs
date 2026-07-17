import { DurableObject } from "cloudflare:workers"

const RELAY_PROTOCOL_VERSION = 1
const MAX_PHONES_PER_SESSION = 8
const MAX_MESSAGE_BYTES = 8 * 1024 * 1024
const MAX_CACHED_PLUGIN_FRAMES = 6
const MAX_SESSION_ID_LENGTH = 128
const MAX_MESSAGES_PER_WINDOW = 120
const MESSAGE_WINDOW_MS = 10_000
const STATE_STORAGE_KEY = 'relay-state'
const PLUGIN_FRAME_KINDS = new Set(['state', 'asset', 'error'])
const PHONE_FRAME_KINDS = new Set(['command'])
const REPLAYABLE_PLUGIN_FRAME_KINDS = new Set(['state', 'asset', 'error'])
const SESSION_ID_PATTERN = /^[A-Za-z0-9_-]+$/

export default {
  async fetch(request, env){
    const url = new URL(request.url)
    if(url.pathname === '/health'){
      return Response.json({
        ok: true,
        runtime: 'cloudflare-workers',
        protocolVersion: RELAY_PROTOCOL_VERSION,
        sessionStatusEndpoint: '/api/session',
        admissionControl: true,
        structuredLogs: true,
        limits: {
          maxPhonesPerSession: MAX_PHONES_PER_SESSION,
          maxMessageBytes: MAX_MESSAGE_BYTES,
          maxCachedPluginFrames: MAX_CACHED_PLUGIN_FRAMES,
          maxSessionIdLength: MAX_SESSION_ID_LENGTH,
          maxMessagesPerWindow: MAX_MESSAGES_PER_WINDOW,
          messageWindowSeconds: MESSAGE_WINDOW_MS / 1000,
        },
      })
    }
    if(url.pathname === '/ws' || url.pathname === '/api/session'){
      const session = url.searchParams.get('session') || ''
      if(!session){
        return new Response('session is required', {status: 400})
      }
      if(session.length > MAX_SESSION_ID_LENGTH){
        return new Response('session id is too long', {status: 400})
      }
      if(!isValidSessionId(session)){
        return new Response('session id format is invalid', {status: 400})
      }
      if(url.pathname === '/ws'){
        const role = url.searchParams.get('role') || ''
        if(!['plugin', 'phone'].includes(role)){
          return new Response('role and session are required', {status: 400})
        }
      }
      const id = env.RELAY_ROOMS.idFromName(session)
      return env.RELAY_ROOMS.get(id).fetch(request)
    }
    return env.ASSETS.fetch(request)
  },
}

export class RelayRoom extends DurableObject {
  constructor(ctx, env){
    super(ctx, env)
    this.ctx = ctx
    this.env = env
    this.sessionId = ''
    this.admissionToken = ''
    this.createdAt = Date.now()
    this.lastSeen = Date.now()
    this.latestPluginHello = ''
    this.cachedPluginFrames = []
    this.connections = new Map()
    this.connectionWindows = new Map()
    this.plugin = null
    this.lastPluginDisconnectAt = 0
    this.metrics = defaultMetrics()
    this.ready = this.ctx.blockConcurrencyWhile(async () => {
      const snapshot = await this.ctx.storage.get(STATE_STORAGE_KEY)
      if(snapshot && typeof snapshot === 'object'){
        if(typeof snapshot.sessionId === 'string'){
          this.sessionId = snapshot.sessionId
        }
        if(typeof snapshot.admissionToken === 'string'){
          this.admissionToken = snapshot.admissionToken
        }
        if(typeof snapshot.createdAt === 'number'){
          this.createdAt = snapshot.createdAt
        }
        if(typeof snapshot.lastSeen === 'number'){
          this.lastSeen = snapshot.lastSeen
        }
        if(typeof snapshot.latestPluginHello === 'string'){
          this.latestPluginHello = snapshot.latestPluginHello
        }
        if(Array.isArray(snapshot.cachedPluginFrames)){
          this.cachedPluginFrames = snapshot.cachedPluginFrames.filter(value => typeof value === 'string')
        }
        if(typeof snapshot.lastPluginDisconnectAt === 'number'){
          this.lastPluginDisconnectAt = snapshot.lastPluginDisconnectAt
        }
        if(snapshot.metrics && typeof snapshot.metrics === 'object'){
          this.metrics = {...defaultMetrics(), ...snapshot.metrics}
        }
      }
      this.restoreConnections()
    })
  }

  restoreConnections(){
    this.connections.clear()
    this.connectionWindows.clear()
    this.plugin = null
    for(const socket of this.ctx.getWebSockets()){
      const attachment = socket.deserializeAttachment() ?? {}
      const role = attachment.role === 'plugin' ? 'plugin' : 'phone'
      const sessionId = typeof attachment.sessionId === 'string' ? attachment.sessionId : ''
      if(!this.sessionId && sessionId){
        this.sessionId = sessionId
      }
      this.connections.set(socket, {role})
      this.connectionWindows.set(socket, [])
      if(role === 'plugin'){
        this.plugin = socket
      }
    }
  }

  async fetch(request){
    await this.ready
    const url = new URL(request.url)
    if(url.pathname === '/api/session'){
      return this.sessionStatus(request)
    }
    if(url.pathname !== '/ws'){
      return new Response('Not found', {status: 404})
    }
    if(request.headers.get('Upgrade') !== 'websocket'){
      return new Response('Expected websocket upgrade', {status: 426})
    }
    const role = url.searchParams.get('role') || ''
    const session = url.searchParams.get('session') || ''
    const admissionToken = url.searchParams.get('a') || ''
    if(!['plugin', 'phone'].includes(role) || !session){
      return new Response('role and session are required', {status: 400})
    }
    if(this.sessionId && this.sessionId !== session){
      return new Response('session mismatch', {status: 400})
    }
    if(!this.authorizeAdmission(admissionToken)){
      this.countMetric('authRejects')
      logEvent('warn', 'relay.auth_reject', {role, session})
      return new Response('session admission token is invalid', {status: 403})
    }
    if(role === 'phone' && this.phoneCount() >= MAX_PHONES_PER_SESSION){
      this.countMetric('rateLimitRejects')
      return new Response('too many phones connected to this session', {status: 429})
    }

    const [client, server] = Object.values(new WebSocketPair())
    this.ctx.acceptWebSocket(server)
    server.serializeAttachment({role, sessionId: session})
    this.connections.set(server, {role})
    this.connectionWindows.set(server, [])
    this.sessionId = session
    this.lastSeen = Date.now()
    this.countMetric('websocketAccepts')
    logEvent('info', 'relay.ws_accept', {role, session})

    if(role === 'plugin'){
      if(this.plugin && this.plugin !== server){
        safeCloseSocket(this.plugin, 4000, 'plugin replaced')
      }
      this.plugin = server
      this.clearCachedPluginMessages()
    }else{
      if(this.latestPluginHello){
        safeSend(server, this.latestPluginHello)
      }
      for(const rawMessage of this.cachedPluginFrames){
        safeSend(server, rawMessage)
      }
    }
    await this.persistSnapshot()

    return new Response(null, {
      status: 101,
      webSocket: client,
    })
  }

  async sessionStatus(request){
    this.countMetric('sessionStatusRequests')
    const url = new URL(request.url)
    const session = url.searchParams.get('session') || ''
    const admissionToken = url.searchParams.get('a') || ''
    if(!this.sessionId || this.sessionId !== session){
      return new Response('session not found', {status: 404})
    }
    if(!this.authorizeAdmission(admissionToken)){
      this.countMetric('authRejects')
      return new Response('session admission token is invalid', {status: 403})
    }
    this.lastSeen = Date.now()
    await this.persistSnapshot()
    return Response.json({
      ok: true,
      session: this.snapshot(),
    })
  }

  async webSocketMessage(ws, message){
    await this.ready
    this.lastSeen = Date.now()
    const connection = this.connections.get(ws)
    if(!connection){
      return
    }
    if(typeof message !== 'string'){
      await this.rejectProtocol(ws, 'binary-unsupported', 'Relay messages must be UTF-8 JSON text.')
      return
    }
    if(utf8ByteLength(message) > MAX_MESSAGE_BYTES){
      await this.rejectProtocol(ws, 'message-too-large', 'Relay message exceeds the configured size limit.')
      return
    }
    if(!this.allowMessage(ws)){
      this.countMetric('rateLimitRejects')
      logEvent('warn', 'relay.rate_limit', {role: connection.role, session: this.sessionId})
      await this.rejectProtocol(ws, 'rate-limit', 'Relay connection exceeded the message rate limit.')
      return
    }
    this.countMetric('framesReceived')

    let envelope
    try{
      envelope = validateProtocolMessage(
        message,
        connection.role,
        this.sessionId,
        this.latestPluginHello,
      )
    }catch(error){
      if(error instanceof RelayProtocolViolation){
        this.countMetric('protocolRejects')
        logEvent('warn', 'relay.protocol_reject', {
          code: error.code,
          role: connection.role,
          session: this.sessionId,
        })
        await this.rejectProtocol(ws, error.code, error.message)
        return
      }
      throw error
    }

    const pluginStateChanged = this.recordPluginMetadata(connection.role, envelope, message)
    if(pluginStateChanged){
      await this.persistSnapshot()
    }

    const targets = connection.role === 'plugin'
      ? this.phoneSockets()
      : this.plugin ? [this.plugin] : []
    let forwarded = 0
    for(const target of targets){
      if(sendTextMessage(target, message)){
        forwarded += 1
        continue
      }
      this.countMetric('sendFailures')
      safeCloseSocket(target, 1011, 'relay send failure')
    }
    this.countMetric('framesForwarded', forwarded)
  }

  async webSocketClose(ws, code, reason){
    await this.ready
    await this.disconnectSocket(ws)
    safeCloseSocket(ws, code, reason)
  }

  async webSocketError(ws){
    await this.ready
    await this.disconnectSocket(ws)
    safeCloseSocket(ws, 1011, 'Relay websocket error')
  }

  phoneCount(){
    let count = 0
    for(const connection of this.connections.values()){
      if(connection.role === 'phone'){
        count += 1
      }
    }
    return count
  }

  phoneSockets(){
    const sockets = []
    for(const [socket, connection] of this.connections.entries()){
      if(connection.role === 'phone'){
        sockets.push(socket)
      }
    }
    return sockets
  }

  authorizeAdmission(admissionToken){
    if(!admissionToken){
      return false
    }
    if(!this.admissionToken){
      this.admissionToken = admissionToken
      return true
    }
    return this.admissionToken === admissionToken
  }

  allowMessage(ws){
    const now = Date.now()
    const threshold = now - MESSAGE_WINDOW_MS
    const bucket = this.connectionWindows.get(ws) ?? []
    bucket.push(now)
    while(bucket.length && bucket[0] < threshold){
      bucket.shift()
    }
    this.connectionWindows.set(ws, bucket)
    return bucket.length <= MAX_MESSAGES_PER_WINDOW
  }

  recordPluginMetadata(role, envelope, rawMessage){
    if(role !== 'plugin'){
      return false
    }
    if(envelope.messageType === 'hello'){
      this.latestPluginHello = rawMessage
      this.cachedPluginFrames = []
      return true
    }
    if(envelope.messageType !== 'frame' || !REPLAYABLE_PLUGIN_FRAME_KINDS.has(envelope.frameKind)){
      return false
    }
    this.cachedPluginFrames.push(rawMessage)
    while(this.cachedPluginFrames.length > MAX_CACHED_PLUGIN_FRAMES){
      this.cachedPluginFrames.shift()
    }
    return true
  }

  clearCachedPluginMessages(){
    this.latestPluginHello = ''
    this.cachedPluginFrames = []
  }

  async disconnectSocket(ws){
    const connection = this.connections.get(ws)
    if(!connection){
      return
    }
    this.connections.delete(ws)
    this.connectionWindows.delete(ws)
    this.countMetric('websocketCloses')
    logEvent('info', 'relay.ws_close', {role: connection.role, session: this.sessionId})
    if(connection.role === 'plugin' && this.plugin === ws){
      this.plugin = null
      this.clearCachedPluginMessages()
      this.lastPluginDisconnectAt = Date.now()
    }
    if(this.connections.size === 0){
      this.clearSessionState()
      await this.ctx.storage.deleteAll()
      return
    }
    await this.persistSnapshot()
  }

  clearSessionState(){
    this.sessionId = ''
    this.admissionToken = ''
    this.createdAt = Date.now()
    this.lastSeen = Date.now()
    this.latestPluginHello = ''
    this.cachedPluginFrames = []
    this.connectionWindows.clear()
    this.plugin = null
    this.lastPluginDisconnectAt = 0
    this.metrics = defaultMetrics()
  }

  snapshot(){
    const pluginConnected = !!(this.plugin && this.connections.has(this.plugin))
    return {
      session: this.sessionId,
      hasPlugin: pluginConnected,
      phones: this.phoneCount(),
      ageSeconds: roundNumber((Date.now() - this.createdAt) / 1000),
      hasHello: !!this.latestPluginHello,
      cachedPluginFrames: this.cachedPluginFrames.length,
      ready: pluginConnected && !!this.latestPluginHello,
      waitingForPlugin: !pluginConnected,
      admissionControlled: !!this.admissionToken,
      secondsSincePluginDisconnect: this.lastPluginDisconnectAt
        ? roundNumber((Date.now() - this.lastPluginDisconnectAt) / 1000)
        : null,
      metrics: {...this.metrics},
    }
  }

  countMetric(name, amount = 1){
    this.metrics[name] = (this.metrics[name] ?? 0) + amount
  }

  async rejectProtocol(ws, code, message){
    try{
      safeSend(ws, encodeErrorMessage(this.sessionId, code, message))
    }catch(_error){
    }
    safeCloseSocket(ws, 1008, message.slice(0, 120))
  }

  async persistSnapshot(){
    if(!this.sessionId){
      return
    }
    await this.ctx.storage.put(STATE_STORAGE_KEY, {
      sessionId: this.sessionId,
      admissionToken: this.admissionToken,
      createdAt: this.createdAt,
      lastSeen: this.lastSeen,
      latestPluginHello: this.latestPluginHello,
      cachedPluginFrames: this.cachedPluginFrames,
      lastPluginDisconnectAt: this.lastPluginDisconnectAt,
      metrics: this.metrics,
    })
  }
}

class RelayProtocolViolation extends Error {
  constructor(code, message){
    super(message)
    this.code = code
    this.message = message
  }
}

function validateProtocolMessage(rawMessage, role, sessionId, latestPluginHello){
  let payload
  try{
    payload = JSON.parse(rawMessage)
  }catch(error){
    throw new RelayProtocolViolation('invalid-json', 'Relay messages must be valid JSON.')
  }
  if(!payload || typeof payload !== 'object' || Array.isArray(payload)){
    throw new RelayProtocolViolation('invalid-json', 'Relay messages must be JSON objects.')
  }

  if(!['hello', 'frame', 'error'].includes(payload.type)){
    throw new RelayProtocolViolation('invalid-type', 'Relay messages must use hello, frame, or error envelopes.')
  }
  if(typeof payload.v !== 'number' || payload.v !== RELAY_PROTOCOL_VERSION){
    throw new RelayProtocolViolation('unsupported-version', 'Unsupported relay protocol version.')
  }
  if(typeof payload.s !== 'string' || payload.s !== sessionId){
    throw new RelayProtocolViolation('session-mismatch', 'Relay message is bound to another session.')
  }

  if(payload.type === 'hello'){
    if(role !== 'plugin'){
      throw new RelayProtocolViolation('invalid-role', 'Only the plugin may publish relay hello messages.')
    }
    const keyId = requiredString(payload, 'k', 'Relay hello is missing a key id.')
    requiredString(payload, 'nonce', 'Relay hello is missing a plugin nonce.')
    return {messageType: 'hello', keyId, frameKind: ''}
  }

  if(payload.type === 'error'){
    if(role !== 'plugin'){
      throw new RelayProtocolViolation('invalid-role', 'Only the plugin may publish plaintext relay errors.')
    }
    requiredString(payload, 'code', 'Relay error messages need an error code.')
    requiredString(payload, 'message', 'Relay error messages need an error message.')
    return {messageType: 'error', keyId: '', frameKind: ''}
  }

  const keyId = requiredString(payload, 'k', 'Encrypted relay frames need a key id.')
  const frameKind = requiredString(payload, 'kind', 'Encrypted relay frames need a kind.')
  requiredString(payload, 'n', 'Encrypted relay frames need a nonce.')
  requiredString(payload, 'ct', 'Encrypted relay frames need ciphertext.')

  const allowedKinds = role === 'plugin' ? PLUGIN_FRAME_KINDS : PHONE_FRAME_KINDS
  if(!allowedKinds.has(frameKind)){
    throw new RelayProtocolViolation('invalid-kind', 'Encrypted relay frame kind is not allowed for this role.')
  }

  if(role === 'plugin'){
    const activeKeyId = helloKeyId(latestPluginHello)
    if(!activeKeyId){
      throw new RelayProtocolViolation('missing-hello', 'The plugin must publish a relay hello before encrypted frames.')
    }
    if(keyId !== activeKeyId){
      throw new RelayProtocolViolation('invalid-key', 'Plugin frame key id does not match the active relay hello.')
    }
  }else if(!latestPluginHello){
    throw new RelayProtocolViolation('missing-hello', 'The relay plugin is not ready for encrypted commands yet.')
  }

  return {messageType: 'frame', keyId, frameKind}
}

function requiredString(payload, key, message){
  const value = payload[key]
  if(typeof value !== 'string' || !value){
    throw new RelayProtocolViolation('invalid-envelope', message)
  }
  return value
}

function helloKeyId(rawHello){
  if(!rawHello){
    return ''
  }
  try{
    const payload = JSON.parse(rawHello)
    return typeof payload.k === 'string' ? payload.k : ''
  }catch(_error){
    return ''
  }
}

function encodeErrorMessage(sessionId, code, message){
  return JSON.stringify({
    type: 'error',
    v: RELAY_PROTOCOL_VERSION,
    s: sessionId,
    code,
    message,
  })
}

function defaultMetrics(){
  return {
    websocketAccepts: 0,
    websocketCloses: 0,
    framesReceived: 0,
    framesForwarded: 0,
    protocolRejects: 0,
    authRejects: 0,
    rateLimitRejects: 0,
    sendFailures: 0,
    sessionStatusRequests: 0,
  }
}

function logEvent(level, event, fields = {}){
  const payload = JSON.stringify({event, ...fields})
  if(level === 'warn'){
    console.warn(payload)
    return
  }
  console.log(payload)
}

function roundNumber(value){
  return Math.round(value * 1000) / 1000
}

function isValidSessionId(sessionId){
  return !!sessionId && SESSION_ID_PATTERN.test(sessionId)
}

function utf8ByteLength(text){
  return new TextEncoder().encode(text).length
}

function safeSend(socket, payload){
  try{
    socket.send(payload)
    return true
  }catch(_error){
    return false
  }
}

function safeCloseSocket(socket, code, reason){
  try{
    socket.close(code, reason)
  }catch(_error){
  }
}

function sendTextMessage(target, rawMessage){
  return safeSend(target, rawMessage)
}
