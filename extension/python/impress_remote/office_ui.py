# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import threading
import webbrowser
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

import unohelper
from impress_remote.config import (
    DEFAULT_PREFERRED_ROUTE,
    ROUTE_LABELS,
    normalize_preferred_route,
    route_label,
)
from impress_remote.localization import translate

if TYPE_CHECKING:
    from impress_remote.component import ImpressRemoteProtocolHandler


class _XActionListenerBase:
    def disposing(self, _event) -> None:
        return None

    def actionPerformed(self, action_event) -> None:
        return None


class _XItemListenerBase:
    def disposing(self, _event) -> None:
        return None

    def itemStateChanged(self, item_event) -> None:
        return None


if not TYPE_CHECKING:
    try:
        from com.sun.star.awt import XActionListener as _XActionListenerBase  # pyright: ignore[reportMissingImports]
    except Exception:
        pass
    try:
        from com.sun.star.awt import XItemListener as _XItemListenerBase  # pyright: ignore[reportMissingImports]
    except Exception:
        pass


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


class _PlainTextTransferable(unohelper.Base):
    def __init__(self, text: str):
        self.text = text
        self._flavor = self._create_plain_text_flavor()

    def getTransferData(self, flavor):
        if self.isDataFlavorSupported(flavor):
            return self.text
        raise ValueError("Unsupported clipboard flavor")

    def getTransferDataFlavors(self):
        return (self._flavor,)

    def isDataFlavorSupported(self, flavor) -> bool:
        return str(getattr(flavor, "MimeType", "")) == "text/plain;charset=utf-16"

    def _create_plain_text_flavor(self):
        try:
            import uno  # pyright: ignore[reportMissingImports]

            flavor = cast(Any, uno.createUnoStruct("com.sun.star.datatransfer.DataFlavor"))
        except Exception:
            flavor = cast(Any, type("DataFlavor", (), {})())
        flavor.MimeType = "text/plain;charset=utf-16"
        flavor.HumanPresentableName = "Text"
        return flavor


def copy_text_to_clipboard(ctx, text: str) -> bool:
    if not text:
        return False
    try:
        clipboard = _service_manager(ctx).createInstanceWithContext(
            "com.sun.star.datatransfer.clipboard.SystemClipboard",
            ctx,
        )
        clipboard.setContents(_PlainTextTransferable(text), None)
        return True
    except Exception:
        pass
    try:
        if sys.platform == "darwin":
            subprocess.run(["pbcopy"], input=text, text=True, check=True)
            return True
        if sys.platform.startswith("linux"):
            subprocess.run(["xclip", "-selection", "clipboard"], input=text, text=True, check=True)
            return True
        if sys.platform == "win32":
            subprocess.run(["clip"], input=text, text=True, check=True)
            return True
    except Exception:
        return False
    return False


class CopyTextListener(unohelper.Base, _XActionListenerBase):
    def __init__(self, ctx, text: str):
        self.ctx = ctx
        self.text = text

    def disposing(self, _event):
        return None

    def actionPerformed(self, action_event):
        del action_event
        copy_text_to_clipboard(self.ctx, self.text)


def _file_url_to_path(value: str) -> Path:
    if value.startswith("file://"):
        parsed = urlparse(value)
        return Path(url2pathname(unquote(parsed.path))).resolve()
    return Path(value).expanduser().resolve()


def choose_export_directory(ctx, title: str) -> Path:
    try:
        picker = _service_manager(ctx).createInstanceWithContext(
            "com.sun.star.ui.dialogs.FolderPicker",
            ctx,
        )
        if hasattr(picker, "setTitle"):
            picker.setTitle(title)
        result = picker.execute()
        if int(result) == 1:
            directory = picker.getDirectory()
            if directory:
                return _file_url_to_path(str(directory))
    except Exception:
        pass

    from impress_remote.resources import default_export_directory

    return default_export_directory()


def show_error_message(ctx, message: str, title: str | None = None, details: str = "") -> None:
    if not message:
        return
    title = title or translate("app.title")
    diagnostic_text = message if not details else f"{message}\n\n{details}"
    try:
        smgr = _service_manager(ctx)
        dialog_model = smgr.createInstanceWithContext(
            "com.sun.star.awt.UnoControlDialogModel",
            ctx,
        )
        dialog_model.PositionX = 50
        dialog_model.PositionY = 50
        dialog_model.Width = 220
        dialog_model.Height = 132
        dialog_model.Closeable = True
        dialog_model.Sizeable = True

        label = dialog_model.createInstance("com.sun.star.awt.UnoControlFixedTextModel")
        label.Name = "message_label"
        label.Label = translate("office.error.copyable")
        label.PositionX = 8
        label.PositionY = 8
        label.Width = 204
        label.Height = 14
        label.MultiLine = True
        dialog_model.insertByName("message_label", label)

        log = dialog_model.createInstance("com.sun.star.awt.UnoControlEditModel")
        log.Name = "diagnostic_text"
        log.Text = diagnostic_text
        log.PositionX = 8
        log.PositionY = 26
        log.Width = 204
        log.Height = 78
        log.ReadOnly = True
        log.MultiLine = True
        log.VScroll = True
        log.HScroll = True
        dialog_model.insertByName("diagnostic_text", log)

        copy_button = dialog_model.createInstance("com.sun.star.awt.UnoControlButtonModel")
        copy_button.Name = "copy_button"
        copy_button.Label = translate("office.button.copyError")
        copy_button.PositionX = 92
        copy_button.PositionY = 112
        copy_button.Width = 70
        copy_button.Height = 14
        dialog_model.insertByName("copy_button", copy_button)

        close_button = dialog_model.createInstance("com.sun.star.awt.UnoControlButtonModel")
        close_button.Name = "close_button"
        close_button.Label = translate("common.close")
        close_button.PositionX = 168
        close_button.PositionY = 112
        close_button.Width = 44
        close_button.Height = 14
        close_button.PushButtonType = 2
        dialog_model.insertByName("close_button", close_button)

        dialog = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialog", ctx)
        dialog.setModel(dialog_model)
        toolkit = smgr.createInstanceWithContext("com.sun.star.awt.ExtToolkit", ctx)
        dialog.setVisible(False)
        dialog.createPeer(toolkit, None)
        dialog.setTitle(title)
        copy_listener = CopyTextListener(ctx, diagnostic_text)
        copy_control = dialog.getControl("copy_button")
        copy_control.addActionListener(copy_listener)
        try:
            dialog.execute()
        finally:
            try:
                copy_control.removeActionListener(copy_listener)
            except Exception:
                pass
            dialog.dispose()
    except Exception:
        try:
            desktop = _service_manager(ctx).createInstanceWithContext(
                "com.sun.star.frame.Desktop",
                ctx,
            )
            frame = desktop.getCurrentFrame() if hasattr(desktop, "getCurrentFrame") else None
            window = frame.getContainerWindow() if frame is not None else None
            parent = window.getPeer() if window is not None and hasattr(window, "getPeer") else None
            toolkit = _service_manager(ctx).createInstanceWithContext(
                "com.sun.star.awt.Toolkit", ctx
            )
            message_box = toolkit.createMessageBox(parent, 3, 1, title, diagnostic_text)
            message_box.execute()
        except Exception:
            return


class DialogButtonListener(unohelper.Base, _XActionListenerBase):
    def __init__(self, dialog):
        self.dialog = dialog

    def disposing(self, _event):
        return None

    def actionPerformed(self, action_event):
        control_name = action_event.Source.getModel().Name
        self.dialog.handle_action(control_name)


class DialogItemListener(unohelper.Base, _XItemListenerBase):
    def __init__(self, dialog):
        self.dialog = dialog

    def disposing(self, _event):
        return None

    def itemStateChanged(self, item_event):
        control_name = item_event.Source.getModel().Name
        self.dialog.handle_item_change(control_name)


class RemoteDialogBase:
    def __init__(self, ctx, handler: ImpressRemoteProtocolHandler):
        self.ctx = ctx
        self.handler = handler
        self.smgr = _service_manager(ctx)
        self.dialog: Any | None = None

    def _create_dialog_shell(self, width: int, height: int, title: str):
        dialog_model = self.smgr.createInstanceWithContext(
            "com.sun.star.awt.UnoControlDialogModel",
            self.ctx,
        )
        dialog_model.PositionX = 40
        dialog_model.PositionY = 40
        dialog_model.Width = width
        dialog_model.Height = height
        dialog_model.Closeable = True
        dialog_model.Sizeable = False

        dialog = self.smgr.createInstanceWithContext(
            "com.sun.star.awt.UnoControlDialog",
            self.ctx,
        )
        dialog.setModel(dialog_model)
        toolkit = self.smgr.createInstanceWithContext("com.sun.star.awt.ExtToolkit", self.ctx)
        dialog.setVisible(False)
        dialog.createPeer(toolkit, None)
        dialog.setTitle(title)
        return dialog

    def _dialog(self) -> Any:
        if self.dialog is None:
            raise RuntimeError(translate("error.dialogNotInitialized"))
        return self.dialog

    def _dialog_model(self) -> Any:
        return self._dialog().getModel()

    def _has_control_model(self, name: str) -> bool:
        return bool(getattr(self._dialog_model(), "hasByName", lambda _name: False)(name))

    def _set_control_visible(self, name: str, visible: bool) -> None:
        if not self._has_control_model(name):
            return
        try:
            self._dialog().getControl(name).setVisible(visible)
        except Exception:
            pass
        try:
            self._dialog_model().getByName(name).EnableVisible = visible
        except Exception:
            pass

    def _set_label(self, name: str, value: str) -> None:
        self._dialog_model().getByName(name).Label = value

    def _set_text(self, name: str, value: str) -> None:
        self._dialog_model().getByName(name).Text = value

    def _get_text(self, name: str) -> str:
        if not self._has_control_model(name):
            return ""
        return str(self._dialog_model().getByName(name).Text)

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
        route_keys: tuple[str, ...] | None = None,
    ) -> None:
        route_keys = route_keys or tuple(ROUTE_LABELS)
        control = dialog_model.createInstance("com.sun.star.awt.UnoControlListBoxModel")
        control.Name = name
        control.PositionX = x
        control.PositionY = y
        control.Width = width
        control.Height = height
        control.Dropdown = True
        control.LineCount = len(route_keys)
        control.MultiSelection = False
        control.StringItemList = tuple(route_label(key) for key in route_keys)
        control.SelectedItems = (route_keys.index(route) if route in route_keys else 0,)
        dialog_model.insertByName(name, control)


class RemotePairingDialog(RemoteDialogBase):
    def __init__(self, ctx, handler: ImpressRemoteProtocolHandler):
        super().__init__(ctx, handler)
        self.qr_error = ""
        self.qr_image_path: Path | None = None
        self.current_pairing_url = ""
        self._last_pairing_error = ""
        self.listeners: dict[str, DialogButtonListener] = {}
        self._closed = threading.Event()
        self._monitor_thread: threading.Thread | None = None

    def show(self) -> None:
        dialog = self._create_dialog()
        self.dialog = dialog
        self._add_listeners()
        self.refresh()
        self._start_monitor()
        try:
            dialog.execute()
        finally:
            self._closed.set()
            if self._monitor_thread is not None:
                self._monitor_thread.join(timeout=1)
            self._remove_listeners()
            self._cleanup_qr_image()
            dialog.dispose()

    def handle_action(self, control_name: str) -> None:
        if control_name != "copy_url_button":
            return
        if not self.current_pairing_url:
            show_error_message(
                self.ctx,
                translate("office.copyUrl.unavailable"),
                translate("office.start.title"),
            )
            return
        if copy_text_to_clipboard(self.ctx, self.current_pairing_url):
            return
        show_error_message(
            self.ctx,
            translate("office.copyUrl.failed"),
            translate("office.start.title"),
            details=self.current_pairing_url,
        )

    def refresh(self) -> None:
        snapshot = cast(dict[str, Any], self.handler.runtime_snapshot())
        connection = cast(dict[str, Any], snapshot["connection"])
        pairing = self.handler.pairing_target()
        self.current_pairing_url = pairing["selectedUrl"]
        self._set_qr_image(pairing["selectedUrl"])
        self._show_pairing_error_if_needed(pairing, connection)

    def _create_dialog(self):
        dialog = self._create_dialog_shell(176, 192, translate("office.start.title"))
        dialog_model = dialog.getModel()
        self._add_image(dialog_model, "pairing_qr_value", 8, 8, 160, 160)
        self._add_button(
            dialog_model,
            "copy_url_button",
            translate("office.button.copyUrl"),
            48,
            172,
            80,
            14,
        )
        return dialog

    def _add_listeners(self) -> None:
        control = self._dialog().getControl("copy_url_button")
        listener = DialogButtonListener(self)
        control.addActionListener(listener)
        self.listeners["copy_url_button"] = listener

    def _remove_listeners(self) -> None:
        for control_name, listener in self.listeners.items():
            try:
                self._dialog().getControl(control_name).removeActionListener(listener)
            except Exception:
                pass
        self.listeners = {}

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

    def _pairing_error_text(
        self,
        pairing: dict[str, str],
        connection: dict[str, Any],
    ) -> str:
        if self.qr_error:
            return translate("office.pairing.qrError", error=self.qr_error)
        if pairing.get("selectedRoute") == "relay":
            relay_error = str(connection.get("relayLastError", "")).strip()
            if relay_error:
                return translate("office.pairing.relayError", error=relay_error)
        return ""

    def _show_pairing_error_if_needed(
        self,
        pairing: dict[str, str],
        connection: dict[str, Any],
    ) -> None:
        message = self._pairing_error_text(pairing, connection)
        if not message or message == self._last_pairing_error:
            return
        self._last_pairing_error = message
        details = "\n".join(
            (
                f"route: {pairing.get('selectedRoute', '')}",
                f"relayStatus: {connection.get('relayStatus', '')}",
                f"relayUrl: {connection.get('relayUrl', '')}",
                f"relaySessionStatusUrl: {connection.get('relaySessionStatusUrl', '')}",
            )
        )
        show_error_message(
            self.ctx,
            message,
            translate("office.start.title"),
            details=details,
        )

    def _start_monitor(self) -> None:
        self._closed.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="impress-remote-pairing-watch",
        )
        self._monitor_thread.start()

    def _monitor_loop(self) -> None:
        while not self._closed.wait(0.35):
            try:
                snapshot = cast(dict[str, Any], self.handler.runtime_snapshot())
            except Exception:
                continue
            connection = cast(dict[str, Any], snapshot["connection"])
            try:
                pairing = self.handler.pairing_target()
                self._show_pairing_error_if_needed(pairing, connection)
            except Exception:
                pass
            if bool(connection.get("clientConnected")) or not bool(snapshot.get("running")):
                try:
                    self._dialog().endExecute()
                except Exception:
                    return
                return


class RemoteHelpDialog(RemoteDialogBase):
    def show(self) -> None:
        dialog = self._create_dialog()
        self.dialog = dialog
        listener = DialogButtonListener(self)
        close_control = dialog.getControl("close_button")
        close_control.addActionListener(listener)
        try:
            dialog.execute()
        finally:
            try:
                close_control.removeActionListener(listener)
            except Exception:
                pass
            dialog.dispose()

    def handle_action(self, control_name: str) -> None:
        if control_name == "close_button":
            self._dialog().endExecute()

    def _create_dialog(self):
        dialog = self._create_dialog_shell(288, 214, translate("office.help.title"))
        dialog_model = dialog.getModel()
        self._add_fixed_text(
            dialog_model,
            "help_intro",
            translate("office.help.intro"),
            8,
            8,
            272,
            28,
            multiline=True,
        )
        self._add_fixed_text(
            dialog_model,
            "help_modes_title",
            translate("office.help.modesTitle"),
            8,
            42,
            272,
            10,
        )
        self._add_fixed_text(
            dialog_model,
            "help_modes_body",
            translate("office.help.modesBody"),
            8,
            54,
            272,
            58,
            multiline=True,
        )
        self._add_fixed_text(
            dialog_model,
            "help_pairing_title",
            translate("office.help.pairingTitle"),
            8,
            118,
            272,
            10,
        )
        self._add_fixed_text(
            dialog_model,
            "help_pairing_body",
            translate("office.help.pairingBody"),
            8,
            130,
            272,
            34,
            multiline=True,
        )
        self._add_fixed_text(
            dialog_model,
            "help_errors_title",
            translate("office.help.errorsTitle"),
            8,
            170,
            272,
            10,
        )
        self._add_fixed_text(
            dialog_model,
            "help_errors_body",
            translate("office.help.errorsBody"),
            8,
            182,
            220,
            24,
            multiline=True,
        )
        self._add_button(dialog_model, "close_button", translate("common.close"), 236, 196, 44, 14)
        return dialog


class RemoteAdvancedOptionsDialog(RemoteDialogBase):
    def __init__(self, ctx, handler: ImpressRemoteProtocolHandler):
        super().__init__(ctx, handler)
        self.listeners: dict[str, DialogButtonListener] = {}
        self.item_listeners: dict[str, DialogItemListener] = {}
        self._updating_route = False

    def show(self) -> None:
        dialog = self._create_dialog()
        self.dialog = dialog
        self._add_listeners()
        self.refresh()
        dialog.execute()
        self._remove_listeners()
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
            if control_name == "help_button":
                RemoteHelpDialog(self.ctx, self.handler).show()
                return
            if control_name == "export_relay_button":
                self._export_resource("relay")
                return
            if control_name == "export_docs_button":
                self._export_resource("docs")
                return
        except Exception as exc:
            message = translate("error.dialogActionFailed", error=exc)
            self.handler.report_runtime_error(message)
            show_error_message(self.ctx, message, details=self._diagnostic_details())
            self.refresh(message)

    def handle_item_change(self, control_name: str) -> None:
        if self._updating_route:
            return
        if control_name == "route_value":
            self._sync_mode_visibility()

    def refresh(self, status_line: str | None = None) -> None:
        snapshot = cast(dict[str, Any], self.handler.runtime_snapshot())
        config = cast(dict[str, Any], snapshot["config"])

        self._set_text("relay_url_value", str(config["relayUrl"]))
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
        self._sync_mode_visibility()

    def _create_dialog(self):
        dialog = self._create_dialog_shell(286, 112, translate("office.settings.title"))
        dialog_model = dialog.getModel()
        self._add_fixed_text(
            dialog_model,
            "route_title",
            translate("office.label.mode"),
            8,
            12,
            50,
            10,
        )
        self._add_route_list_box(
            dialog_model,
            "route_value",
            normalize_preferred_route(DEFAULT_PREFERRED_ROUTE),
            72,
            10,
            184,
            14,
            self._route_keys(),
        )
        self._add_fixed_text(
            dialog_model,
            "relay_url_title",
            translate("office.label.relayServer"),
            8,
            36,
            64,
            10,
        )
        self._add_edit(dialog_model, "relay_url_value", "", 82, 34, 196, 12)
        self._add_fixed_text(
            dialog_model,
            "resources_title",
            translate("office.label.resources"),
            8,
            58,
            58,
            10,
        )
        self._add_button(
            dialog_model,
            "export_relay_button",
            translate("office.button.exportRelay"),
            72,
            56,
            74,
            14,
        )
        self._add_button(
            dialog_model,
            "export_docs_button",
            translate("office.button.exportDocs"),
            150,
            56,
            74,
            14,
        )
        self._add_button(
            dialog_model,
            "help_button",
            translate("office.button.help"),
            8,
            94,
            44,
            14,
        )
        self._add_button(dialog_model, "save_button", translate("common.save"), 186, 94, 44, 14)
        self._add_button(dialog_model, "close_button", translate("common.close"), 236, 94, 44, 14)
        return dialog

    def _add_listeners(self) -> None:
        dialog = self._dialog()
        for control_name in (
            "help_button",
            "save_button",
            "close_button",
            "export_relay_button",
            "export_docs_button",
        ):
            control = dialog.getControl(control_name)
            listener = DialogButtonListener(self)
            control.addActionListener(listener)
            self.listeners[control_name] = listener

        route_control = dialog.getControl("route_value")
        route_listener = DialogItemListener(self)
        route_control.addItemListener(route_listener)
        self.item_listeners["route_value"] = route_listener

    def _remove_listeners(self) -> None:
        dialog = self._dialog()
        for control_name, listener in self.listeners.items():
            dialog.getControl(control_name).removeActionListener(listener)
        self.listeners = {}

        for control_name, listener in self.item_listeners.items():
            dialog.getControl(control_name).removeItemListener(listener)
        self.item_listeners = {}

    def _save_settings(self) -> None:
        payload: dict[str, object] = {"preferredRoute": self._selected_route()}
        if payload["preferredRoute"] == "relay":
            payload["relayUrl"] = self._get_text("relay_url_value").strip()
        snapshot = cast(dict[str, Any], self.handler.runtime_snapshot())
        should_stop = bool(snapshot.get("running")) and self._settings_changed(
            payload,
            cast(dict[str, Any], snapshot.get("config", {})),
        )
        try:
            self.handler.apply_settings(payload, restart_runtime=False)
        except ValueError as exc:
            show_error_message(self.ctx, str(exc), translate("office.settings.title"))
            return
        if should_stop:
            self.handler.stop()
        self._dialog().endExecute()

    def _export_resource(self, kind: str) -> None:
        from impress_remote.resources import export_packaged_resource

        destination = choose_export_directory(self.ctx, translate("office.export.chooseFolder"))
        result = export_packaged_resource(kind, destination)
        if kind == "relay":
            self.refresh(
                translate(
                    "office.export.relayDone",
                    path=result.destination,
                    count=result.entries,
                )
            )
            return
        self.refresh(
            translate(
                "office.export.docsDone",
                path=result.destination,
                count=result.entries,
            )
        )

    def _set_route_selection(self, name: str, route: str) -> None:
        route_keys = self._route_keys()
        try:
            selected_index = route_keys.index(route)
        except ValueError:
            selected_index = route_keys.index(DEFAULT_PREFERRED_ROUTE)
        self._dialog_model().getByName(name).SelectedItems = (selected_index,)

    def _selected_route(self, fallback: str = DEFAULT_PREFERRED_ROUTE) -> str:
        model = self._dialog_model().getByName("route_value")
        selected_items = tuple(getattr(model, "SelectedItems", ()))
        if selected_items:
            try:
                selected_index = int(selected_items[0])
            except (TypeError, ValueError):
                selected_index = -1
            route_keys = self._route_keys()
            if 0 <= selected_index < len(route_keys):
                return route_keys[selected_index]
        return normalize_preferred_route(fallback, fallback)

    def _route_keys(self) -> tuple[str, ...]:
        return tuple(ROUTE_LABELS) or (DEFAULT_PREFERRED_ROUTE,)

    def _sync_mode_visibility(self) -> None:
        relay_selected = self._selected_route() == "relay"
        for name in (
            "relay_url_title",
            "relay_url_value",
            "resources_title",
            "export_relay_button",
            "export_docs_button",
        ):
            self._set_control_visible(name, relay_selected)

    def _settings_changed(self, payload: dict[str, object], config: dict[str, Any]) -> bool:
        if normalize_preferred_route(payload.get("preferredRoute")) != normalize_preferred_route(
            config.get("preferredRoute")
        ):
            return True
        if "relayUrl" in payload and str(payload["relayUrl"]).strip() != str(
            config.get("relayUrl", "")
        ).strip():
            return True
        return False

    def _diagnostic_details(self) -> str:
        try:
            snapshot = cast(dict[str, Any], self.handler.runtime_snapshot())
        except Exception as exc:
            return f"snapshot: unavailable ({exc})"
        connection = cast(dict[str, Any], snapshot.get("connection", {}))
        config = cast(dict[str, Any], snapshot.get("config", {}))
        return "\n".join(
            (
                f"running: {snapshot.get('running')}",
                f"status: {snapshot.get('statusLine')}",
                f"lastError: {snapshot.get('lastError')}",
                f"preferredRoute: {config.get('preferredRoute')}",
                f"pairingRoute: {connection.get('pairingRoute')}",
                f"relayStatus: {connection.get('relayStatus')}",
                f"tunnelStatus: {connection.get('tunnelStatus')}",
                f"ipv6Status: {connection.get('ipv6Status')}",
            )
        )


def show_remote_pairing_dialog(ctx, handler: ImpressRemoteProtocolHandler) -> None:
    RemotePairingDialog(ctx, handler).show()


def show_remote_advanced_dialog(ctx, handler: ImpressRemoteProtocolHandler) -> None:
    RemoteAdvancedOptionsDialog(ctx, handler).show()


def show_remote_settings_dialog(ctx, handler: ImpressRemoteProtocolHandler) -> None:
    show_remote_advanced_dialog(ctx, handler)
