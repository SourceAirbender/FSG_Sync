import gi
gi.require_version("Gtk", "3.0")
try:
    gi.require_version("WebKit2", "4.0")
except ValueError:
    gi.require_version("WebKit2", "4.0")

from gi.repository import Gtk, WebKit2, GLib


class miniBrowser:
    def __init__(self, url=None, username=None, redirect=None, appKey=None):
        self.code = ""
        self.redirect = redirect or ""

        # Build default URL if none provided
        if url is None:
            url = "https://ident.familysearch.org/cis-web/oauth2/v3/authorization?response_type=code"
            if appKey is not None:
                url += "&client_id=" + appKey
            if redirect is not None:
                url += "&redirect_uri=" + redirect
            if username is not None:
                url += "&username=" + username
            # url += "&scope=openid profile country"

        # Window
        self.main_window = Gtk.Window(title="My Browser")
        self.main_window.connect("destroy", Gtk.main_quit)
        self.main_window.set_default_size(800, 800)

        # WebView
        self.web_view = WebKit2.WebView()
        self.web_view.load_uri(url)

        # Keep handler IDs so we can disconnect before teardown
        self._title_handler = self.web_view.connect("notify::title", self._on_title)
        self._uri_handler = self.web_view.connect("notify::uri", self._on_uri)

        # Scroller + container (use VBox for drop-in compatibility)
        scrolled = Gtk.ScrolledWindow()
        scrolled.add(self.web_view)

        try:
            vbox = Gtk.VBox()  # GTK 3 still accepts this alias
        except AttributeError:
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        vbox.pack_start(scrolled, True, True, 0)
        self.main_window.add(vbox)
        self.main_window.show_all()

        Gtk.main()

    # ---- Signal handlers -------------------------------------------------

    def _on_title(self, _widget, _pspec):
        try:
            title = self.web_view.get_title()
            if title:
                self.main_window.set_title(title)
        except Exception:
            pass

    def _on_uri(self, _widget, _pspec):
        try:
            uri = self.web_view.get_uri()
        except Exception:
            uri = None

        if not uri:
            return

        # When we reach the redirect, extract ?code=... and shut down safely.
        if self.redirect and uri.startswith(self.redirect):
            print("change_url:url=" + uri)
            p = uri.find("code=")
            if p > 0:
                self.code = uri[p + 5 :]
                print("change_url:code=" + self.code)

            # Stop loading further navigations
            try:
                self.web_view.stop_loading()
            except Exception:
                pass

            # Disconnect signals before destroying widgets
            try:
                if self._title_handler:
                    self.web_view.disconnect(self._title_handler)
                    self._title_handler = None
                if self._uri_handler:
                    self.web_view.disconnect(self._uri_handler)
                    self._uri_handler = None
            except Exception:
                pass

            # Defer destruction/quit to the GTK idle loop (prevents WebKit aborts)
            GLib.idle_add(self._shutdown)

    # ---- Teardown --------------------------------------------------------

    def _shutdown(self):
        try:
            if self.main_window:
                self.main_window.destroy()
        except Exception:
            pass
        # Ensure the GTK loop exits even if 'destroy' wasn't emitted
        try:
            Gtk.main_quit()
        except Exception:
            pass
        return False  # remove idle handler


if __name__ == "__main__":
    # Simple manual test (replace appKey/redirect as needed)
    miniBrowser(
        appKey="a02j000000KTRjpAAH",
        redirect="https://misbach.github.io/fs-auth/index_raw.html",
        username=None,
    )
