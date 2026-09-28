/* SPDX-FileCopyrightText: 2026 Bora Yarkın */
/* SPDX-License-Identifier: GPL-3.0-only */

'use strict'

const statusNode = document.getElementById('status')
const quitButton = document.getElementById('quit')
const titleNode = document.getElementById('title')
let shutdownToken = ''
let messages = {
  title: 'Impress Remote Companion',
  opening: 'Opening…',
  disconnected: 'No presentation is connected.',
  connectError: 'Unable to connect to the companion.',
  closing: 'Closing companion…',
  closed: 'Companion closed.',
  closeError: 'Unable to close the companion. Try again.',
  quit: 'Quit companion',
}

function preferredLocale() {
  const languages = navigator.languages?.length ? navigator.languages : [navigator.language]
  return languages[0]?.toLowerCase().startsWith('tr') ? 'tr' : 'en'
}

async function loadMessages() {
  let locale = preferredLocale()
  try {
    const response = await fetch(`/localizations/${locale}.json`, { cache: 'no-store' })
    if (response.ok) {
      const localized = await response.json()
      if (Object.keys(messages).every(key => typeof localized[key] === 'string')) {
        messages = localized
      } else {
        locale = 'en'
      }
    } else {
      locale = 'en'
    }
  } catch (_error) {
    locale = 'en'
  }
  document.documentElement.lang = locale
  document.title = messages.title
  titleNode.textContent = messages.title
  statusNode.textContent = messages.opening
  quitButton.textContent = messages.quit
}

async function initialize() {
  await loadMessages()
  try {
    const response = await fetch('/api/session', { cache: 'no-store' })
    if (!response.ok) {
      throw new Error('session unavailable')
    }
    const session = await response.json()
    if (typeof session.shutdownToken !== 'string' || session.shutdownToken.length === 0) {
      throw new Error('invalid local session')
    }
    shutdownToken = session.shutdownToken
    statusNode.textContent = messages.disconnected
    quitButton.disabled = false
  } catch (_error) {
    statusNode.textContent = messages.connectError
  }
}

async function quitCompanion() {
  quitButton.disabled = true
  statusNode.textContent = messages.closing
  try {
    const response = await fetch('/api/shutdown', {
      method: 'POST',
      headers: { 'X-Companion-Token': shutdownToken },
    })
    if (!response.ok) {
      throw new Error('shutdown rejected')
    }
    statusNode.textContent = messages.closed
  } catch (_error) {
    statusNode.textContent = messages.closeError
    quitButton.disabled = false
  }
}

quitButton.addEventListener('click', () => {
  quitCompanion().catch(() => {
    statusNode.textContent = messages.closeError
    quitButton.disabled = false
  })
})

initialize().catch(() => {
  statusNode.textContent = messages.connectError
})
