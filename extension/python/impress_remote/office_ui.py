# SPDX-FileCopyrightText: 2026 Bora Yarkın
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from binascii import crc32
from collections.abc import Sequence
import html
from pathlib import Path
import re
from struct import pack
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname
from zlib import compress
from zipfile import ZipFile

from impress_remote import __version__
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


class _UnoBase:
    pass


if not TYPE_CHECKING:
    try:
        import unohelper as _unohelper  # pyright: ignore[reportMissingImports]

        _UnoBase = _unohelper.Base
    except Exception:
        pass


def _uno_type(type_name: str) -> object:
    try:
        import uno  # pyright: ignore[reportMissingImports]

        return uno.getTypeByName(type_name)
    except Exception:
        return type_name


class _UnoTypeProviderMixin:
    UNO_TYPES: tuple[str, ...] = ()

    def getTypes(self) -> tuple[object, ...]:
        return tuple(_uno_type(type_name) for type_name in self.UNO_TYPES)

    def getImplementationId(self) -> bytes:
        return b""


class _ActionListenerUnoMixin(_UnoTypeProviderMixin):
    UNO_TYPES = ("com.sun.star.awt.XActionListener",)


class _ItemListenerUnoMixin(_UnoTypeProviderMixin):
    UNO_TYPES = ("com.sun.star.awt.XItemListener",)


class _TransferableUnoMixin(_UnoTypeProviderMixin):
    UNO_TYPES = ("com.sun.star.datatransfer.XTransferable",)


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_BLACK = 0
PNG_WHITE = 255


def _service_manager(ctx):
    if hasattr(ctx, "ServiceManager"):
        return ctx.ServiceManager
    return ctx.getServiceManager()


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    return (
        pack(">I", len(data))
        + chunk_type
        + data
        + pack(">I", crc32(chunk_type + data) & 0xFFFFFFFF)
    )


def _matrix_to_png_bytes(
    matrix: Sequence[Sequence[bool | None]],
    box_size: int = 8,
) -> bytes:
    if not matrix or not matrix[0]:
        raise RuntimeError(translate("error.qrEmpty"))

    size = len(matrix)
    width = size * box_size
    rows = bytearray()
    for matrix_row in matrix:
        pixel_row = bytearray()
        for cell in matrix_row:
            color = PNG_BLACK if bool(cell) else PNG_WHITE
            pixel_row.extend([color] * box_size)
        for _ in range(box_size):
            rows.append(0)
            rows.extend(pixel_row)

    ihdr = pack(">IIBBBBB", width, width, 8, 0, 0, 0, 0)
    return b"".join(
        (
            PNG_SIGNATURE,
            _png_chunk(b"IHDR", ihdr),
            _png_chunk(b"IDAT", compress(bytes(rows), level=9)),
            _png_chunk(b"IEND", b""),
        )
    )


def export_qr_png_path(_ctx, payload: str) -> Path:
    if not payload:
        raise RuntimeError(translate("error.noPairingUrl"))

    from qrcode import QRCode, constants

    temp_file = tempfile.NamedTemporaryFile(
        prefix="impress-remote-qr-",
        suffix=".png",
        delete=False,
    )
    temp_file.close()
    output_path = Path(temp_file.name)

    try:
        qr_code = QRCode(
            version=None,
            error_correction=constants.ERROR_CORRECT_M,
            box_size=8,
            border=4,
        )
        qr_code.add_data(payload)
        qr_code.make(fit=True)
        output_path.write_bytes(_matrix_to_png_bytes(qr_code.get_matrix()))
        return output_path
    except Exception:
        try:
            output_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


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


class _PlainTextTransferable(_TransferableUnoMixin, _UnoBase):
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


class CopyTextListener(_ActionListenerUnoMixin, _UnoBase, _XActionListenerBase):
    def __init__(self, ctx, text: str):
        self.ctx = ctx
        self.text = text

    def disposing(self, _event):
        return None

    def actionPerformed(self, action_event):
        del action_event
        copy_text_to_clipboard(self.ctx, self.text)


class ResourceExport:
    def __init__(self, *, kind: str, destination: Path, entries: int) -> None:
        self.kind = kind
        self.destination = destination
        self.entries = entries


RESOURCE_ARCHIVES = {
    "relay": f"impress-remote-relay-python-{__version__}.zip",
}


def _file_url_to_path(value: str) -> Path:
    if value.startswith("file://"):
        parsed = urlparse(value)
        return Path(url2pathname(unquote(parsed.path))).resolve()
    return Path(value).expanduser().resolve()


def _archive_extract_root(archive_path: Path, archive: ZipFile) -> Path:
    file_names = [member.filename for member in archive.infolist() if not member.is_dir()]
    top_level_names = {
        Path(name).parts[0]
        for name in file_names
        if Path(name).parts and Path(name).parts[0] not in {"", ".", ".."}
    }
    if len(top_level_names) == 1 and all(
        len(Path(name).parts) > 1 for name in file_names if Path(name).parts
    ):
        return Path()
    return Path(archive_path.stem)


def default_export_directory() -> Path:
    downloads = Path.home() / "Downloads"
    if downloads.is_dir():
        return downloads
    return Path.home()


def packaged_resource_path(kind: str, module_file: str = __file__) -> Path:
    archive_name = RESOURCE_ARCHIVES.get(kind)
    if archive_name is None:
        raise ValueError(translate("resource.error.unknownKind", kind=kind))

    module_path = _file_url_to_path(module_file)
    packaged_path = module_path.parents[2] / "resources" / archive_name
    if packaged_path.is_file():
        return packaged_path

    source_tree_path = module_path.parents[3] / "dist" / archive_name
    if source_tree_path.is_file():
        return source_tree_path

    raise FileNotFoundError(translate("resource.error.notBundled", name=archive_name))


def packaged_user_guide_path(module_file: str = __file__) -> Path:
    module_path = _file_url_to_path(module_file)
    packaged_path = module_path.parents[2] / "resources" / "user-guide.md"
    if packaged_path.is_file():
        return packaged_path

    source_tree_path = module_path.parents[3] / "docs" / "user-guide.md"
    if source_tree_path.is_file():
        return source_tree_path

    raise FileNotFoundError(translate("resource.error.notBundled", name="user-guide.md"))


def read_packaged_user_guide(module_file: str = __file__) -> str:
    text = packaged_user_guide_path(module_file).read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if not line.startswith("<!-- SPDX-")]
    return "\n".join(lines).strip() + "\n"


def _markdown_inline(value: str) -> str:
    rendered = html.escape(value)
    rendered = re.sub(r"`([^`]+)`", r"<code>\1</code>", rendered)
    rendered = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", rendered)
    return rendered


def _markdown_table(lines: list[str], start: int) -> tuple[str, int]:
    def cells(row: str) -> list[str]:
        return [cell.strip() for cell in row.strip().strip("|").split("|")]

    header = cells(lines[start])
    rows: list[list[str]] = []
    index = start + 2
    while index < len(lines) and "|" in lines[index] and lines[index].strip():
        rows.append(cells(lines[index]))
        index += 1

    parts = ["<table>", "<thead><tr>"]
    parts.extend(f"<th>{_markdown_inline(cell)}</th>" for cell in header)
    parts.append("</tr></thead>")
    if rows:
        parts.append("<tbody>")
        for row in rows:
            parts.append("<tr>")
            parts.extend(f"<td>{_markdown_inline(cell)}</td>" for cell in row)
            parts.append("</tr>")
        parts.append("</tbody>")
    parts.append("</table>")
    return "".join(parts), index


def render_user_guide_html(markdown: str) -> str:
    lines = markdown.splitlines()
    body: list[str] = []
    index = 0
    list_type = ""
    in_code = False
    code_lines: list[str] = []

    def close_list() -> None:
        nonlocal list_type
        if list_type:
            body.append(f"</{list_type}>")
            list_type = ""

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code:
                body.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
                code_lines = []
                in_code = False
            else:
                close_list()
                in_code = True
            index += 1
            continue

        if in_code:
            code_lines.append(line)
            index += 1
            continue

        if not stripped:
            close_list()
            index += 1
            continue

        if (
            "|" in stripped
            and index + 1 < len(lines)
            and re.fullmatch(r"\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*", lines[index + 1])
        ):
            close_list()
            table_html, index = _markdown_table(lines, index)
            body.append(table_html)
            continue

        heading = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if heading:
            close_list()
            level = len(heading.group(1))
            body.append(f"<h{level}>{_markdown_inline(heading.group(2))}</h{level}>")
            index += 1
            continue

        ordered = re.match(r"^\d+\.\s+(.+)$", stripped)
        unordered = re.match(r"^-\s+(.+)$", stripped)
        if ordered or unordered:
            wanted = "ol" if ordered else "ul"
            if list_type != wanted:
                close_list()
                body.append(f"<{wanted}>")
                list_type = wanted
            item = cast(re.Match[str], ordered or unordered).group(1)
            body.append(f"<li>{_markdown_inline(item)}</li>")
            index += 1
            continue

        close_list()
        body.append(f"<p>{_markdown_inline(stripped)}</p>")
        index += 1

    close_list()
    if in_code:
        body.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")

    return (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        "<title>LibreOffice Impress Remote Help</title>"
        "<style>"
        ":root{color-scheme:light dark;font:16px/1.55 Georgia,serif;}"
        "body{max-width:900px;margin:32px auto;padding:0 20px;color:#1b1b18;background:#fbfaf4;}"
        "h1,h2,h3,h4{font-family:Helvetica,Arial,sans-serif;line-height:1.15;margin:1.5em 0 .45em;}"
        "h1{font-size:2.3rem;margin-top:0;}h2{border-top:1px solid #ddd7c8;padding-top:1rem;}"
        "code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;"
        "background:#eee8d8;padding:.1em .3em;border-radius:4px;}"
        "pre{overflow:auto;background:#1f2328;color:#f6f8fa;padding:14px;border-radius:8px;}"
        "pre code{background:transparent;color:inherit;padding:0;}"
        "table{border-collapse:collapse;width:100%;margin:1rem 0;}"
        "th,td{border:1px solid #d8d0bd;padding:8px;text-align:left;vertical-align:top;}"
        "th{background:#eee8d8;}li{margin:.25rem 0;}"
        "@media(prefers-color-scheme:dark){body{background:#181713;color:#efeadc;}"
        "h2{border-color:#3b3529;}code,th{background:#302a20;}th,td{border-color:#4a4234;}}"
        "</style></head><body>"
        + "\n".join(body)
        + "</body></html>"
    )


def write_rendered_user_guide_html(module_file: str = __file__) -> Path:
    output = Path(
        tempfile.NamedTemporaryFile(
            prefix="impress-remote-help-",
            suffix=".html",
            delete=False,
        ).name
    )
    output.write_text(
        render_user_guide_html(read_packaged_user_guide(module_file)),
        encoding="utf-8",
    )
    return output


def open_rendered_user_guide(ctx, module_file: str = __file__) -> bool:
    guide_path = write_rendered_user_guide_html(module_file)
    if open_external_url(ctx, guide_path.resolve().as_uri()):
        return True
    try:
        guide_path.unlink(missing_ok=True)
    except OSError:
        pass
    return False


def export_packaged_resource(
    kind: str,
    destination: Path | None = None,
    module_file: str = __file__,
) -> ResourceExport:
    archive_path = packaged_resource_path(kind, module_file)
    target_dir = (destination or default_export_directory()).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    entries = 0
    with ZipFile(archive_path) as archive:
        extract_root = _archive_extract_root(archive_path, archive)
        for member in archive.infolist():
            if member.is_dir():
                continue
            member_path = Path(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError(translate("resource.error.unsafeArchive", name=member.filename))
            output_path = (target_dir / extract_root / member_path).resolve()
            if not output_path.is_relative_to(target_dir):
                raise ValueError(translate("resource.error.unsafeArchive", name=member.filename))
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, output_path.open("wb") as target:
                target.write(source.read())
            entries += 1

    return ResourceExport(kind=kind, destination=target_dir, entries=entries)


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


class DialogButtonListener(_ActionListenerUnoMixin, _UnoBase, _XActionListenerBase):
    def __init__(self, dialog):
        self.dialog = dialog

    def disposing(self, _event):
        return None

    def actionPerformed(self, action_event):
        control_name = action_event.Source.getModel().Name
        self.dialog.handle_action(control_name)


class DialogItemListener(_ItemListenerUnoMixin, _UnoBase, _XItemListenerBase):
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
        multiline: bool = False,
        vscroll: bool = False,
        hscroll: bool = False,
    ) -> None:
        control = dialog_model.createInstance("com.sun.star.awt.UnoControlEditModel")
        control.Name = name
        control.Text = text
        control.PositionX = x
        control.PositionY = y
        control.Width = width
        control.Height = height
        control.ReadOnly = readonly
        control.MultiLine = multiline
        control.VScroll = vscroll
        control.HScroll = hscroll
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
        self._empty_pairing_seen_at = 0.0
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
        self._refresh_pairing_from_snapshot(snapshot, show_pending=True)

    def _create_dialog(self):
        dialog = self._create_dialog_shell(176, 222, translate("office.start.title"))
        dialog_model = dialog.getModel()
        self._add_image(dialog_model, "pairing_qr_value", 8, 8, 160, 160)
        self._add_fixed_text(
            dialog_model,
            "pairing_status_value",
            "",
            8,
            172,
            160,
            22,
            multiline=True,
        )
        self._add_button(
            dialog_model,
            "copy_url_button",
            translate("office.button.copyUrl"),
            48,
            200,
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
        if pairing.get("selectedRoute") == "tunnel":
            tunnel_error = str(connection.get("tunnelLastError", "")).strip()
            tunnel_status = str(connection.get("tunnelStatus", "")).strip()
            if tunnel_error and tunnel_status not in {"connecting", "retrying", "ready"}:
                return translate("localServer.hint.tunnelError", error=tunnel_error)
            if tunnel_status in {"connecting", "retrying", "ready"}:
                return ""
            if (
                not pairing.get("selectedUrl")
                and tunnel_status not in {"connecting", "retrying", "ready"}
            ):
                return str(pairing.get("hint") or translate("error.noPairingUrl"))
        if not pairing.get("selectedUrl"):
            return str(pairing.get("hint") or translate("error.noPairingUrl"))
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
        details = self._pairing_error_details(pairing, connection)
        show_error_message(
            self.ctx,
            message,
            translate("office.start.title"),
            details=details,
        )

    def _refresh_pairing_from_snapshot(
        self,
        snapshot: dict[str, Any],
        *,
        show_pending: bool,
    ) -> None:
        connection = cast(dict[str, Any], snapshot["connection"])
        pairing = self.handler.pairing_target()
        pairing_url = str(pairing.get("selectedUrl", "")).strip()
        if pairing_url != self.current_pairing_url:
            self.current_pairing_url = pairing_url
            self._set_qr_image(pairing_url)
        if pairing_url:
            self._empty_pairing_seen_at = 0.0
            self._set_pairing_status("")
            return
        self._set_pairing_status(self._pairing_status_text(pairing, connection))
        if self._empty_pairing_seen_at <= 0:
            self._empty_pairing_seen_at = time.monotonic()
        if show_pending or time.monotonic() - self._empty_pairing_seen_at >= 2.0:
            self._show_pairing_error_if_needed(pairing, connection)

    def _pairing_status_text(
        self,
        pairing: dict[str, str],
        connection: dict[str, Any],
    ) -> str:
        if pairing.get("selectedRoute") != "tunnel":
            return ""
        tunnel_error = str(connection.get("tunnelLastError", "")).strip()
        tunnel_status = str(connection.get("tunnelStatus", "")).strip()
        if tunnel_error and tunnel_status not in {"connecting", "retrying", "ready"}:
            return ""
        if tunnel_status in {"connecting", "retrying", "ready"}:
            return str(pairing.get("hint") or translate("localServer.hint.tunnelStarting"))
        return ""

    def _set_pairing_status(self, message: str) -> None:
        if not self._has_control_model("pairing_status_value"):
            return
        self._set_label("pairing_status_value", message)
        self._set_control_visible("pairing_status_value", bool(message))

    def _pairing_error_details(
        self,
        pairing: dict[str, str],
        connection: dict[str, Any],
    ) -> str:
        route = pairing.get("selectedRoute", "")
        if route == "relay":
            lines = (
                f"route: {route}",
                f"relayStatus: {connection.get('relayStatus', '')}",
                f"relayUrl: {connection.get('relayUrl', '')}",
                f"relaySessionStatusUrl: {connection.get('relaySessionStatusUrl', '')}",
            )
        elif route == "tunnel":
            lines = (
                f"route: {route}",
                f"tunnelStatus: {connection.get('tunnelStatus', '')}",
                f"tunnelUrl: {connection.get('tunnelUrl', '')}",
                f"tunnelLastError: {connection.get('tunnelLastError', '')}",
            )
        else:
            lines = (f"route: {route}", f"hint: {pairing.get('hint', '')}")
        return "\n".join(lines)

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
            try:
                self._refresh_pairing_from_snapshot(snapshot, show_pending=False)
            except Exception:
                pass
            connection = cast(dict[str, Any], snapshot["connection"])
            if bool(connection.get("clientConnected")) or not bool(snapshot.get("running")):
                try:
                    self._dialog().endExecute()
                except Exception:
                    return
                return


class RemoteHelpDialog(RemoteDialogBase):
    def show(self) -> None:
        if open_rendered_user_guide(self.ctx):
            return
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
        dialog = self._create_dialog_shell(330, 320, translate("office.help.title"))
        dialog_model = dialog.getModel()
        self._add_edit(
            dialog_model,
            "help_guide",
            read_packaged_user_guide(),
            8,
            8,
            314,
            282,
            readonly=True,
            multiline=True,
            vscroll=True,
            hscroll=True,
        )
        self._add_button(dialog_model, "close_button", translate("common.close"), 278, 298, 44, 14)
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
            "relay_package_title",
            translate("office.label.relayPackage"),
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
        destination = choose_export_directory(self.ctx, translate("office.export.chooseFolder"))
        result = export_packaged_resource(kind, destination)
        self.refresh(
            translate(
                "office.export.relayDone",
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
            "relay_package_title",
            "export_relay_button",
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
