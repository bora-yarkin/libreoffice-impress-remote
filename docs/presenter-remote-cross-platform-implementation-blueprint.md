# Cross-Platform Presenter Remote Expansion Blueprint

**Target repository:** `bora-yarkin/libreoffice-impress-remote`  
**Prepared:** 2026-07-17  
**Repository snapshot used:** current `main`, whose protocol and roadmap identify version `0.3.5`  
**Purpose:** preserve an implementation plan for PowerPoint desktop, PowerPoint for the web, Google Slides, and other browser-based presentation suites after the LibreOffice extension and relay server are complete.

---

## 1. Executive decision

Do not convert the LibreOffice `.oxt` package into another extension format.

Keep one product, phone UI, relay protocol, and security model, but implement separate presentation hosts:

1. **LibreOffice Impress**
   - Existing Python/UNO `.oxt`
   - Local LAN, direct IPv6, and relay

2. **PowerPoint for Windows**
   - Thin VSTO add-in in C#
   - Shared packaged helper for networking, crypto, phone UI, pairing, and relay
   - Full or near-full slideshow-control parity

3. **PowerPoint for macOS**
   - `.ppam` VBA add-in for PowerPoint events, notes, state, and slide export
   - Signed helper application for networking and trusted input
   - A mandatory proof-of-concept gate because Office sandboxing and helper-to-PowerPoint command execution are the difficult boundary

4. **Browser host**
   - Chromium Manifest V3 extension
   - Firefox WebExtension build
   - Site-specific adapters for Google Slides, PowerPoint for the web, and other suites
   - Relay-first; optional native helper for local-LAN mode

5. **Optional Office.js companion**
   - Used only for reliable document data such as slide images
   - Not the primary slideshow controller because the supported PowerPoint JavaScript API does not expose the full running-slide-show surface this project requires

The reusable product boundary must be the versioned encrypted protocol, not LibreOffice Python classes.

---

## 2. Completion gates before starting the ports

Do not begin these ports while the core contract is changing rapidly.

### Gate A: LibreOffice local mode is stable

Required:

- Installation, start, QR scan, next/previous, notes, previews, reconnect, and shutdown work reliably.
- Local endpoint tests cover state, commands, events, and assets.
- State transitions are stable when:
  - no presentation is open;
  - a presentation opens or closes;
  - slide show starts or ends;
  - the user navigates manually;
  - the phone disconnects and reconnects.

### Gate B: Relay server is operationally stable

Required:

- Session matching, reconnect, cleanup, backpressure, and limits are tested.
- TLS deployment is documented.
- Relay does not decrypt state, notes, commands, or slide images.
- Health checks and content-free diagnostics exist.
- Phone reconnect does not force a desktop-host restart.

### Gate C: Protocol is implementation-ready

Required:

- The protocol document is authoritative.
- JSON schemas exist for `hello`, `frame`, transport `error`, state, command, and asset payloads.
- Golden interoperability vectors exist for:
  - HKDF inputs and output;
  - state and command keys;
  - AES-GCM nonce, AAD, ciphertext, and tag;
  - replay rejection;
  - rotation;
  - previous-key receive window.
- Python, TypeScript, and C# implementations consume the same vectors.
- Unknown additive state fields are permitted.
- Breaking changes require a new protocol version.

### Gate D: Phone UI is host-neutral

Remove product-specific text such as “Connecting to LibreOffice” from shared frontend code.

The phone receives host metadata:

```json
{
  "host": {
    "family": "libreoffice-impress",
    "displayName": "LibreOffice Impress",
    "platform": "macos",
    "adapterVersion": "1.0.0"
  }
}
```

### Gate E: Capability negotiation exists

Add an optional capabilities object:

```json
{
  "capabilities": {
    "startPresentation": true,
    "startFromFirstSlide": true,
    "endPresentation": true,
    "nextEffect": true,
    "previousEffect": true,
    "nextSlide": true,
    "previousSlide": true,
    "goToSlide": true,
    "pause": true,
    "resume": true,
    "blankScreen": true,
    "currentPreview": true,
    "nextPreview": true,
    "speakerNotes": true,
    "manualNavigationTracking": true
  }
}
```

The phone hides or disables unsupported controls.

---

## 3. Existing repository boundaries

Current architecture:

```text
Local:
Phone browser -> laptop local IP -> LibreOffice extension

Relay:
Phone browser -> Python relay UI/WS <- LibreOffice extension relay client

Direct IPv6:
Phone browser -> laptop global IPv6 -> LibreOffice extension
```

LibreOffice-specific areas:

```text
extension/python/impress_remote/component.py
extension/python/impress_remote/controller.py
extension/python/impress_remote/notes.py
extension/python/impress_remote/preview.py
extension/python/impress_remote/office_ui.py
extension/python/impress_remote/config.py
extension/META-INF/
extension/Settings.xcs
extension/Settings.xcu
```

Conceptually reusable areas:

```text
extension/python/impress_remote/crypto.py
extension/python/impress_remote/protocol.py
extension/python/impress_remote/relay_client.py
extension/python/impress_remote/network.py
extension/python/impress_remote/local_server.py
extension/python/impress_remote/qr.py
extension/web/
server/
```

Refactor reusable modules so they receive a generic presentation host rather than constructing `ImpressController`.

---

## 4. Current protocol contract

Current encrypted profile:

```text
Protocol version: 1
Key derivation: HKDF-SHA256
Encryption: AES-256-GCM
Bootstrap: pairing secret from QR/manual-link fragment
State direction: desktop host -> phone
Command direction: phone -> desktop host
Asset direction: desktop host -> phone
Rotation: desktop-host driven
Replay cache: per direction and per key
```

Pairing fragment:

```text
#mode=<route>&s=<session-id>&k=<pairing-secret>
```

`hello`:

```json
{
  "type": "hello",
  "v": 1,
  "s": "session-id",
  "k": "key-id",
  "nonce": "plugin-nonce",
  "suite": "HKDF-SHA256+AES-256-GCM+PSK",
  "rotate": 300,
  "features": ["state", "command", "error", "asset"]
}
```

Encrypted frame:

```json
{
  "type": "frame",
  "v": 1,
  "s": "session-id",
  "k": "key-id",
  "kind": "state",
  "n": "96-bit-nonce-base64url",
  "ct": "ciphertext-plus-128-bit-tag-base64url"
}
```

Key derivation:

```text
salt = "impress-remote-relay/v1" || 0x00 || session-id
info = "relay-keys" || 0x00 || key-id || 0x00 || plugin-nonce
material = HKDF-SHA256(pairing-secret, salt, info, 64 bytes)
state-key = material[0:32]
command-key = material[32:64]
```

AAD:

```json
{"kind":"state","k":"key-id","n":"nonce","s":"session-id","v":1}
```

Encrypted kinds:

```text
state
command
error
asset
```

### Existing state payload

```json
{
  "running": true,
  "presentationActive": true,
  "presentationPaused": false,
  "presentationBlanked": false,
  "documentKind": "impress",
  "statusMessage": "Presentation running",
  "currentSlide": 3,
  "slideCount": 20,
  "currentTitle": "Architecture",
  "notes": "Explain the transport boundary.",
  "nextSlide": 4,
  "nextTitle": "Protocol",
  "nextPreview": "Protocol | HKDF | AES-GCM",
  "canGoPrevious": true,
  "canGoNext": true,
  "remainingSlides": 16,
  "atEndOfDeck": false,
  "elapsedSeconds": 140,
  "currentSlideImageRevision": "opaque-current-revision",
  "nextSlideImageRevision": "opaque-next-revision",
  "currentSlideImageUrl": "/api/slide/current?rev=...",
  "nextSlideImageUrl": "/api/slide/next?rev=..."
}
```

Relay image URLs remain empty; image bytes arrive as encrypted assets.

Asset:

```json
{
  "contentType": "image/png",
  "encoding": "base64url",
  "data": "...",
  "slot": "current",
  "revision": "opaque-render-revision"
}
```

Current command concepts:

```text
start_presentation
start_presentation_from_first_slide
end_presentation
next_effect
previous_effect
next_slide
previous_slide
goto_slide
pause_presentation
resume_presentation
blank_screen
goto_last_slide
```

`goto_slide.index` is zero-based in the protocol.

### Recommended additive state fields

```json
{
  "stateSchema": 1,
  "host": {
    "family": "powerpoint-windows",
    "displayName": "Microsoft PowerPoint",
    "platform": "windows",
    "hostVersion": "16.0",
    "adapterVersion": "1.0.0"
  },
  "presentation": {
    "id": "opaque-host-specific-id",
    "title": "Quarterly Review"
  },
  "currentSlideId": "opaque-slide-id",
  "nextSlideId": "opaque-slide-id",
  "capabilities": {}
}
```

Never relay local paths, document URLs, account IDs, OAuth tokens, or usernames.

### Optional command correlation

```json
{
  "command": "next_slide",
  "commandId": "random-request-id"
}
```

Encrypted error:

```json
{
  "code": "unsupported-command",
  "message": "This host cannot pause a running show.",
  "commandId": "random-request-id"
}
```

---

## 5. Canonical host interface

```typescript
export interface PresentationHost {
  readonly identity: HostIdentity;

  getCapabilities(): Promise<PresentationCapabilities>;
  getState(): Promise<PresentationState>;
  execute(command: PresentationCommand): Promise<CommandResult>;
  getAsset(request: AssetRequest): Promise<PresentationAsset | null>;

  start(onEvent: (event: HostEvent) => void): Promise<void>;
  stop(): Promise<void>;
}
```

```typescript
export interface HostIdentity {
  family:
    | "libreoffice-impress"
    | "powerpoint-windows"
    | "powerpoint-macos"
    | "google-slides"
    | "powerpoint-web"
    | "onlyoffice"
    | "zoho-show"
    | "pitch"
    | "canva"
    | "prezi"
    | "generic-web";
  displayName: string;
  platform: "windows" | "macos" | "linux" | "web";
  hostVersion?: string;
  adapterVersion: string;
}
```

```typescript
export interface PresentationCapabilities {
  startPresentation: boolean;
  startFromFirstSlide: boolean;
  endPresentation: boolean;
  nextEffect: boolean;
  previousEffect: boolean;
  nextSlide: boolean;
  previousSlide: boolean;
  goToSlide: boolean;
  pause: boolean;
  resume: boolean;
  blankScreen: boolean;
  currentPreview: boolean;
  nextPreview: boolean;
  speakerNotes: boolean;
  manualNavigationTracking: boolean;
}
```

```typescript
export type PresentationCommand =
  | { command: "start_presentation"; commandId?: string }
  | { command: "start_presentation_from_first_slide"; commandId?: string }
  | { command: "end_presentation"; commandId?: string }
  | { command: "next_effect"; commandId?: string }
  | { command: "previous_effect"; commandId?: string }
  | { command: "next_slide"; commandId?: string }
  | { command: "previous_slide"; commandId?: string }
  | { command: "goto_slide"; index: number; commandId?: string }
  | { command: "pause_presentation"; commandId?: string }
  | { command: "resume_presentation"; commandId?: string }
  | { command: "blank_screen"; commandId?: string }
  | { command: "goto_last_slide"; commandId?: string };
```

Python extraction:

```python
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class HostCommand:
    command: str
    index: int | None = None
    command_id: str = ""


@dataclass(frozen=True)
class HostAsset:
    content_type: str
    data: bytes
    slot: str
    revision: str


class PresentationHost(Protocol):
    def capabilities(self) -> dict[str, bool]:
        ...

    def state_payload(self) -> dict[str, object]:
        ...

    def execute(self, command: HostCommand) -> None:
        ...

    def asset(self, slot: str, revision: str) -> HostAsset | None:
        ...
```

---

## 6. Recommended repository structure

A monorepo is preferable because protocol, phone UI, vectors, and relay must remain synchronized.

```text
presenter-remote/
├── docs/
│   ├── architecture/
│   ├── protocol/
│   ├── security/
│   ├── platforms/
│   └── deployment/
├── shared/
│   ├── protocol/
│   │   ├── protocol.md
│   │   ├── schemas/
│   │   └── test-vectors/
│   ├── web/
│   │   ├── phone/
│   │   └── pairing/
│   └── python/
│       └── presenter_remote_core/
│           ├── crypto.py
│           ├── protocol.py
│           ├── relay_client.py
│           ├── local_server.py
│           ├── network.py
│           ├── qr.py
│           ├── host.py
│           └── runtime.py
├── hosts/
│   ├── libreoffice/
│   ├── powerpoint-windows/
│   ├── powerpoint-macos/
│   └── browser-extension/
├── companion/
│   ├── python/
│   ├── packaging/
│   └── tests/
└── server/
```

Rename the repository only after the LibreOffice release, or create an umbrella repository and preserve the existing project as the LibreOffice host.

---

## 7. Shared companion process

The companion owns:

- session and pairing-secret generation;
- encrypted codec and rotation;
- relay WebSocket;
- local HTTP server;
- direct IPv6 listener, if retained;
- phone assets;
- QR generation;
- host-independent settings;
- encrypted asset forwarding;
- bridge authentication;
- lifecycle and diagnostics.

Office add-ins own:

- presentation API access;
- slideshow state;
- command execution;
- notes;
- slide export;
- native UI entry points;
- office events.

```text
Phone browser/PWA
        |
 local or relay
        |
Presenter Remote Companion
 protocol / crypto / relay / local server / QR / UI
        |
 authenticated local bridge
        |
Office host adapter
        |
PowerPoint
```

### Bridge security

Never expose an unauthenticated localhost command endpoint.

Use:

- loopback only;
- random port;
- random 256-bit token;
- per-launch nonce;
- versioned bridge protocol;
- short expiration;
- strict request and asset limits;
- no permissive CORS;
- no trust based only on `Origin`;
- current-user ownership checks where possible.

Bootstrap descriptor:

```json
{
  "version": 1,
  "pid": 12345,
  "port": 48192,
  "token": "base64url-random-32-bytes",
  "expiresAt": "2026-07-17T12:00:00Z"
}
```

Suggested messages:

```json
{
  "type": "host.register",
  "bridgeVersion": 1,
  "host": {
    "family": "powerpoint-windows",
    "displayName": "Microsoft PowerPoint",
    "platform": "windows",
    "adapterVersion": "1.0.0"
  },
  "capabilities": {}
}
```

```json
{
  "type": "host.command",
  "requestId": "random-id",
  "command": {
    "command": "next_slide"
  }
}
```

```json
{
  "type": "host.commandResult",
  "requestId": "random-id",
  "ok": true
}
```

Windows should prefer a user-restricted named pipe. macOS VBA can push state through `AppleScriptTask` to a token-protected loopback endpoint.
---

## 8. PowerPoint for Windows

## 8.1 Architecture

```text
PowerPoint
  └── VSTO add-in
        ├── PowerPoint object-model adapter
        ├── slide-show events
        ├── notes extraction
        ├── slide export
        ├── Ribbon controls
        └── authenticated bridge
              └── packaged companion
                    ├── local HTTP/SSE
                    ├── relay WebSocket
                    ├── crypto
                    ├── QR and pairing
                    └── shared phone UI
```

VSTO is Windows-only but exposes the required native PowerPoint object model.

Projects:

```text
PresenterRemote.PowerPoint.sln
├── PresenterRemote.PowerPoint.AddIn
├── PresenterRemote.PowerPoint.Bridge
├── PresenterRemote.PowerPoint.Contracts
├── PresenterRemote.PowerPoint.Tests
└── PresenterRemote.PowerPoint.IntegrationTests
```

Recommended choices:

- VSTO project: framework supported by the selected Visual Studio Office template.
- Companion: bundled Python application initially, so users do not install Python.
- IPC: named pipe with current-user ACL.
- Logs: rolling, without slide content or notes.

## 8.2 Adapter contract

```csharp
public interface IPresentationHost
{
    HostIdentity Identity { get; }
    PresentationCapabilities GetCapabilities();
    PresentationState GetState();
    CommandResult Execute(PresentationCommand command);
    PresentationAsset? GetAsset(string slot, string revision);
}
```

Reference implementation skeleton:

```csharp
using System;
using System.IO;
using Microsoft.Office.Core;
using PowerPoint = Microsoft.Office.Interop.PowerPoint;

public sealed class PowerPointPresentationHost : IPresentationHost
{
    private readonly PowerPoint.Application _application;
    private readonly object _sync = new object();

    public PowerPointPresentationHost(PowerPoint.Application application)
    {
        _application = application
            ?? throw new ArgumentNullException(nameof(application));
    }

    public HostIdentity Identity => new HostIdentity
    {
        Family = "powerpoint-windows",
        DisplayName = "Microsoft PowerPoint",
        Platform = "windows",
        HostVersion = _application.Version,
        AdapterVersion = "1.0.0"
    };

    public PresentationCapabilities GetCapabilities()
    {
        return new PresentationCapabilities
        {
            StartPresentation = true,
            StartFromFirstSlide = true,
            EndPresentation = true,
            NextEffect = true,
            PreviousEffect = true,
            NextSlide = true,
            PreviousSlide = true,
            GoToSlide = true,
            Pause = true,
            Resume = true,
            BlankScreen = true,
            CurrentPreview = true,
            NextPreview = true,
            SpeakerNotes = true,
            ManualNavigationTracking = true
        };
    }

    public PresentationState GetState()
    {
        lock (_sync)
        {
            PowerPoint.Presentation presentation = TryGetPresentation();

            if (presentation == null)
            {
                return PresentationState.Empty(
                    "none",
                    "Open a PowerPoint presentation to use the remote."
                );
            }

            PowerPoint.SlideShowView view = TryGetSlideShowView();
            int slideCount = presentation.Slides.Count;
            bool running = view != null;

            int currentOneBased = running
                ? view.CurrentShowPosition
                : GetEditingSlideNumber();

            int currentZeroBased = Clamp(
                currentOneBased - 1,
                0,
                Math.Max(slideCount - 1, 0)
            );

            int? nextZeroBased = currentZeroBased + 1 < slideCount
                ? currentZeroBased + 1
                : (int?)null;

            PowerPoint.Slide currentSlide =
                presentation.Slides[currentZeroBased + 1];

            PowerPoint.Slide nextSlide = nextZeroBased.HasValue
                ? presentation.Slides[nextZeroBased.Value + 1]
                : null;

            string notes = ExtractNotes(currentSlide);
            string title = ExtractTitle(currentSlide);
            string nextTitle = nextSlide == null
                ? string.Empty
                : ExtractTitle(nextSlide);

            return new PresentationState
            {
                Running = running,
                PresentationActive = running,
                PresentationPaused =
                    running
                    && view.State ==
                        PowerPoint.PpSlideShowState.ppSlideShowPaused,
                PresentationBlanked =
                    running && IsBlankState(view.State),
                DocumentKind = "powerpoint",
                StatusMessage =
                    running
                    ? "Presentation running"
                    : "Presentation ready",
                CurrentSlide = currentZeroBased,
                SlideCount = slideCount,
                CurrentTitle = title,
                Notes = notes,
                NextSlide = nextZeroBased,
                NextTitle = nextTitle,
                CanGoPrevious = currentZeroBased > 0,
                CanGoNext = nextZeroBased.HasValue,
                RemainingSlides = Math.Max(
                    slideCount - currentZeroBased - 1,
                    0
                ),
                AtEndOfDeck =
                    slideCount > 0 && !nextZeroBased.HasValue,
                ElapsedSeconds = 0,
                CurrentSlideImageRevision =
                    BuildRevision(currentSlide, title, notes),
                NextSlideImageRevision =
                    nextSlide == null
                    ? string.Empty
                    : BuildRevision(
                        nextSlide,
                        nextTitle,
                        string.Empty
                    )
            };
        }
    }

    public CommandResult Execute(PresentationCommand command)
    {
        lock (_sync)
        {
            switch (command.Command)
            {
                case "start_presentation":
                    RequirePresentation()
                        .SlideShowSettings
                        .Run();
                    return CommandResult.Success();

                case "start_presentation_from_first_slide":
                    PowerPoint.Presentation presentation =
                        RequirePresentation();

                    presentation.SlideShowSettings.RangeType =
                        PowerPoint.PpSlideShowRangeType.ppShowAll;

                    presentation.SlideShowSettings.Run();
                    return CommandResult.Success();

                case "end_presentation":
                    RequireSlideShowView().Exit();
                    return CommandResult.Success();

                case "next_effect":
                    RequireSlideShowView().Next();
                    return CommandResult.Success();

                case "previous_effect":
                    RequireSlideShowView().Previous();
                    return CommandResult.Success();

                case "next_slide":
                    GoRelativeSlide(1);
                    return CommandResult.Success();

                case "previous_slide":
                    GoRelativeSlide(-1);
                    return CommandResult.Success();

                case "goto_slide":
                    if (!command.Index.HasValue)
                    {
                        return CommandResult.Failure(
                            "invalid-command",
                            "goto_slide requires index."
                        );
                    }

                    RequireSlideShowView()
                        .GotoSlide(command.Index.Value + 1);

                    return CommandResult.Success();

                case "goto_last_slide":
                    PowerPoint.Presentation active =
                        RequirePresentation();

                    RequireSlideShowView()
                        .GotoSlide(active.Slides.Count);

                    return CommandResult.Success();

                case "pause_presentation":
                    RequireSlideShowView().State =
                        PowerPoint.PpSlideShowState.ppSlideShowPaused;

                    return CommandResult.Success();

                case "resume_presentation":
                    RequireSlideShowView().State =
                        PowerPoint.PpSlideShowState.ppSlideShowRunning;

                    return CommandResult.Success();

                case "blank_screen":
                    ToggleBlackScreen();
                    return CommandResult.Success();

                default:
                    return CommandResult.Failure(
                        "unsupported-command",
                        "Unsupported command: " + command.Command
                    );
            }
        }
    }

    public PresentationAsset GetAsset(
        string slot,
        string revision
    )
    {
        lock (_sync)
        {
            PresentationState state = GetState();
            PowerPoint.Presentation presentation =
                RequirePresentation();

            int slideIndex;

            if (slot == "current")
            {
                slideIndex = state.CurrentSlide;
            }
            else if (
                slot == "next"
                && state.NextSlide.HasValue
            )
            {
                slideIndex = state.NextSlide.Value;
            }
            else
            {
                return null;
            }

            string expected =
                slot == "current"
                ? state.CurrentSlideImageRevision
                : state.NextSlideImageRevision;

            if (!StringComparer.Ordinal.Equals(
                expected,
                revision
            ))
            {
                return null;
            }

            PowerPoint.Slide slide =
                presentation.Slides[slideIndex + 1];

            byte[] bytes = ExportSlidePng(slide);

            PresentationState after = GetState();

            string afterRevision =
                slot == "current"
                ? after.CurrentSlideImageRevision
                : after.NextSlideImageRevision;

            if (!StringComparer.Ordinal.Equals(
                revision,
                afterRevision
            ))
            {
                return null;
            }

            return new PresentationAsset
            {
                ContentType = "image/png",
                Bytes = bytes,
                Slot = slot,
                Revision = revision
            };
        }
    }

    private PowerPoint.Presentation TryGetPresentation()
    {
        return _application.Presentations.Count > 0
            ? _application.ActivePresentation
            : null;
    }

    private PowerPoint.Presentation RequirePresentation()
    {
        PowerPoint.Presentation presentation =
            TryGetPresentation();

        if (presentation == null)
        {
            throw new InvalidOperationException(
                "No active PowerPoint presentation."
            );
        }

        return presentation;
    }

    private PowerPoint.SlideShowView TryGetSlideShowView()
    {
        return _application.SlideShowWindows.Count > 0
            ? _application.SlideShowWindows[1].View
            : null;
    }

    private PowerPoint.SlideShowView RequireSlideShowView()
    {
        PowerPoint.SlideShowView view =
            TryGetSlideShowView();

        if (view == null)
        {
            throw new InvalidOperationException(
                "No running slide show."
            );
        }

        return view;
    }

    private void GoRelativeSlide(int delta)
    {
        PowerPoint.SlideShowView view =
            TryGetSlideShowView();

        if (view != null)
        {
            int count =
                RequirePresentation().Slides.Count;

            int target = Clamp(
                view.CurrentShowPosition + delta,
                1,
                count
            );

            view.GotoSlide(target);
            return;
        }

        PowerPoint.DocumentWindow window =
            _application.ActiveWindow;

        int current =
            window.View.Slide.SlideIndex;

        int targetEditing = Clamp(
            current + delta,
            1,
            RequirePresentation().Slides.Count
        );

        window.View.GotoSlide(targetEditing);
    }

    private void ToggleBlackScreen()
    {
        PowerPoint.SlideShowView view =
            RequireSlideShowView();

        view.State =
            view.State ==
                PowerPoint.PpSlideShowState
                    .ppSlideShowBlackScreen
            ? PowerPoint.PpSlideShowState
                .ppSlideShowRunning
            : PowerPoint.PpSlideShowState
                .ppSlideShowBlackScreen;
    }

    private static bool IsBlankState(
        PowerPoint.PpSlideShowState state
    )
    {
        return state ==
            PowerPoint.PpSlideShowState
                .ppSlideShowBlackScreen
            || state ==
            PowerPoint.PpSlideShowState
                .ppSlideShowWhiteScreen;
    }

    private int GetEditingSlideNumber()
    {
        try
        {
            return _application
                .ActiveWindow
                .View
                .Slide
                .SlideIndex;
        }
        catch
        {
            return 1;
        }
    }

    private static string ExtractTitle(
        PowerPoint.Slide slide
    )
    {
        foreach (
            PowerPoint.Shape shape
            in slide.Shapes
        )
        {
            try
            {
                if (
                    shape.HasTextFrame ==
                        MsoTriState.msoTrue
                    && shape.TextFrame.HasText ==
                        MsoTriState.msoTrue
                )
                {
                    string text =
                        shape.TextFrame
                            .TextRange
                            .Text
                            .Trim();

                    if (!string.IsNullOrEmpty(text))
                    {
                        return text
                            .Split(
                                new[] { '\r', '\n' },
                                StringSplitOptions
                                    .RemoveEmptyEntries
                            )[0]
                            .Trim();
                    }
                }
            }
            finally
            {
                ReleaseCom(shape);
            }
        }

        return string.Empty;
    }

    private static string ExtractNotes(
        PowerPoint.Slide slide
    )
    {
        var parts =
            new System.Collections.Generic
                .List<string>();

        foreach (
            PowerPoint.Shape shape
            in slide.NotesPage.Shapes
        )
        {
            try
            {
                if (
                    shape.HasTextFrame !=
                        MsoTriState.msoTrue
                    || shape.TextFrame.HasText !=
                        MsoTriState.msoTrue
                )
                {
                    continue;
                }

                string text =
                    shape.TextFrame
                        .TextRange
                        .Text
                        .Trim();

                if (
                    string.IsNullOrEmpty(text)
                    || IsNotesPlaceholderNoise(
                        shape,
                        text
                    )
                )
                {
                    continue;
                }

                parts.Add(text);
            }
            finally
            {
                ReleaseCom(shape);
            }
        }

        return string.Join(
            Environment.NewLine
                + Environment.NewLine,
            parts
        );
    }

    private static bool IsNotesPlaceholderNoise(
        PowerPoint.Shape shape,
        string text
    )
    {
        string normalized =
            string.Join(
                " ",
                text.ToLowerInvariant()
                    .Split(
                        (char[])null,
                        StringSplitOptions
                            .RemoveEmptyEntries
                    )
            );

        switch (normalized)
        {
            case "<number>":
            case "<date>":
            case "<time>":
            case "<date/time>":
            case "<header>":
            case "<footer>":
            case "<slide number>":
                return true;
        }

        try
        {
            if (
                shape.Type ==
                MsoShapeType.msoPlaceholder
            )
            {
                PowerPoint.PpPlaceholderType type =
                    shape.PlaceholderFormat.Type;

                return type ==
                    PowerPoint.PpPlaceholderType
                        .ppPlaceholderSlideImage
                    || type ==
                    PowerPoint.PpPlaceholderType
                        .ppPlaceholderHeader
                    || type ==
                    PowerPoint.PpPlaceholderType
                        .ppPlaceholderFooter
                    || type ==
                    PowerPoint.PpPlaceholderType
                        .ppPlaceholderDate
                    || type ==
                    PowerPoint.PpPlaceholderType
                        .ppPlaceholderSlideNumber;
            }
        }
        catch
        {
        }

        return false;
    }

    private static byte[] ExportSlidePng(
        PowerPoint.Slide slide
    )
    {
        string directory = Path.Combine(
            Path.GetTempPath(),
            "PresenterRemote",
            Guid.NewGuid().ToString("N")
        );

        Directory.CreateDirectory(directory);

        string file =
            Path.Combine(directory, "slide.png");

        try
        {
            slide.Export(
                file,
                "PNG",
                1600,
                900
            );

            return File.ReadAllBytes(file);
        }
        finally
        {
            try
            {
                Directory.Delete(
                    directory,
                    true
                );
            }
            catch
            {
            }
        }
    }

    private static int Clamp(
        int value,
        int minimum,
        int maximum
    )
    {
        return Math.Max(
            minimum,
            Math.Min(maximum, value)
        );
    }

    private static string BuildRevision(
        PowerPoint.Slide slide,
        string title,
        string notes
    )
    {
        string input =
            slide.SlideID
            + "|"
            + slide.SlideIndex
            + "|"
            + title
            + "|"
            + notes;

        using (
            var sha =
                System.Security.Cryptography
                    .SHA256.Create()
        )
        {
            byte[] hash = sha.ComputeHash(
                System.Text.Encoding.UTF8
                    .GetBytes(input)
            );

            return BitConverter
                .ToString(hash)
                .Replace("-", "")
                .ToLowerInvariant();
        }
    }

    private static void ReleaseCom(
        object value
    )
    {
        if (
            value != null
            && System.Runtime.InteropServices
                .Marshal.IsComObject(value)
        )
        {
            System.Runtime.InteropServices
                .Marshal.FinalReleaseComObject(
                    value
                );
        }
    }
}
```

This is a reference skeleton. Exact COM cleanup, VSTO threading, and framework compatibility must be tested in the chosen project template.

## 8.3 Events

Subscribe to:

```csharp
private void RegisterEvents()
{
    Application.SlideShowBegin +=
        OnSlideShowBegin;

    Application.SlideShowNextSlide +=
        OnSlideShowNextSlide;

    Application.SlideShowNextBuild +=
        OnSlideShowNextBuild;

    Application.SlideShowEnd +=
        OnSlideShowEnd;

    Application.WindowSelectionChange +=
        OnWindowSelectionChange;

    Application.PresentationOpen +=
        OnPresentationChanged;

    Application.PresentationClose +=
        OnPresentationChanged;
}
```

Handlers should:

- debounce rapid build events;
- not block PowerPoint;
- publish state to the companion;
- avoid modal dialogs during a show.

Run a low-frequency fallback poll while a remote session is active so manual changes are not missed.

## 8.4 Ribbon

```text
Presentation Remote
├── Start Remote
├── Stop Remote
├── Show Pairing
├── Route
│   ├── Auto
│   ├── Local
│   ├── Direct IPv6
│   └── Relay
├── Settings
└── Diagnostics
```

The companion owns transport settings; the add-in forwards UI actions.

## 8.5 Lifecycle

Startup:

1. Locate signed companion.
2. Start it if absent.
3. Read bootstrap descriptor.
4. Authenticate bridge.
5. Register PowerPoint host.
6. Begin event forwarding.

Shutdown:

1. Remove PowerPoint events.
2. Close bridge.
3. Mark host unavailable.
4. Stop companion only when no other host uses it.

## 8.6 Packaging

Ship:

- VSTO add-in;
- companion executable;
- required runtime;
- signed installer;
- repair and uninstall support.

Test:

- current Microsoft 365 PowerPoint;
- supported Windows releases;
- normal user rights;
- corporate add-in policy;
- upgrade/repair/uninstall;
- multiple presentations;
- companion crash and restart.

---

## 9. PowerPoint for macOS

## 9.1 Architecture

PowerPoint for Mac supports VBA add-ins and much of the PowerPoint object model. The hard part is asynchronous commands from an external helper because Office is sandboxed.

```text
PowerPoint for Mac
  └── PresentationRemote.ppam
        ├── Auto_Open / Auto_Close
        ├── PowerPoint application events
        ├── notes extraction
        ├── slide export
        ├── state serialization
        └── AppleScriptTask state push
              └── signed Presenter Remote.app
                    ├── local/relay runtime
                    ├── pairing UI
                    ├── accessibility command executor
                    └── shared phone UI
```

Recommended command direction:

```text
Phone command
 -> encrypted local/relay transport
 -> helper
 -> trusted Accessibility/CGEvent input
 -> PowerPoint slide show
 -> PPAM event
 -> updated state to helper
```

This avoids depending on undocumented helper-to-VBA invocation.

## 9.2 Mandatory proof of concept

Prove all of these before building the full port:

1. `.ppam` loads and runs `Auto_Open`.
2. Events fire for slide-show begin, next slide, next build, and end.
3. VBA reads current slide, count, notes, and title.
4. VBA exports current slide to PNG in an allowed location.
5. `AppleScriptTask` posts state to helper.
6. Helper can send trusted next, previous, black, exit, and slide-number input.
7. PPAM events confirm state changes.
8. Accessibility permission is recoverable.
9. It works with presenter view, full screen, and multiple monitors.

If any point is unreliable, reduce capabilities.

## 9.3 VBA structure

```text
PresentationRemote.ppam
├── AutoMacros.bas
├── RemoteController.bas
├── StateSerializer.bas
├── Notes.bas
├── Preview.bas
├── HelperBridge.bas
├── RibbonCallbacks.bas
└── PresentationEvents.cls
```

Auto macros:

```vb
Option Explicit

Public gEvents As PresentationEvents

Public Sub Auto_Open()
    Set gEvents = New PresentationEvents
    Set gEvents.App = Application
    HelperStart
    PublishCurrentState
End Sub

Public Sub Auto_Close()
    On Error Resume Next
    HelperStop
    Set gEvents.App = Nothing
    Set gEvents = Nothing
End Sub
```

Event class:

```vb
Option Explicit

Public WithEvents App As PowerPoint.Application

Private Sub App_SlideShowBegin( _
    ByVal Wn As SlideShowWindow _
)
    PublishCurrentState
End Sub

Private Sub App_SlideShowNextSlide( _
    ByVal Wn As SlideShowWindow _
)
    PublishCurrentState
End Sub

Private Sub App_SlideShowNextBuild( _
    ByVal Wn As SlideShowWindow _
)
    PublishCurrentState
End Sub

Private Sub App_SlideShowEnd( _
    ByVal Pres As Presentation _
)
    PublishCurrentState
End Sub

Private Sub App_PresentationOpen( _
    ByVal Pres As Presentation _
)
    PublishCurrentState
End Sub

Private Sub App_PresentationClose( _
    ByVal Pres As Presentation _
)
    PublishCurrentState
End Sub
```

State helpers:

```vb
Option Explicit

Public Function CurrentSlideIndexZeroBased() As Long
    If SlideShowWindows.Count > 0 Then
        CurrentSlideIndexZeroBased = _
            SlideShowWindows(1) _
                .View _
                .CurrentShowPosition - 1

        Exit Function
    End If

    If Not ActiveWindow Is Nothing Then
        CurrentSlideIndexZeroBased = _
            ActiveWindow _
                .View _
                .Slide _
                .SlideIndex - 1

        Exit Function
    End If

    CurrentSlideIndexZeroBased = 0
End Function

Public Function ExtractSlideNotes( _
    ByVal Sld As Slide _
) As String

    Dim Shp As Shape
    Dim Result As String
    Dim TextValue As String

    For Each Shp In Sld.NotesPage.Shapes
        If Shp.HasTextFrame Then
            If Shp.TextFrame.HasText Then
                TextValue = Trim$( _
                    Shp.TextFrame.TextRange.Text _
                )

                If Len(TextValue) > 0 Then
                    If Not IsNotesPlaceholderNoise( _
                        Shp, _
                        TextValue _
                    ) Then
                        If Len(Result) > 0 Then
                            Result = _
                                Result _
                                & vbCrLf _
                                & vbCrLf
                        End If

                        Result = _
                            Result _
                            & TextValue
                    End If
                End If
            End If
        End If
    Next Shp

    ExtractSlideNotes = Result
End Function
```

State push:

```vb
Option Explicit

Private Const SCRIPT_FILE As String = _
    "PresenterRemoteBridge.applescript"

Private Const SCRIPT_HANDLER As String = _
    "postState"

Public Sub PublishCurrentState()
    On Error GoTo Failed

    Dim JsonPayload As String
    JsonPayload = BuildStateJson()

    Dim Result As String

    Result = AppleScriptTask( _
        SCRIPT_FILE, _
        SCRIPT_HANDLER, _
        JsonPayload _
    )

    Exit Sub

Failed:
    Debug.Print _
        "PublishCurrentState failed: " _
        & Err.Description
End Sub
```

AppleScript location:

```text
~/Library/Application Scripts/com.microsoft.Powerpoint/
```

Bridge example:

```applescript
on postState(jsonPayload)
    set shellCommand to ¬
        "/usr/bin/curl --silent --show-error " & ¬
        "--max-time 2 " & ¬
        "--header " & ¬
        quoted form of "Content-Type: application/json" & ¬
        " " & ¬
        "--header " & ¬
        quoted form of "Authorization: Bearer TOKEN" & ¬
        " " & ¬
        "--data-binary " & ¬
        quoted form of jsonPayload & ¬
        " " & ¬
        quoted form of ¬
        "http://127.0.0.1:PORT/bridge/state"

    return do shell script shellCommand
end postState
```

Do not hardcode token or port. Production code reads a current-user bootstrap descriptor or receives an endpoint descriptor in the `AppleScriptTask` parameter.

## 9.4 Slide export

```vb
Public Function ExportSlidePng( _
    ByVal Sld As Slide, _
    ByVal TargetPath As String _
) As Boolean

    On Error GoTo Failed

    Sld.Export _
        TargetPath, _
        "PNG", _
        1600, _
        900

    ExportSlidePng = True
    Exit Function

Failed:
    ExportSlidePng = False
End Function
```

Use an Office-accessible location or request access during setup. Delete exported files promptly.

## 9.5 Helper input

The helper needs Accessibility permission.

Reference Swift:

```swift
import ApplicationServices

enum RemoteCommand {
    case next
    case previous
    case black
    case exit
    case goToSlide(Int)
}

enum RemoteError: Error {
    case accessibilityPermissionMissing
    case eventCreationFailed
}

func postKey(
    _ keyCode: CGKeyCode,
    flags: CGEventFlags = []
) throws {
    guard AXIsProcessTrusted() else {
        throw RemoteError
            .accessibilityPermissionMissing
    }

    guard
        let down = CGEvent(
            keyboardEventSource: nil,
            virtualKey: keyCode,
            keyDown: true
        ),
        let up = CGEvent(
            keyboardEventSource: nil,
            virtualKey: keyCode,
            keyDown: false
        )
    else {
        throw RemoteError.eventCreationFailed
    }

    down.flags = flags
    up.flags = flags

    down.post(tap: .cghidEventTap)
    up.post(tap: .cghidEventTap)
}
```

Verify mappings against the current PowerPoint release:

```text
next effect/slide -> Right Arrow or Space
previous -> Left Arrow
black screen -> B
end -> Escape
go to slide -> digits followed by Return, only if confirmed
```

Do not advertise start, pause, resume, or jump until proven.

## 9.6 Capability tiers

Tier 1:

- next;
- previous;
- current slide;
- notes;
- current preview;
- end;
- black screen;
- state updates.

Tier 2:

- effect distinction;
- next preview;
- jump;
- start;
- pause/resume;
- reliable background operation.

Release only tested capabilities.

## 9.7 macOS packaging

Install:

- signed/notarized helper app;
- `.ppam`;
- AppleScript bridge;
- per-user configuration.

The installer explains Accessibility permission, avoids Full Disk Access, installs no system daemon, and provides diagnostics.
---

## 10. Browser extension

## 10.1 Scope

A browser extension can support Google Slides, PowerPoint for the web, and other online suites, but each suite requires its own adapter.

Pure extension mode uses relay transport because a normal extension cannot bind an arbitrary LAN HTTP server. Local-LAN mode can be added through the shared native companion and browser native messaging.

```text
Phone
  └── encrypted WebSocket
        └── relay
              └── encrypted WebSocket
                    └── extension background
                          └── content script
                                └── suite adapter
                                      └── presentation page
```

Optional local mode:

```text
Phone
  └── local HTTP/SSE
        └── companion
              └── native messaging
                    └── extension
                          └── suite adapter
```

Targets:

```text
Chrome/Chromium: Manifest V3, minimum Chrome 116
Microsoft Edge: Chromium build
Firefox: separate WebExtension manifest/build
```

Use a compatibility wrapper rather than scattering `chrome.*` and `browser.*` differences through the codebase.

Bundle all executable code. Do not download adapters as JavaScript or WebAssembly.

## 10.2 Structure

```text
hosts/browser-extension/
├── src/
│   ├── background/
│   │   ├── service-worker.ts
│   │   ├── sessions.ts
│   │   ├── tabs.ts
│   │   └── diagnostics.ts
│   ├── relay/
│   │   ├── client.ts
│   │   ├── reconnect.ts
│   │   └── keepalive.ts
│   ├── protocol/
│   │   ├── codec.ts
│   │   ├── messages.ts
│   │   ├── replay-cache.ts
│   │   └── vectors.test.ts
│   ├── content/
│   │   ├── bootstrap.ts
│   │   ├── bridge.ts
│   │   ├── observer.ts
│   │   └── page-world.ts
│   ├── adapters/
│   │   ├── adapter.ts
│   │   ├── google-slides/
│   │   ├── powerpoint-web/
│   │   ├── onlyoffice/
│   │   └── generic/
│   ├── oauth/
│   ├── capture/
│   ├── popup/
│   ├── options/
│   └── shared/
├── manifests/
│   ├── chromium.json
│   └── firefox.json
├── fixtures/
├── tests/
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## 10.3 Adapter interface

```typescript
export interface WebPresentationAdapter {
  readonly id: string;
  readonly displayName: string;

  matches(
    location: Location,
    document: Document
  ): boolean;

  initialize(
    context: AdapterContext
  ): Promise<void>;

  dispose(): Promise<void>;

  getCapabilities():
    Promise<PresentationCapabilities>;

  getState():
    Promise<PresentationState>;

  execute(
    command: PresentationCommand
  ): Promise<CommandResult>;

  getAsset(
    request: AssetRequest
  ): Promise<PresentationAsset | null>;

  subscribe(
    listener: (event: AdapterEvent) => void
  ): Promise<() => void>;
}
```

```typescript
export interface AdapterContext {
  tabId: number;
  frameId: number;

  sendToBackground(
    message: ContentToBackgroundMessage
  ): Promise<void>;

  requestVisibleTabCapture():
    Promise<string>;

  logger: Logger;
}
```

Registry:

```typescript
const adapters: WebPresentationAdapter[] = [
  new GoogleSlidesAdapter(),
  new PowerPointWebAdapter(),
  new OnlyOfficeAdapter(),
  new GenericPresentationAdapter(),
];

export function selectAdapter(
  location: Location,
  document: Document
): WebPresentationAdapter | null {
  return (
    adapters.find(
      (adapter) =>
        adapter.matches(location, document)
    ) ?? null
  );
}
```

## 10.4 Chromium manifest

```json
{
  "manifest_version": 3,
  "name": "Presenter Remote",
  "version": "1.0.0",
  "minimum_chrome_version": "116",
  "action": {
    "default_popup": "popup/index.html"
  },
  "background": {
    "service_worker": "background/service-worker.js",
    "type": "module"
  },
  "permissions": [
    "activeTab",
    "storage",
    "scripting",
    "tabs",
    "identity"
  ],
  "optional_permissions": [
    "nativeMessaging"
  ],
  "host_permissions": [
    "https://docs.google.com/presentation/*",
    "https://*.office.com/*",
    "https://*.officeapps.live.com/*"
  ],
  "content_scripts": [
    {
      "matches": [
        "https://docs.google.com/presentation/*",
        "https://*.office.com/*",
        "https://*.officeapps.live.com/*"
      ],
      "js": [
        "content/bootstrap.js"
      ],
      "run_at": "document_idle",
      "all_frames": true
    }
  ],
  "web_accessible_resources": [
    {
      "resources": [
        "content/page-world.js"
      ],
      "matches": [
        "https://docs.google.com/*",
        "https://*.office.com/*",
        "https://*.officeapps.live.com/*"
      ]
    }
  ],
  "content_security_policy": {
    "extension_pages": "script-src 'self'; object-src 'none';"
  }
}
```

Narrow host permissions where possible. Prefer optional permissions for additional suites.

## 10.5 Firefox manifest

Generate a separate manifest:

```json
{
  "manifest_version": 3,
  "name": "Presenter Remote",
  "version": "1.0.0",
  "action": {
    "default_popup": "popup/index.html"
  },
  "background": {
    "scripts": [
      "background/background.js"
    ]
  },
  "permissions": [
    "activeTab",
    "storage",
    "scripting",
    "tabs",
    "identity"
  ],
  "optional_permissions": [
    "nativeMessaging"
  ],
  "host_permissions": [
    "https://docs.google.com/presentation/*",
    "https://*.office.com/*",
    "https://*.officeapps.live.com/*"
  ],
  "browser_specific_settings": {
    "gecko": {
      "id": "presenter-remote@example.invalid",
      "strict_min_version": "REVERIFY_AT_IMPLEMENTATION"
    }
  }
}
```

Reverify Firefox background service-worker support and lifecycle when implementation begins. Use a background-script build if it is more reliable for the target release.

## 10.6 Background relay client

The background runtime owns:

- relay connection;
- codec and secrets;
- active tab/adapter association;
- reconnect;
- state throttling;
- assets;
- command forwarding;
- diagnostics.

Reference skeleton:

```typescript
class RelaySession {
  private socket: WebSocket | null = null;
  private codec: SecureRelayCodec;
  private keepAliveTimer: number | null = null;
  private stopped = false;

  constructor(
    private readonly relayUrl: string,
    private readonly sessionId: string,
    pairingSecret: string,
    private readonly activeHost: ActiveHost
  ) {
    this.codec =
      SecureRelayCodec.forDesktopHost(
        sessionId,
        pairingSecret
      );
  }

  async start(): Promise<void> {
    this.stopped = false;
    await this.connectLoop();
  }

  stop(): void {
    this.stopped = true;
    this.clearKeepAlive();
    this.socket?.close();
    this.socket = null;
  }

  private async connectLoop(): Promise<void> {
    let delayMs = 1000;

    while (!this.stopped) {
      try {
        await this.connectOnce();
        delayMs = 1000;
      } catch {
        await sleep(delayMs);
        delayMs = Math.min(
          delayMs * 2,
          30000
        );
      }
    }
  }

  private async connectOnce(): Promise<void> {
    const socket = new WebSocket(
      buildRelayWebSocketUrl(
        this.relayUrl,
        this.sessionId
      )
    );

    this.socket = socket;
    await waitForOpen(socket);

    socket.send(
      JSON.stringify(
        await this.codec.rotateSendKey()
      )
    );

    this.startKeepAlive();

    let lastStateJson = "";
    let lastStateAt = 0;

    while (
      !this.stopped
      && socket.readyState ===
        WebSocket.OPEN
    ) {
      if (
        this.codec.shouldRotateSendKey()
      ) {
        socket.send(
          JSON.stringify(
            await this.codec
              .rotateSendKey()
          )
        );

        lastStateJson = "";
      }

      const state =
        await this.activeHost.getState();

      const stateJson =
        JSON.stringify(state);

      const now = Date.now();

      if (
        stateJson !== lastStateJson
        || now - lastStateAt >= 1000
      ) {
        socket.send(
          JSON.stringify(
            await this.codec
              .encodeStateFrame(state)
          )
        );

        lastStateJson = stateJson;
        lastStateAt = now;
      }

      await this.sendChangedAssets(
        socket,
        state
      );

      const incoming =
        await receiveWithTimeout(
          socket,
          500
        );

      if (incoming !== null) {
        await this.handleIncoming(
          socket,
          incoming
        );
      }
    }

    this.clearKeepAlive();
    socket.close();
  }

  private startKeepAlive(): void {
    this.clearKeepAlive();

    this.keepAliveTimer =
      self.setInterval(() => {
        if (
          this.socket?.readyState ===
          WebSocket.OPEN
        ) {
          this.socket.send(
            JSON.stringify({
              type: "keepalive",
            })
          );
        }
      }, 20000);
  }

  private clearKeepAlive(): void {
    if (
      this.keepAliveTimer !== null
    ) {
      clearInterval(
        this.keepAliveTimer
      );

      this.keepAliveTimer = null;
    }
  }
}
```

Persist only enough session state to restore after service-worker termination. Do not store pairing secrets in synchronized storage.

## 10.7 Content script

```typescript
const adapter = selectAdapter(
  window.location,
  document
);

if (adapter) {
  await adapter.initialize(context);

  const unsubscribe =
    await adapter.subscribe(async () => {
      const state =
        await adapter.getState();

      await browser.runtime
        .sendMessage({
          type: "adapter.state",
          adapterId: adapter.id,
          state,
        });
    });

  browser.runtime.onMessage
    .addListener(
      async (
        message: BackgroundToContentMessage
      ) => {
        if (
          message.type ===
          "adapter.command"
        ) {
          return adapter.execute(
            message.command
          );
        }

        if (
          message.type ===
          "adapter.asset"
        ) {
          return adapter.getAsset(
            message.request
          );
        }

        return undefined;
      }
    );

  window.addEventListener(
    "pagehide",
    () => {
      unsubscribe();
      void adapter.dispose();
    }
  );
}
```

The content script never stores relay or OAuth secrets.

## 10.8 DOM interaction policy

Preference order:

1. Official suite API.
2. Stable accessible DOM controls.
3. Documented integration hooks.
4. Actual visible DOM `.click()`.
5. Synthetic keyboard event fallback.
6. Debugger/input APIs only as an experimental opt-in.

Prefer:

- roles;
- ARIA labels;
- stable `data-*` attributes;
- DOM relationships;
- URL state;
- presenter-view regions.

Do not rely solely on generated CSS class names.

Each selector set needs:

- confidence;
- version marker;
- fallbacks;
- fixture tests;
- local diagnostics.

---

## 11. Google Slides adapter

## 11.1 Design

Use two sources.

### Presenter page

Used for:

- start or attach;
- next/previous;
- current slide;
- manual navigation;
- presentation ID;
- immediate state.

### Google Slides REST API

Used for:

- ordered slide IDs;
- speaker notes;
- titles/text;
- clean thumbnails;
- skipped-slide metadata.

The REST API is not a running-slideshow control API. Navigation remains DOM-based.

## 11.2 OAuth

Prefer read-only scopes:

```text
https://www.googleapis.com/auth/presentations.readonly
https://www.googleapis.com/auth/drive.readonly
```

Use only the scope actually required. Tokens remain in background-owned local storage and never go to relay or content scripts.

## 11.3 API flow

Load:

```http
GET https://slides.googleapis.com/v1/presentations/{presentationId}
```

For each slide:

- use page object ID as stable slide ID;
- locate `slideProperties.notesPage`;
- locate `notesProperties.speakerNotesObjectId`;
- read matching shape text;
- honor `isSkipped`.

Thumbnail:

```http
GET https://slides.googleapis.com/v1/presentations/{presentationId}/pages/{pageObjectId}/thumbnail
```

Use `MEDIUM` by default. Fetch temporary thumbnail URLs promptly and forward bytes, not URLs.

## 11.4 Adapter skeleton

```typescript
export class GoogleSlidesAdapter
  implements WebPresentationAdapter {

  readonly id = "google-slides";
  readonly displayName =
    "Google Slides";

  private presentationId = "";
  private slideIds: string[] = [];
  private currentIndex = 0;
  private observer:
    MutationObserver | null = null;

  constructor(
    private readonly api:
      GoogleSlidesClient
  ) {}

  matches(
    location: Location
  ): boolean {
    return (
      location.hostname ===
        "docs.google.com"
      && location.pathname
        .startsWith(
          "/presentation/"
        )
    );
  }

  async initialize(
    context: AdapterContext
  ): Promise<void> {
    this.presentationId =
      extractGooglePresentationId(
        location.href
      );

    if (!this.presentationId) {
      throw new Error(
        "Google Slides presentation ID was not found."
      );
    }

    const presentation =
      await this.api.getPresentation(
        this.presentationId
      );

    this.slideIds =
      presentation.slides
        .filter(
          (slide) =>
            !slide.slideProperties
              ?.isSkipped
        )
        .map(
          (slide) => slide.objectId
        );

    this.currentIndex =
      this.detectCurrentIndex();

    this.observer =
      new MutationObserver(() => {
        const next =
          this.detectCurrentIndex();

        if (
          next !== this.currentIndex
        ) {
          this.currentIndex = next;

          void context
            .sendToBackground({
              type: "adapter.changed",
              adapterId: this.id,
            });
        }
      });

    this.observer.observe(
      document.documentElement,
      {
        subtree: true,
        attributes: true,
        childList: true,
      }
    );
  }

  async getCapabilities():
    Promise<PresentationCapabilities> {
    return {
      startPresentation:
        this.hasStartControl(),
      startFromFirstSlide:
        this.hasStartControl(),
      endPresentation:
        this.hasEndControl(),
      nextEffect:
        this.hasNextControl(),
      previousEffect:
        this.hasPreviousControl(),
      nextSlide:
        this.hasNextControl(),
      previousSlide:
        this.hasPreviousControl(),
      goToSlide:
        this.hasSlideNavigator(),
      pause: false,
      resume: false,
      blankScreen: false,
      currentPreview: true,
      nextPreview: true,
      speakerNotes: true,
      manualNavigationTracking: true,
    };
  }

  async getState():
    Promise<PresentationState> {
    const presentation =
      await this.api.getPresentation(
        this.presentationId
      );

    const current =
      presentation.slides[
        this.currentIndex
      ];

    const next =
      presentation.slides[
        this.currentIndex + 1
      ];

    return {
      stateSchema: 1,
      host: {
        family: "google-slides",
        displayName:
          "Google Slides",
        platform: "web",
        adapterVersion: "1.0.0",
      },
      running:
        this.isPresenting(),
      presentationActive:
        this.isPresenting(),
      presentationPaused: false,
      presentationBlanked: false,
      documentKind:
        "google-slides",
      statusMessage:
        this.isPresenting()
        ? "Presentation running"
        : "Presentation ready",
      currentSlide:
        this.currentIndex,
      slideCount:
        presentation.slides.length,
      currentTitle:
        extractGoogleSlideTitle(
          current
        ),
      notes:
        extractGoogleSpeakerNotes(
          current
        ),
      nextSlide:
        next
        ? this.currentIndex + 1
        : null,
      nextTitle:
        next
        ? extractGoogleSlideTitle(
            next
          )
        : "",
      nextPreview:
        next
        ? extractGoogleSlideSummary(
            next
          )
        : "",
      canGoPrevious:
        this.currentIndex > 0,
      canGoNext: Boolean(next),
      remainingSlides:
        Math.max(
          presentation.slides
            .length
            - this.currentIndex
            - 1,
          0
        ),
      atEndOfDeck: !next,
      elapsedSeconds: 0,
      currentSlideImageRevision:
        buildGoogleRevision(
          presentation.revisionId,
          current.objectId
        ),
      nextSlideImageRevision:
        next
        ? buildGoogleRevision(
            presentation.revisionId,
            next.objectId
          )
        : "",
      currentSlideImageUrl: "",
      nextSlideImageUrl: "",
      capabilities:
        await this.getCapabilities(),
    };
  }

  async execute(
    command: PresentationCommand
  ): Promise<CommandResult> {
    switch (command.command) {
      case "next_effect":
      case "next_slide":
        return clickFirstVisible(
          this.nextControlSelectors()
        );

      case "previous_effect":
      case "previous_slide":
        return clickFirstVisible(
          this.previousControlSelectors()
        );

      case "start_presentation":
      case "start_presentation_from_first_slide":
        return clickFirstVisible(
          this.startControlSelectors()
        );

      case "end_presentation":
        return clickFirstVisible(
          this.endControlSelectors()
        );

      case "goto_slide":
        return this.goToSlide(
          command.index
        );

      default:
        return {
          ok: false,
          code:
            "unsupported-command",
          message:
            "Google Slides adapter does not support this command.",
        };
    }
  }

  async getAsset(
    request: AssetRequest
  ): Promise<PresentationAsset | null> {
    const index =
      request.slot === "current"
      ? this.currentIndex
      : this.currentIndex + 1;

    const slideId =
      this.slideIds[index];

    if (!slideId) {
      return null;
    }

    const thumbnail =
      await this.api.getThumbnail(
        this.presentationId,
        slideId,
        "MEDIUM"
      );

    const response = await fetch(
      thumbnail.contentUrl,
      {
        credentials: "include",
      }
    );

    if (!response.ok) {
      throw new Error(
        "Google Slides thumbnail failed: "
          + response.status
      );
    }

    return {
      contentType:
        response.headers
          .get("content-type")
        ?? "image/png",
      bytes:
        new Uint8Array(
          await response.arrayBuffer()
        ),
      slot: request.slot,
      revision: request.revision,
    };
  }

  async dispose(): Promise<void> {
    this.observer?.disconnect();
    this.observer = null;
  }
}
```

DOM selectors must be discovered and tested against live Google Slides at implementation time. Do not treat temporary selectors as API contracts.

## 11.5 Google Slides tests

Cover:

- sanitized presenter fixtures;
- localized UI;
- presenter view and slideshow popup;
- skipped slides;
- absent/present notes;
- read-only shared files;
- OAuth expiration;
- thumbnail expiration;
- manual navigation;
- slide edits while presenting.

Run a manual live smoke test before every adapter release.

---

## 12. PowerPoint for the web adapter

## 12.1 Design

Use:

- presenter DOM for commands;
- DOM/URL for current state;
- visible-tab capture for current preview;
- optional Office.js companion for clean images or metadata;
- notes DOM when available.

Do not assume Office.js controls the running slide show.

### Extension-only mode

Likely features:

- next/previous;
- presenter attachment;
- current slide;
- current capture;
- possibly notes and jump.

### Extension plus Office.js

Office.js can contribute:

- slide collection;
- selected slide;
- clean slide image;
- document metadata.

The browser extension still controls and observes the presenter page.

## 12.2 Adapter skeleton

```typescript
export class PowerPointWebAdapter
  implements WebPresentationAdapter {

  readonly id = "powerpoint-web";

  readonly displayName =
    "PowerPoint for the web";

  private observer:
    MutationObserver | null = null;

  private lastFingerprint = "";

  matches(
    location: Location
  ): boolean {
    return (
      (
        location.hostname
          .endsWith(".office.com")
        || location.hostname
          .endsWith(
            ".officeapps.live.com"
          )
      )
      && this.detectPowerPointRoot()
    );
  }

  async initialize(
    context: AdapterContext
  ): Promise<void> {
    this.observer =
      new MutationObserver(
        async () => {
          const state =
            await this.getState();

          const fingerprint =
            JSON.stringify([
              state.running,
              state.currentSlide,
              state.slideCount,
              state.currentTitle,
              state.notes,
            ]);

          if (
            fingerprint !==
            this.lastFingerprint
          ) {
            this.lastFingerprint =
              fingerprint;

            await context
              .sendToBackground({
                type:
                  "adapter.changed",
                adapterId: this.id,
              });
          }
        }
      );

    this.observer.observe(
      document.documentElement,
      {
        subtree: true,
        childList: true,
        attributes: true,
      }
    );
  }

  async getCapabilities():
    Promise<PresentationCapabilities> {
    return {
      startPresentation:
        this.findStartButton() !== null,
      startFromFirstSlide:
        this.findStartButton() !== null,
      endPresentation:
        this.findEndButton() !== null,
      nextEffect:
        this.findNextButton() !== null,
      previousEffect:
        this.findPreviousButton() !==
        null,
      nextSlide:
        this.findNextButton() !== null,
      previousSlide:
        this.findPreviousButton() !==
        null,
      goToSlide:
        this.findSlideNavigator() !==
        null,
      pause:
        this.findPauseButton() !== null,
      resume:
        this.findResumeButton() !==
        null,
      blankScreen:
        this.findBlankButton() !==
        null,
      currentPreview: true,
      nextPreview: false,
      speakerNotes:
        this.findNotesRegion() !== null,
      manualNavigationTracking: true,
    };
  }

  async execute(
    command: PresentationCommand
  ): Promise<CommandResult> {
    const target =
      this.resolveControl(command);

    if (!target) {
      return {
        ok: false,
        code: "control-not-found",
        message:
          "PowerPoint Web control was not found for "
          + command.command,
      };
    }

    target.click();

    return {
      ok: true,
    };
  }

  async getAsset(
    request: AssetRequest
  ): Promise<PresentationAsset | null> {
    if (
      request.slot !== "current"
    ) {
      return null;
    }

    const screenshotDataUrl =
      await browser.runtime
        .sendMessage({
          type:
            "capture.visibleTab",
        });

    const bounds =
      this.detectSlideBounds();

    const bytes =
      await cropDataUrlToPng(
        screenshotDataUrl,
        bounds,
        window.devicePixelRatio
      );

    return {
      contentType: "image/png",
      bytes,
      slot: "current",
      revision: request.revision,
    };
  }

  async dispose(): Promise<void> {
    this.observer?.disconnect();
    this.observer = null;
  }
}
```

## 12.3 Notes order

1. Presenter-view notes DOM.
2. Optional Office.js companion.
3. Microsoft Graph download plus Open XML parsing only with explicit consent.
4. No notes capability.

Do not scrape internal authentication tokens or undocumented network APIs.

## 12.4 Capture

Use `captureVisibleTab` only when revision changes and required permission is present. Crop using detected slide bounds. Expect scaling, transitions, cursor, and overlays. Clean API images are preferable.

---

## 13. Other suites

Potential adapters:

```text
onlyoffice
zoho-show
pitch
canva-presentations
prezi
generic-web
```

Good targets have accessible controls, observable current slide, stable origin, and capturable stage.

Poor targets use inaccessible cross-origin frames, canvas-only controls, unstable generated selectors, or reject programmatic interaction.

### Generic adapter

Keep conservative capabilities:

- user selects a tab;
- configured actual next/previous buttons;
- current screenshot;
- no guaranteed notes;
- no trusted slide count;
- no guaranteed jump.

Never claim universal full support.

---

## 14. Native messaging for browser local mode

Native messaging connects the extension to the companion.

Use for:

- local LAN;
- direct IPv6;
- shared pairing;
- long-running session;
- system input fallback;
- avoiding service-worker lifecycle issues.

Native host manifest for Chromium:

```json
{
  "name": "org.presenterremote.companion",
  "description": "Presenter Remote companion bridge",
  "path": "/absolute/path/to/presenter-remote-native-host",
  "type": "stdio",
  "allowed_origins": [
    "chrome-extension://EXTENSION_ID/"
  ]
}
```

Firefox uses `allowed_extensions`.

Native messages are length-prefixed JSON. Avoid large base64 image messages where possible; use a token-protected companion asset endpoint or strict chunking.

Keep native messaging optional so relay-only users need no companion.

---

## 15. Shared phone UI

Required changes:

- generic title and connection strings;
- host display name;
- capability-driven controls;
- correlated command errors;
- separate current/next revisions;
- reject stale assets;
- transport display;
- diagnostics without secrets.

```typescript
interface RemoteViewModel {
  connection:
    | "connecting"
    | "live"
    | "reconnecting"
    | "offline";

  host: HostIdentity | null;

  capabilities:
    PresentationCapabilities;

  presentation:
    PresentationState | null;

  currentImageUrl: string;
  nextImageUrl: string;

  lastError: {
    code: string;
    message: string;
    commandId?: string;
  } | null;
}
```

Rules:

- hide structurally unsupported controls;
- disable controls forbidden by current state;
- if a suite cannot distinguish effect from slide, expose one advance action;
- keep preview-tap behavior capability-aware.

---

## 16. Security

## 16.1 Relay-hosted frontend limitation

Current encrypted frames protect against a passive or honest-but-curious relay, but a relay serving hostile phone JavaScript can read the fragment pairing secret.

Long-term options:

1. Installed PWA.
2. Native phone app.
3. Independently hosted audited static client.
4. Signed client bundle verified by installed bootstrap.
5. Relay serves transport only, not executable frontend.

Do not claim malicious-relay frontend protection until solved.

## 16.2 ECDH migration

Recommended future handshake:

- ephemeral P-256 keys;
- QR binds session and authentication material;
- ECDH plus HKDF;
- transcript-bound derivation;
- key confirmation;
- relay substitution detection;
- explicit protocol negotiation.

Maintain v1 compatibility during transition.

## 16.3 Browser security

- OAuth tokens only in background.
- No tokens in DOM.
- Validate every message.
- Bind messages to tab, frame, document, and adapter.
- Invalidate on navigation.
- Optional host permissions.
- No remote executable code.
- No `eval`.
- Avoid `chrome.debugger`.
- Use narrow randomized `postMessage` bridges if page-world code is required.

## 16.4 Companion security

- Signed binary.
- User-only data.
- Loopback-only bridge.
- Per-launch token.
- Strict sizes and rates.
- Temporary asset cleanup.
- No notes/images in logs.
- Crash-safe token invalidation.

## 16.5 Native input

- Request only required permission.
- Explain purpose.
- Verify target process is PowerPoint.
- Verify slideshow context.
- Fixed command enum only.
- Never send arbitrary user-provided keys.
- Disable during secure input or screen lock.

---

## 17. Protocol conformance

Create language-independent vectors:

```json
{
  "name": "v1-state-basic",
  "version": 1,
  "role": "plugin",
  "sessionId": "demo-session",
  "pairingSecret": "base64url-secret",
  "keyId": "kid123",
  "pluginNonce": "base64url-plugin-nonce",
  "kind": "state",
  "nonce": "base64url-12-byte-nonce",
  "payload": {
    "currentSlide": 0,
    "slideCount": 3
  },
  "expected": {
    "saltHex": "...",
    "infoHex": "...",
    "stateKeyHex": "...",
    "commandKeyHex": "...",
    "aadUtf8": "{\"kind\":\"state\",\"k\":\"kid123\",\"n\":\"...\",\"s\":\"demo-session\",\"v\":1}",
    "ciphertextAndTagBase64url": "..."
  }
}
```

Implement in:

```text
Python
TypeScript/Web Crypto
C#
Swift CryptoKit if native crypto is introduced
```

Test:

- derivation;
- wrong session/key/kind;
- modified nonce/AAD/ciphertext;
- replay;
- rotation;
- old-key window;
- malformed base64url;
- oversized frame;
- Unicode and empty notes;
- maximum asset.

Relay tests verify ciphertext is unchanged.

---

## 18. State and asset consistency

Revision tokens change when relevant rendered state changes.

Include:

- presentation identity;
- slide identity/index;
- host revision if available;
- title;
- notes where appropriate;
- blank/pause state when it affects rendering.

Asset flow:

1. Read state and revision.
2. Confirm request revision.
3. export/fetch/capture.
4. Read state again.
5. confirm revision unchanged.
6. return asset.
7. otherwise discard.

---

## 19. Error model

Recommended codes:

```text
no-presentation
not-presenting
unsupported-command
invalid-command
invalid-index
host-unavailable
host-busy
permission-required
oauth-required
oauth-expired
adapter-not-found
adapter-outdated
control-not-found
capture-unavailable
asset-stale
asset-too-large
bridge-offline
bridge-auth-failed
relay-offline
relay-rejected
protocol-mismatch
replay-detected
crypto-failed
```

```json
{
  "code": "permission-required",
  "message": "Enable Accessibility access for Presenter Remote.",
  "commandId": "optional-command-id",
  "details": {
    "permission": "macos-accessibility"
  }
}
```

No secrets, paths, notes, tokens, or document URLs in errors.

---

## 20. Testing

### Shared unit tests

- protocol and crypto;
- schemas;
- normalization;
- command validation;
- revision logic;
- reconnect and routing.

### Windows

- COM helper tests;
- notes filtering;
- title extraction;
- command mapping;
- bridge authentication;
- sample-deck integration.

Sample decks:

```text
basic.pptx
notes.pptx
animations.pptx
hidden-slides.pptx
custom-show.pptx
large-deck.pptx
media.pptx
unicode.pptx
```

### macOS

- VBA JSON fixtures;
- AppleScript bridge;
- input mapping;
- permissions;
- presenter view;
- one/two monitors;
- PowerPoint foreground/background;
- helper restart.

### Browser

- adapter selection;
- selectors against fixtures;
- state parsing;
- service-worker recovery;
- OAuth lifecycle;
- capture cropping;
- native messaging;
- live manual smoke tests.

Use Playwright for extension fixture tests. Do not store personal suite credentials in public CI.

### Compatibility matrix

Track:

```text
Host
Host version/build
OS
Browser
Extension version
Adapter version
Capabilities
Last verified date
Known issues
```

---

## 21. CI/CD

Workflows:

```text
protocol.yml
python-core.yml
libreoffice-extension.yml
relay-server.yml
powerpoint-windows.yml
powerpoint-macos.yml
browser-extension.yml
security.yml
release.yml
```

Protocol workflow:

- schemas;
- vectors in all languages;
- undocumented-change rejection.

Browser workflow:

- lint;
- type check;
- tests;
- Playwright fixtures;
- Chromium package;
- Firefox package;
- remote-code scan;
- permission inspection;
- source archive.

Windows integration requires a controlled Office test machine. macOS PowerPoint tests may require a dedicated interactive runner.

Signing:

- Windows code signing;
- macOS Developer ID and notarization;
- browser-store review/signing;
- checksums and provenance.

---

## 22. Packaging

LibreOffice:

```text
.oxt
```

PowerPoint Windows:

```text
signed installer
VSTO add-in
companion executable
```

PowerPoint macOS:

```text
signed/notarized app
.ppam
AppleScript bridge
.pkg or documented installation
```

Browser:

```text
Chrome Web Store
Microsoft Edge Add-ons
Firefox AMO
source archive
```

Relay:

```text
Python package
Docker image
release artifact
deployment examples
```

Publish a compatibility table:

```text
Protocol v1
Phone UI 1.x
Relay 1.x
LibreOffice host 1.x
PowerPoint Windows host 1.x
PowerPoint macOS host 1.x
Browser extension 1.x
```

---

## 23. Delivery order after LibreOffice and relay completion

### Phase 1: shared extraction

- generic Python runtime;
- schemas;
- vectors;
- host-neutral phone UI;
- capabilities;
- LibreOffice through generic interface.

Exit:

```text
LibreOffice works through PresentationHost without behavior loss.
```

### Phase 2: companion

- packaged runtime;
- secure bridge;
- pairing/settings;
- fake host;
- end-to-end local and relay tests.

Exit:

```text
Fake host sends state/assets, receives commands, rotates keys,
reconnects, and shuts down.
```

### Phase 3: PowerPoint Windows

- VSTO adapter;
- companion integration;
- full capability matrix;
- installer and tests.

### Phase 4: macOS proof of concept

- PPAM;
- events/state push;
- trusted helper commands;
- capability tier decision.

Stop or reduce scope if unreliable.

### Phase 5: browser core

- TypeScript protocol;
- conformance;
- relay session;
- adapter framework;
- fixture harness;
- Chromium/Firefox packages.

### Phase 6: Google Slides

- OAuth;
- API notes/thumbnails;
- DOM navigation;
- live validation.

### Phase 7: PowerPoint Web

- presenter adapter;
- capture;
- notes discovery;
- optional Office.js experiment.

### Phase 8: other suites

Add only with demand and a maintainer.

---

## 24. Non-goals

Do not promise:

- one extension package for every suite;
- universal full DOM control;
- macOS parity before proof;
- browser local mode without companion;
- protection from malicious relay-served phone code under current fragment-secret design;
- permanent stability of undocumented web UI;
- bypassing permissions or access controls.

---

## 25. Web-adapter maintenance policy

Each adapter needs:

- maintainer;
- last verified date;
- suite version marker;
- fixtures;
- smoke checklist;
- feature matrix;
- fallbacks;
- bundled quick-disable flag;
- no remotely downloaded executable patch.

When broken:

1. disable broken capability only;
2. preserve working state;
3. show `adapter-outdated`;
4. collect local diagnostics;
5. update bundled code;
6. publish store update.

Do not silently fall back to uncontrolled keyboard simulation.

---

## 26. Sources to reverify

### Project

- <https://github.com/bora-yarkin/libreoffice-impress-remote>
- <https://github.com/bora-yarkin/libreoffice-impress-remote/blob/main/docs/architecture.md>
- <https://github.com/bora-yarkin/libreoffice-impress-remote/blob/main/docs/protocol.md>
- <https://github.com/bora-yarkin/libreoffice-impress-remote/blob/main/docs/security/e2ee.md>
- <https://github.com/bora-yarkin/libreoffice-impress-remote/blob/main/docs/relay-server.md>
- <https://github.com/bora-yarkin/libreoffice-impress-remote/blob/main/docs/roadmap.md>

### Microsoft

- <https://learn.microsoft.com/en-us/visualstudio/vsto/powerpoint-solutions>
- <https://learn.microsoft.com/en-us/office/vba/api/powerpoint.slideshowview.next>
- <https://learn.microsoft.com/en-us/office/vba/api/powerpoint.slideshowview.gotoslide>
- <https://learn.microsoft.com/en-us/office/vba/api/powerpoint.slideshowsettings.run>
- <https://learn.microsoft.com/en-us/office/vba/api/powerpoint.application.run>
- <https://learn.microsoft.com/en-us/office/vba/powerpoint/concepts/auto-macros>
- <https://learn.microsoft.com/en-us/office/vba/api/overview/office-mac>
- <https://learn.microsoft.com/en-us/office/vba/office-mac/applescripttask>
- <https://learn.microsoft.com/en-us/office/dev/add-ins/overview/office-add-ins>
- <https://learn.microsoft.com/en-us/office/dev/add-ins/concepts/browsers-used-by-office-web-add-ins>
- <https://learn.microsoft.com/en-us/javascript/api/requirement-sets/powerpoint/powerpoint-api-requirement-sets>
- <https://learn.microsoft.com/en-us/javascript/api/requirement-sets/powerpoint/powerpoint-api-1-8-requirement-set>
- <https://learn.microsoft.com/en-us/javascript/api/powerpoint/powerpoint.slidegetimageoptions>

### Google

- <https://developers.google.com/workspace/slides/api/guides/overview>
- <https://developers.google.com/workspace/slides/api/guides/notes>
- <https://developers.google.com/workspace/slides/api/reference/rest/v1/presentations>
- <https://developers.google.com/workspace/slides/api/reference/rest/v1/presentations/get>
- <https://developers.google.com/workspace/slides/api/reference/rest/v1/presentations.pages/get>
- <https://developers.google.com/workspace/slides/api/reference/rest/v1/presentations.pages/getThumbnail>

### Chromium

- <https://developer.chrome.com/docs/extensions/develop/concepts/content-scripts>
- <https://developer.chrome.com/docs/extensions/develop/migrate/what-is-mv3>
- <https://developer.chrome.com/docs/extensions/how-to/web-platform/websockets>
- <https://developer.chrome.com/docs/extensions/reference/api/tabs>
- <https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging>
- <https://developer.chrome.com/docs/extensions/develop/migrate/remote-hosted-code>

### Mozilla

- <https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/manifest.json>
- <https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/manifest.json/background>

---

## 27. Final recommendation

After LibreOffice and relay are complete:

1. Extract the Python transport/security runtime behind a generic host interface.
2. Make the phone UI host-neutral and capability-aware.
3. Package the shared runtime as a companion.
4. Implement PowerPoint Windows first with VSTO.
5. Run a strict macOS proof before committing to the PPAM/helper port.
6. Build browser protocol conformance and adapter framework before site automation.
7. Implement Google Slides first because its API supplies notes and clean thumbnails.
8. Implement PowerPoint Web second, accepting DOM-dependent presenter control.
9. Add other suites only through isolated adapters with explicit capability matrices.

The project should become a protocol-driven presenter-remote platform, not a collection of unrelated ports.
