# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from pathlib import Path
import webbrowser
from typing import TYPE_CHECKING, Any, cast

import unohelper

from impress_remote.config import DEFAULT_PREFERRED_ROUTE, ROUTE_LABELS, normalize_preferred_route

if TYPE_CHECKING:
    from com.sun.star.awt import (  # pyright: ignore[reportMissingImports]
        XActionListener,
        XItemListener,
        XTextListener,
    )
    from impress_remote.component import ImpressRemoteProtocolHandler
else:
    from com.sun.star.awt import XActionListener  # pyright: ignore[reportMissingImports]
    try:
        from com.sun.star.awt import XItemListener  # pyright: ignore[reportMissingImports]
    except Exception:
        class XItemListener:
            def disposing(self, _event) -> None:
                return None

            def itemStateChanged(self, item_event) -> None:
                return None

    try:
        from com.sun.star.awt import XTextListener  # pyright: ignore[reportMissingImports]
    except Exception:
        class XTextListener:
            def disposing(self, _event) -> None:
                return None

            def textChanged(self, text_event) -> None:
                return None


def _service_manager(ctx):
    if hasattr(ctx, "ServiceManager"):
        return ctx.ServiceManager
    return ctx.getServiceManager()


def open_external_url(ctx, url: str) -> bool:
    if not url:
        return False
    try:
        shell = _service_manager(ctx).createInstanceWithContext(
            "com.sun.star.system.SystemShellExecute",
            ctx,
        )
        shell.execute(url, "", 0)
        return True
    except Exception:
        return bool(webbrowser.open(url, new=2))


def show_error_message(ctx, message: str, title: str = "Impress Remote") -> None:
    if not message:
        return
    try:
        desktop = _service_manager(ctx).createInstanceWithContext(
            "com.sun.star.frame.Desktop",
            ctx,
        )
        frame = desktop.getCurrentFrame() if hasattr(desktop, "getCurrentFrame") else None
        window = frame.getContainerWindow() if frame is not None else None
        parent = window.getPeer() if window is not None and hasattr(window, "getPeer") else None
        toolkit = _service_manager(ctx).createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)
        message_box = toolkit.createMessageBox(parent, 3, 1, title, message)
        message_box.execute()
    except Exception:
        return


class DialogButtonListener(unohelper.Base, XActionListener):
    def __init__(self, dialog):
        self.dialog = dialog

    def disposing(self, _event):
        return None

    def actionPerformed(self, action_event):
        control_name = action_event.Source.getModel().Name
        self.dialog.handle_action(control_name)


class DialogItemListener(unohelper.Base, XItemListener):
    def __init__(self, dialog):
        self.dialog = dialog

    def disposing(self, _event):
        return None

    def itemStateChanged(self, item_event):
        control_name = item_event.Source.getModel().Name
        self.dialog.handle_item_change(control_name)


class DialogTextListener(unohelper.Base, XTextListener):
    def __init__(self, dialog):
        self.dialog = dialog

    def disposing(self, _event):
        return None

    def textChanged(self, text_event):
        control_name = text_event.Source.getModel().Name
        self.dialog.handle_text_change(control_name)


class RemoteSettingsDialog:
    def __init__(self, ctx, handler: ImpressRemoteProtocolHandler):
        self.ctx = ctx
        self.handler = handler
        self.smgr = _service_manager(ctx)
        self.dialog: Any | None = None
        self.listeners: dict[str, DialogButtonListener] = {}
        self.item_listeners: dict[str, DialogItemListener] = {}
        self.text_listeners: dict[str, DialogTextListener] = {}
        self.qr_error = ""
        self.preview_error = ""
        self.qr_image_path: Path | None = None
        self._updating_route = False

    def show(self) -> None:
        dialog = self._create_dialog()
        self.dialog = dialog
        self._add_listeners()
        self.refresh()
        dialog.execute()
        self._remove_listeners()
        self._cleanup_qr_image()
        dialog.dispose()

    def handle_action(self, control_name: str) -> None:
        dialog = self._dialog()
        try:
            if control_name == "close_button":
                dialog.endExecute()
                return
            if control_name == "save_button":
                self._save_settings()
                return
            if control_name == "start_button":
                self.handler.start()
                self.refresh("Remote started.")
                return
            if control_name == "stop_button":
                self.handler.stop()
                self.refresh("Remote stopped.")
                return
            if control_name == "open_button":
                self._open_selected_remote()
                return
        except Exception as exc:
            message = f"Action failed: {exc}"
            self.handler.report_runtime_error(message)
            show_error_message(self.ctx, message)
            self.refresh(message)

    def handle_item_change(self, control_name: str) -> None:
        if self._updating_route:
            return
        if control_name in {"route_value", "local_value", "ipv6_value", "relay_value"}:
            self._refresh_pairing_preview()

    def handle_text_change(self, control_name: str) -> None:
        if control_name in {"relay_url_value", "local_port_value"}:
            self._refresh_pairing_preview()

    def refresh(self, status_line: str | None = None) -> None:
        snapshot = cast(dict[str, Any], self.handler.runtime_snapshot())
        config = cast(dict[str, Any], snapshot["config"])
        connection = cast(dict[str, Any], snapshot["connection"])

        self._set_label("status_value", status_line or str(snapshot["statusLine"]))
        self._set_label("session_value", f"Session ID: {connection['session']}")
        self._set_text("local_port_value", str(config["localPort"]))
        self._set_text("relay_url_value", str(config["relayUrl"]))
        self._set_checkbox("local_value", bool(config["enableLocalListener"]))
        self._set_checkbox("ipv6_value", bool(config["enableIpv6Direct"]))
        self._set_checkbox("relay_value", bool(config["enableRelay"]))
        self._set_label("relay_state_value", self._relay_state_text(connection))
        self._set_label("warning_value", self._issues_text(snapshot, connection))
        self._updating_route = True
        try:
            self._set_route_selection(
                "route_value",
                normalize_preferred_route(
                    str(config.get("preferredRoute", DEFAULT_PREFERRED_ROUTE))
                ),
            )
        finally:
            self._updating_route = False
        self._refresh_pairing_preview(snapshot)

    def _save_settings(self) -> None:
        local_port_text = self._get_text("local_port_value").strip()
        if not local_port_text.isdigit() or not 1 <= int(local_port_text) <= 65535:
            self.refresh("Preferred local port must be a number from 1 to 65535.")
            return

        payload = {
            "localPort": int(local_port_text),
            "enableLocalListener": self._get_checkbox("local_value"),
            "enableIpv6Direct": self._get_checkbox("ipv6_value"),
            "enableRelay": self._get_checkbox("relay_value"),
            "relayUrl": self._get_text("relay_url_value").strip(),
            "preferredRoute": self._selected_route(),
        }
        try:
            self.handler.apply_settings(payload, restart_runtime=True)
        except ValueError as exc:
            self.refresh(str(exc))
            return
        self.refresh("Settings saved.")

    def _open_selected_remote(self) -> None:
        if self._has_unsaved_transport_changes():
            self.refresh("Save settings before opening a route with new transport changes.")
            return
        pairing = self.handler.preview_pairing_target(self._draft_payload(), self._selected_route())
        target = pairing["selectedUrl"]
        if not target:
            self.refresh(pairing["hint"])
            return
        if open_external_url(self.ctx, target):
            self.refresh("Opened the remote preview in your browser.")
            return
        self.refresh("LibreOffice could not open the remote preview.")

    def _create_dialog(self):
        dialog_model = self.smgr.createInstanceWithContext(
            "com.sun.star.awt.UnoControlDialogModel",
            self.ctx,
        )
        dialog_model.PositionX = 40
        dialog_model.PositionY = 40
        dialog_model.Width = 346
        dialog_model.Height = 338
        dialog_model.Closeable = True
        dialog_model.Sizeable = False

        self._add_fixed_text(dialog_model, "status_title", "Status", 8, 8, 50, 10)
        self._add_fixed_text(dialog_model, "status_value", "", 8, 18, 330, 18, multiline=True)
        self._add_image(dialog_model, "pairing_qr_value", 8, 42, 102, 102)
        self._add_fixed_text(dialog_model, "pairing_title", "Phone Pairing", 118, 42, 92, 10)
        self._add_fixed_text(
            dialog_model,
            "pairing_route_value",
            "",
            118,
            54,
            220,
            18,
            multiline=True,
        )
        self._add_fixed_text(
            dialog_model,
            "pairing_hint_value",
            "",
            118,
            76,
            220,
            36,
            multiline=True,
        )
        self._add_fixed_text(dialog_model, "relay_title", "Relay Status", 118, 116, 66, 10)
        self._add_fixed_text(dialog_model, "relay_state_value", "", 118, 126, 220, 12)
        self._add_fixed_text(dialog_model, "warning_title", "Issues", 8, 148, 52, 10)
        self._add_fixed_text(dialog_model, "warning_value", "", 8, 158, 330, 18, multiline=True)
        self._add_fixed_text(dialog_model, "session_value", "", 8, 180, 330, 10)
        self._add_fixed_text(dialog_model, "manual_link_title", "Manual Link", 8, 194, 58, 10)
        self._add_edit(dialog_model, "manual_link_value", "", 72, 192, 266, 12, readonly=True)
        self._add_fixed_text(dialog_model, "howto_title", "How to Use", 8, 210, 60, 10)
        self._add_fixed_text(
            dialog_model,
            "howto_value",
            "",
            8,
            220,
            330,
            28,
            multiline=True,
        )
        self._add_fixed_text(dialog_model, "route_title", "Pairing Route", 8, 252, 68, 10)
        self._add_route_list_box(
            dialog_model,
            "route_value",
            normalize_preferred_route(DEFAULT_PREFERRED_ROUTE),
            82,
            250,
            156,
            14,
        )
        self._add_fixed_text(dialog_model, "local_port_title", "Local Port", 246, 252, 40, 10)
        self._add_edit(dialog_model, "local_port_value", "", 292, 250, 46, 12)
        self._add_checkbox(dialog_model, "local_value", "Enable local", 8, 270, 82, 10)
        self._add_checkbox(dialog_model, "ipv6_value", "Enable direct IPv6", 96, 270, 108, 10)
        self._add_checkbox(dialog_model, "relay_value", "Enable relay", 222, 270, 70, 10)
        self._add_fixed_text(dialog_model, "relay_url_title", "Relay Server", 8, 288, 58, 10)
        self._add_edit(dialog_model, "relay_url_value", "", 72, 286, 266, 12)
        self._add_button(dialog_model, "stop_button", "Stop", 8, 310, 44, 14)
        self._add_button(dialog_model, "save_button", "Save", 58, 310, 44, 14)
        self._add_button(dialog_model, "start_button", "Start", 158, 310, 44, 14)
        self._add_button(dialog_model, "open_button", "Open", 208, 310, 44, 14)
        self._add_button(dialog_model, "close_button", "Close", 294, 310, 44, 14)

        dialog = self.smgr.createInstanceWithContext(
            "com.sun.star.awt.UnoControlDialog",
            self.ctx,
        )
        dialog.setModel(dialog_model)
        toolkit = self.smgr.createInstanceWithContext("com.sun.star.awt.ExtToolkit", self.ctx)
        dialog.setVisible(False)
        dialog.createPeer(toolkit, None)
        dialog.setTitle("Impress Remote")
        return dialog

    def _add_listeners(self) -> None:
        dialog = self._dialog()
        for control_name in (
            "start_button",
            "stop_button",
            "open_button",
            "save_button",
            "close_button",
        ):
            control = dialog.getControl(control_name)
            listener = DialogButtonListener(self)
            control.addActionListener(listener)
            self.listeners[control_name] = listener
        route_control = dialog.getControl("route_value")
        route_listener = DialogItemListener(self)
        route_control.addItemListener(route_listener)
        self.item_listeners["route_value"] = route_listener
        for control_name in ("local_value", "ipv6_value", "relay_value"):
            control = dialog.getControl(control_name)
            listener = DialogItemListener(self)
            control.addItemListener(listener)
            self.item_listeners[control_name] = listener
        for control_name in ("relay_url_value", "local_port_value"):
            control = dialog.getControl(control_name)
            listener = DialogTextListener(self)
            control.addTextListener(listener)
            self.text_listeners[control_name] = listener

    def _remove_listeners(self) -> None:
        dialog = self._dialog()
        for control_name, listener in self.listeners.items():
            control = dialog.getControl(control_name)
            control.removeActionListener(listener)
        self.listeners = {}
        for control_name, listener in self.item_listeners.items():
            control = dialog.getControl(control_name)
            control.removeItemListener(listener)
        self.item_listeners = {}
        for control_name, listener in self.text_listeners.items():
            control = dialog.getControl(control_name)
            control.removeTextListener(listener)
        self.text_listeners = {}

    def _set_label(self, name: str, value: str) -> None:
        self._dialog_model().getByName(name).Label = value

    def _set_text(self, name: str, value: str) -> None:
        self._dialog_model().getByName(name).Text = value

    def _get_text(self, name: str) -> str:
        return str(self._dialog_model().getByName(name).Text)

    def _set_checkbox(self, name: str, checked: bool) -> None:
        self._dialog_model().getByName(name).State = 1 if checked else 0

    def _get_checkbox(self, name: str) -> bool:
        return bool(self._dialog_model().getByName(name).State)

    def _set_route_selection(self, name: str, route: str) -> None:
        route_keys = tuple(ROUTE_LABELS)
        try:
            selected_index = route_keys.index(route)
        except ValueError:
            selected_index = route_keys.index(DEFAULT_PREFERRED_ROUTE)
        model = self._dialog_model().getByName(name)
        model.SelectedItems = (selected_index,)

    def _selected_route(self, fallback: str = DEFAULT_PREFERRED_ROUTE) -> str:
        model = self._dialog_model().getByName("route_value")
        selected_items = tuple(getattr(model, "SelectedItems", ()))
        if selected_items:
            try:
                selected_index = int(selected_items[0])
            except (TypeError, ValueError):
                selected_index = -1
            route_keys = tuple(ROUTE_LABELS)
            if 0 <= selected_index < len(route_keys):
                return route_keys[selected_index]
        return normalize_preferred_route(fallback, fallback)

    def _set_qr_image(self, pairing_url: str) -> None:
        image_model = self._dialog_model().getByName("pairing_qr_value")
        self._cleanup_qr_image()
        self.qr_error = ""
        if not pairing_url:
            try:
                image_model.ImageURL = ""
            except Exception:
                pass
            return
        try:
            from impress_remote.qr import export_qr_png_path

            image_path = export_qr_png_path(self.ctx, pairing_url)
            self.qr_image_path = image_path
            image_model.ImageURL = image_path.resolve().as_uri()
        except Exception as exc:
            self.qr_error = str(exc)
            try:
                image_model.ImageURL = ""
            except Exception:
                pass

    def _cleanup_qr_image(self) -> None:
        if self.qr_image_path is None:
            return
        try:
            self.qr_image_path.unlink(missing_ok=True)
        except OSError:
            pass
        self.qr_image_path = None

    def _refresh_pairing_preview(self, snapshot: dict[str, Any] | None = None) -> None:
        if snapshot is None:
            snapshot = cast(dict[str, Any], self.handler.runtime_snapshot())
        connection = cast(dict[str, Any], snapshot["connection"])
        self.preview_error = ""
        try:
            pairing = self.handler.preview_pairing_target(
                self._draft_payload(),
                self._selected_route(),
            )
        except ValueError as exc:
            self.preview_error = str(exc)
            pairing = self.handler.pairing_target(self._selected_route())
        self._set_qr_image(pairing["selectedUrl"])
        self._set_label(
            "pairing_route_value",
            self._pairing_route_text(pairing, bool(snapshot["running"])),
        )
        self._set_label(
            "pairing_hint_value",
            self._pairing_hint_text(pairing, connection),
        )
        self._set_label(
            "howto_value",
            self._how_to_use_text(pairing, bool(snapshot["running"])),
        )
        self._set_text(
            "manual_link_value",
            pairing["selectedUrl"] or "Unavailable for the current route.",
        )

    def _pairing_route_text(self, pairing: dict[str, str], running: bool) -> str:
        if not running:
            return "QR code is inactive until the remote is started."
        if pairing["selectedRoute"]:
            if pairing["requestedRoute"] == "auto":
                return f"Current route: {pairing['selectedLabel']}"
            return f"Manual route: {pairing['selectedLabel']}"
        if pairing["requestedRoute"] == "auto":
            return "Auto route could not find a working connection path."
        return "The selected pairing route is unavailable."

    def _pairing_hint_text(self, pairing: dict[str, str], connection: dict[str, Any]) -> str:
        if self.preview_error:
            return f"{pairing['hint']} Draft settings error: {self.preview_error}"
        if self.qr_error:
            return f"{pairing['hint']} QR generation failed: {self.qr_error}"
        if pairing["selectedUrl"]:
            return pairing["hint"]
        if connection["relayStatus"] == "error" and connection["relayLastError"]:
            return f"{pairing['hint']} Relay error: {connection['relayLastError']}"
        return pairing["hint"]

    def _how_to_use_text(self, pairing: dict[str, str], running: bool) -> str:
        if not running:
            return (
                "Click Start, keep the phone on the same Wi-Fi or hotspot, then scan "
                "the QR code. Use Manual Link if scanning fails."
            )
        if pairing["selectedRoute"] in {"", "local"} or pairing["requestedRoute"] == "auto":
            return (
                "Local mode is recommended. Keep the phone on the same Wi-Fi or hotspot, "
                "then scan the QR code or open the Manual Link."
            )
        if pairing["selectedRoute"] == "ipv6":
            return (
                "Use Direct IPv6 only if local mode does not work. Scan the QR code or "
                "open the Manual Link on the phone."
            )
        if pairing["selectedRoute"] == "relay":
            return (
                "Use Relay only when local mode does not work. Save the relay server, "
                "start the remote, then scan the QR code or open the Manual Link."
            )
        return (
            "Use local mode first. If it does not work on your network, try Direct IPv6 "
            "or Relay from the Pairing Route menu."
        )

    def _relay_state_text(self, connection: dict[str, Any]) -> str:
        relay_status = str(connection["relayStatus"])
        relay_url = str(connection["relayUrl"])
        if relay_status == "connected":
            return "Relay connected and ready."
        if relay_status == "connecting":
            return "Relay is connecting."
        if relay_status == "error":
            detail = str(connection["relayLastError"]).strip()
            return f"Relay error: {detail}" if detail else "Relay reported an error."
        if relay_url and connection["relayEnabled"]:
            return "Relay is configured but waiting for the runtime."
        if relay_url:
            return "Relay server saved but currently disabled."
        return "No relay server configured."

    def _warning_text(self, connection: dict[str, Any]) -> str:
        warnings = cast(list[str], connection["listenerWarnings"])
        if warnings:
            return str(warnings[0])
        return "No runtime warnings."

    def _issues_text(self, snapshot: dict[str, Any], connection: dict[str, Any]) -> str:
        issues: list[str] = []
        last_error = str(snapshot.get("lastError", "")).strip()
        if last_error:
            issues.append(last_error)
        warning = self._warning_text(connection)
        if warning != "No runtime warnings.":
            issues.append(warning)
        if bool(connection.get("configPendingRestart")):
            issues.append("Restart the remote to apply the saved listener changes.")
        return " ".join(issues) if issues else "No current issues."

    def _draft_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "enableLocalListener": self._get_checkbox("local_value"),
            "enableIpv6Direct": self._get_checkbox("ipv6_value"),
            "enableRelay": self._get_checkbox("relay_value"),
            "relayUrl": self._get_text("relay_url_value").strip(),
            "preferredRoute": self._selected_route(),
        }
        local_port_text = self._get_text("local_port_value").strip()
        if local_port_text.isdigit() and 1 <= int(local_port_text) <= 65535:
            payload["localPort"] = int(local_port_text)
        return payload

    def _has_unsaved_transport_changes(self) -> bool:
        snapshot = cast(dict[str, Any], self.handler.runtime_snapshot())
        config = cast(dict[str, Any], snapshot["config"])
        draft = self._draft_payload()
        for key in (
            "localPort",
            "enableLocalListener",
            "enableIpv6Direct",
            "enableRelay",
            "relayUrl",
        ):
            if key in draft and draft[key] != config.get(key):
                return True
        return False

    def _dialog(self) -> Any:
        if self.dialog is None:
            raise RuntimeError("Dialog is not initialized.")
        return self.dialog

    def _dialog_model(self) -> Any:
        return self._dialog().getModel()

    def _add_fixed_text(
        self,
        dialog_model,
        name: str,
        label: str,
        x: int,
        y: int,
        width: int,
        height: int,
        multiline: bool = False,
    ) -> None:
        control = dialog_model.createInstance("com.sun.star.awt.UnoControlFixedTextModel")
        control.Name = name
        control.Label = label
        control.PositionX = x
        control.PositionY = y
        control.Width = width
        control.Height = height
        control.MultiLine = multiline
        dialog_model.insertByName(name, control)

    def _add_edit(
        self,
        dialog_model,
        name: str,
        text: str,
        x: int,
        y: int,
        width: int,
        height: int,
        readonly: bool = False,
    ) -> None:
        control = dialog_model.createInstance("com.sun.star.awt.UnoControlEditModel")
        control.Name = name
        control.Text = text
        control.PositionX = x
        control.PositionY = y
        control.Width = width
        control.Height = height
        control.ReadOnly = readonly
        dialog_model.insertByName(name, control)

    def _add_checkbox(
        self,
        dialog_model,
        name: str,
        label: str,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        control = dialog_model.createInstance("com.sun.star.awt.UnoControlCheckBoxModel")
        control.Name = name
        control.Label = label
        control.PositionX = x
        control.PositionY = y
        control.Width = width
        control.Height = height
        dialog_model.insertByName(name, control)

    def _add_button(
        self,
        dialog_model,
        name: str,
        label: str,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        control = dialog_model.createInstance("com.sun.star.awt.UnoControlButtonModel")
        control.Name = name
        control.Label = label
        control.PositionX = x
        control.PositionY = y
        control.Width = width
        control.Height = height
        dialog_model.insertByName(name, control)

    def _add_image(
        self,
        dialog_model,
        name: str,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        control = dialog_model.createInstance("com.sun.star.awt.UnoControlImageControlModel")
        control.Name = name
        control.PositionX = x
        control.PositionY = y
        control.Width = width
        control.Height = height
        control.Border = 1
        control.ScaleImage = True
        dialog_model.insertByName(name, control)

    def _add_route_list_box(
        self,
        dialog_model,
        name: str,
        route: str,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        control = dialog_model.createInstance("com.sun.star.awt.UnoControlListBoxModel")
        control.Name = name
        control.PositionX = x
        control.PositionY = y
        control.Width = width
        control.Height = height
        control.Dropdown = True
        control.LineCount = len(ROUTE_LABELS)
        control.MultiSelection = False
        control.StringItemList = tuple(ROUTE_LABELS.values())
        control.SelectedItems = (tuple(ROUTE_LABELS).index(route),)
        dialog_model.insertByName(name, control)


def show_remote_settings_dialog(ctx, handler: ImpressRemoteProtocolHandler) -> None:
    RemoteSettingsDialog(ctx, handler).show()
