/* SPDX-FileCopyrightText: 2026 Bora Yarkın */
/* SPDX-License-Identifier: GPL-3.0-only */

(function () {
  'use strict'

  const plugin = window.Asc && window.Asc.plugin
  const eventNames = ['onSlideShowBegin', 'onSlideShowEnd', 'onSlideShowSlideChanged']
  const state = {
    editorVersion: 'Unknown',
    slideCount: null,
    editorSlideIndex: null,
    showSlideIndex: null,
    slideShowActive: false,
    notes: '',
    notesAvailable: null,
    destroyed: false
  }
  let snapshotRequestSequence = 0

  const elements = {
    status: document.getElementById('status'),
    editorVersion: document.getElementById('editor-version'),
    showState: document.getElementById('show-state'),
    currentSlide: document.getElementById('current-slide'),
    notesState: document.getElementById('notes-state'),
    notes: document.getElementById('notes'),
    goToSlide: document.getElementById('go-to-slide')
  }

  function setStatus(message) {
    elements.status.textContent = message
  }

  function formatSlide(index) {
    if (!Number.isInteger(index) || index < 0) {
      return 'Not reported'
    }
    if (!Number.isInteger(state.slideCount) || state.slideCount < 1) {
      return String(index + 1)
    }
    return `${index + 1} of ${state.slideCount}`
  }

  function render() {
    elements.editorVersion.textContent = state.editorVersion
    elements.showState.textContent = state.slideShowActive ? 'Running' : 'Not running'
    const activeIndex = state.slideShowActive ? state.showSlideIndex : state.editorSlideIndex
    elements.currentSlide.textContent = formatSlide(activeIndex)
    if (state.notesAvailable === null) {
      elements.notesState.textContent = 'Not read'
    } else if (!state.notesAvailable) {
      elements.notesState.textContent = 'No notes page'
    } else {
      elements.notesState.textContent = state.notes ? 'Available' : 'Available, empty'
    }
    elements.notes.textContent = state.notes
    elements.goToSlide.max = Number.isInteger(state.slideCount) ? String(state.slideCount) : ''
  }

  function executeMethod(name, params) {
    if (!plugin || state.destroyed) {
      setStatus('The editor plugin API is unavailable.')
      return false
    }

    try {
      const accepted = plugin.executeMethod(name, params || [])
      setStatus(accepted === false ? `${name} is unavailable in this editor.` : `${name} was sent to the editor.`)
      return accepted !== false
    } catch (_) {
      setStatus(`${name} could not be sent to the editor.`)
      return false
    }
  }

  function readPresentation(requestedSlideIndex) {
    if (!plugin || state.destroyed) {
      setStatus('The editor plugin API is unavailable.')
      return
    }

    window.Asc.scope.impressRemoteSlideIndex = Number.isInteger(requestedSlideIndex)
      ? requestedSlideIndex
      : null
    const requestSequence = ++snapshotRequestSequence

    setStatus('Reading slide count and presenter notes…')
    state.notes = ''
    state.notesAvailable = null
    render()
    try {
      plugin.callCommand(function () {
        try {
          const presentation = Api.GetPresentation()
          const slideCount = presentation.GetSlideCount()
          const editorSlideIndex = presentation.GetCurSlideIndex()
          const requestedIndex = Asc.scope.impressRemoteSlideIndex
          const notesIndex = Number.isInteger(requestedIndex) ? requestedIndex : editorSlideIndex
          let notes = ''
          let notesAvailable = null

          if (Number.isInteger(notesIndex) && notesIndex >= 0 && notesIndex < slideCount) {
            const slide = presentation.GetSlideByIndex(notesIndex)
            const notesPage = slide && slide.GetNotesPage()
            notesAvailable = Boolean(notesPage)
            notes = notesPage ? notesPage.GetBodyShapeText() || '' : ''
          }

          return JSON.stringify({
            slideCount: slideCount,
            editorSlideIndex: editorSlideIndex,
            notes: notes,
            notesAvailable: notesAvailable
          })
        } catch (_) {
          return JSON.stringify({ error: 'read_failed' })
        }
      }, false, false, function (result) {
        if (state.destroyed || requestSequence !== snapshotRequestSequence) {
          return
        }

        let snapshot
        try {
          snapshot = JSON.parse(result)
        } catch (_) {
          setStatus('The editor returned an unreadable presentation snapshot.')
          return
        }

        if (!snapshot || snapshot.error) {
          setStatus('The editor could not provide presentation state.')
          return
        }

        state.slideCount = Number.isInteger(snapshot.slideCount) ? snapshot.slideCount : null
        state.editorSlideIndex = Number.isInteger(snapshot.editorSlideIndex)
          ? snapshot.editorSlideIndex
          : null
        state.notes = typeof snapshot.notes === 'string' ? snapshot.notes : ''
        state.notesAvailable = typeof snapshot.notesAvailable === 'boolean'
          ? snapshot.notesAvailable
          : null
        render()
        setStatus('Presentation state read from the editor.')
      })
    } catch (_) {
      setStatus('The editor could not read presentation state.')
    }
  }

  function readEditorVersion() {
    try {
      const accepted = plugin.executeMethod('GetVersion', [], function (version) {
        if (state.destroyed) {
          return
        }
        state.editorVersion = typeof version === 'string' ? version : 'Unknown'
        render()
      })
      if (accepted === false) {
        setStatus('The editor version API is unavailable.')
      }
    } catch (_) {
      setStatus('The editor version could not be read.')
    }
  }

  function handleSlideShowBegin() {
    snapshotRequestSequence += 1
    state.slideShowActive = true
    state.showSlideIndex = null
    state.notes = ''
    state.notesAvailable = null
    render()
    setStatus('Slide show started; waiting for a slide-change event.')
  }

  function handleSlideShowEnd() {
    snapshotRequestSequence += 1
    state.slideShowActive = false
    state.showSlideIndex = null
    state.notes = ''
    state.notesAvailable = null
    render()
    readPresentation(null)
  }

  function handleSlideShowSlideChanged(data) {
    if (!data || !Number.isInteger(data.slideIndex) || data.slideIndex < 0) {
      setStatus('The editor sent an invalid slide-change event.')
      return
    }

    state.slideShowActive = true
    state.showSlideIndex = data.slideIndex
    render()
    readPresentation(data.slideIndex)
  }

  function bindControls() {
    document.querySelectorAll('[data-method]').forEach(function (button) {
      button.addEventListener('click', function () {
        executeMethod(button.dataset.method, [])
      })
    })

    document.getElementById('first-slide').addEventListener('click', function () {
      executeMethod('GoToSlideInSlideShow', [0])
    })

    document.getElementById('last-slide').addEventListener('click', function () {
      if (!Number.isInteger(state.slideCount) || state.slideCount < 1) {
        setStatus('Read presentation state before going to the last slide.')
        return
      }
      executeMethod('GoToSlideInSlideShow', [state.slideCount - 1])
    })

    document.getElementById('go-to-form').addEventListener('submit', function (event) {
      event.preventDefault()
      const slideNumber = Number(elements.goToSlide.value)
      if (!Number.isInteger(slideNumber) || slideNumber < 1) {
        setStatus('Enter a whole slide number greater than zero.')
        return
      }
      if (!Number.isInteger(state.slideCount) || state.slideCount < 1) {
        setStatus('Read presentation state before choosing a slide number.')
        return
      }
      if (slideNumber > state.slideCount) {
        setStatus(`Enter a slide number from 1 to ${state.slideCount}.`)
        return
      }
      executeMethod('GoToSlideInSlideShow', [slideNumber - 1])
    })

    document.getElementById('read-current-slide').addEventListener('click', function () {
      if (state.slideShowActive && !Number.isInteger(state.showSlideIndex)) {
        setStatus('Waiting for the editor to report the active slide.')
        return
      }
      readPresentation(state.slideShowActive ? state.showSlideIndex : null)
    })
  }

  function initialize() {
    if (!plugin) {
      setStatus('ONLYOFFICE plugin SDK did not load.')
      return
    }

    plugin.attachEditorEvent('onSlideShowBegin', handleSlideShowBegin)
    plugin.attachEditorEvent('onSlideShowEnd', handleSlideShowEnd)
    plugin.attachEditorEvent('onSlideShowSlideChanged', handleSlideShowSlideChanged)
    plugin.onDestroy = function () {
      state.destroyed = true
      snapshotRequestSequence += 1
      eventNames.forEach(function (eventName) {
        plugin.detachEditorEvent(eventName)
      })
    }
    bindControls()
    readEditorVersion()
    readPresentation(null)
  }

  if (plugin) {
    plugin.init = initialize
    plugin.button = function () {}
  } else {
    setStatus('ONLYOFFICE plugin SDK did not load.')
  }
})()
