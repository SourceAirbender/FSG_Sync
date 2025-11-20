from __future__ import annotations

import os
from typing import List, Optional

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.0")
from gi.repository import Gtk, WebKit2, GLib


class SourceImageBrowser:
    """
    Modal browser for grabbing image files from a source page.
    - Prompts user to pick a download directory (once per session).
    - Intercepts WebKit downloads and saves to that directory.
    - Tracks all saved files and returns them on close.
    """

    def __init__(
        self,
        url: str,
        parent_window: Optional[Gtk.Window] = None,
        start_dir: Optional[str] = None,
        title: str = "Add Source Image",
    ):
        self.url = url or "about:blank"
        self.parent_window = parent_window
        self.download_dir: Optional[str] = start_dir
        self.saved_files: List[str] = []
        self._handlers: list[tuple[object, int]] = []
        self._ctx = None

        self.dialog = Gtk.Dialog(
            title=title,
            transient_for=parent_window,
            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
        )
        self.dialog.add_button("_Close", Gtk.ResponseType.CLOSE)
        self.dialog.set_default_size(1024, 800)

        # Top hint + choose dir button
        header = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
            margin_top=6,
            margin_bottom=6,
            margin_start=6,
            margin_end=6,
        )
        self.lbl_dir = Gtk.Label(xalign=0)
        # 3 == Gtk.EllipsizeMode.END, kept numeric to avoid extra import
        self.lbl_dir.set_ellipsize(3)
        btn_pick = Gtk.Button(label="Choose download folder…")
        btn_pick.connect("clicked", self._choose_dir)

        header.pack_start(self.lbl_dir, True, True, 0)
        header.pack_end(btn_pick, False, False, 0)

        # WebView inside scroller
        self.webview = WebKit2.WebView()
        sc = Gtk.ScrolledWindow()
        sc.add(self.webview)

        # Footer (progress / info)
        self.info = Gtk.Label(xalign=0)
        self.info.set_margin_top(4)
        self.info.set_margin_bottom(6)
        self.info.set_margin_start(6)
        self.info.set_margin_end(6)

        vbox = self.dialog.get_content_area()
        vbox.set_spacing(0)
        vbox.pack_start(header, False, False, 0)
        vbox.pack_start(sc, True, True, 0)
        vbox.pack_end(self.info, False, False, 0)

        self._wire_downloads()
        if not self.download_dir:
            self._choose_dir()
        self._refresh_dir_label()

        try:
            self.webview.load_uri(self.url)
        except Exception:
            pass

    # ---- public API -------------------------------------------------------

    def run(self) -> List[str]:
        self.dialog.show_all()
        self.dialog.run()
        self._teardown()
        return self.saved_files

    # ---- internals --------------------------------------------------------

    def _wire_downloads(self) -> None:
        try:
            self._ctx = self.webview.get_context()
            h = self._ctx.connect("download-started", self._on_download_started)
            self._handlers.append((self._ctx, h))
        except Exception:
            pass

    def _on_download_started(self, _ctx, download: WebKit2.Download) -> None:
        # Ask for dir if not set
        if not self.download_dir:
            self._choose_dir()
            self._refresh_dir_label()
            if not self.download_dir:
                # Cancel the download if user declined
                try:
                    download.cancel()
                except Exception:
                    pass
                return

        download.connect("decide-destination", self._on_decide_destination)
        download.connect("finished", self._on_finished)
        download.connect("failed", self._on_failed)
        download.connect("received-data", self._on_progress)

    def _on_decide_destination(self, download: WebKit2.Download, suggested_filename: str) -> bool:
        fname = suggested_filename or "download.bin"
        dest_path = self._unique_path(os.path.join(self.download_dir, fname))
        try:
            dest_uri = GLib.filename_to_uri(dest_path)
        except Exception:
            dest_uri = "file://" + dest_path
        try:
            download.set_destination(dest_uri)
        except Exception:
            pass
        download._dest_path = dest_path  # type: ignore[attr-defined]
        return True

    def _on_progress(self, download: WebKit2.Download, _received) -> None:
        try:
            t = download.get_estimated_progress() * 100.0
            self.info.set_text(f"Downloading… {t:0.0f}%")
        except Exception:
            pass

    def _on_finished(self, download: WebKit2.Download) -> None:
        path = getattr(download, "_dest_path", None)
        if path and os.path.exists(path):
            self.saved_files.append(path)
            self.info.set_text(
                f"Saved: {os.path.basename(path)}  –  {len(self.saved_files)} file(s) total."
            )

    def _on_failed(self, download: WebKit2.Download, _error) -> None:
        self.info.set_text("Download failed.")

    def _choose_dir(self, *_):
        dlg = Gtk.FileChooserDialog(
            title="Choose download folder",
            parent=self.dialog,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
            buttons=(
                "_Cancel",
                Gtk.ResponseType.CANCEL,
                "_Select",
                Gtk.ResponseType.OK,
            ),
        )
        if self.download_dir and os.path.isdir(self.download_dir):
            dlg.set_current_folder(self.download_dir)
        resp = dlg.run()
        if resp == Gtk.ResponseType.OK:
            self.download_dir = dlg.get_filename()
        dlg.destroy()
        self._refresh_dir_label()

    def _refresh_dir_label(self) -> None:
        path = self.download_dir or "(no folder selected)"
        self.lbl_dir.set_text(f"Download folder: {path}")

    def _unique_path(self, path: str) -> str:
        if not os.path.exists(path):
            return path
        root, ext = os.path.splitext(path)
        i = 2
        while True:
            candidate = f"{root} ({i}){ext}"
            if not os.path.exists(candidate):
                return candidate
            i += 1

    def _teardown(self) -> None:
        # Disconnect signals to avoid WebKit shutdown warnings
        for obj, hid in self._handlers:
            try:
                obj.disconnect(hid)
            except Exception:
                pass
        try:
            self.dialog.destroy()
        except Exception:
            pass


def pick_images(
    url: str,
    parent_window=None,
    start_dir: Optional[str] = None,
    title: str = "Add Source Image",
) -> List[str]:
    """
    Convenience wrapper: launches the modal browser and returns saved file paths.
    """
    b = SourceImageBrowser(url, parent_window=parent_window, start_dir=start_dir, title=title)
    return b.run()
