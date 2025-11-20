# -*- coding: utf-8 -*-
from __future__ import annotations

# GTK
from gi.repository import Gtk

# Gramps
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gui.dialog import OkDialog, WarningDialog

# Plugin deps
import tree
from .constants import APP_KEY, REDIRECT, has_minibrowser

import gedcomx_v1

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext


class AuthMixin:
    def _ensure_session(self) -> bool:
        if tree._fs_session and tree._fs_session.logged:
            return True
        fs_username = self.CONFIG.get("preferences.fs_username")
        fs_pass = self.CONFIG.get("preferences.fs_pass") or ""
        lang = getattr(self, "lang", "en")
        tree._fs_session = gedcomx_v1.FsSession(
            fs_username,
            fs_pass,
            False,
            False,
            2,
            lang,
        )
        client_id = self.CONFIG.get("preferences.fs_client_id")
        if client_id:
            tree._fs_session.client_id = client_id
        return False

    def _login_minibrowser(self) -> bool:
        Browser = None
        if has_minibrowser:
            from minibrowser import miniBrowser as Browser
        else:
            return False

        main = Browser(
            appKey=APP_KEY,
            redirect=REDIRECT,
            username=getattr(tree._fs_session, "username", ""),
        )
        code = getattr(main, "code", None)
        if not code:
            return False

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": "authorization_code",
            "client_id": APP_KEY,
            "code": code,
            "redirect_uri": REDIRECT,
        }
        r = tree._fs_session.post_url(
            "https://ident.familysearch.org/cis-web/oauth2/v3/token",
            data,
            headers,
        )
        if not r:
            return False
        try:
            j = r.json()
        except Exception:
            j = None
        if j and j.get("access_token"):
            tree._fs_session.access_token = j["access_token"]
            tree._fs_session.logged = True
            tree._fs_session.status = gedcomx_v1.fs_session.STATUS_CONNECTED
            return True
        return False

    @classmethod
    def ensure_session(cls, caller=None, verbosity=5) -> bool:
        """
        Ensure a global FamilySearch session exists and is authenticated when possible.
        Returns True if a session exists (and is logged-in when mini-browser auth runs).
        """

        # Already logged in?
        if getattr(tree, "_fs_session", None) and getattr(tree._fs_session, "logged", False):
            return True

        # Path A: we have a UI 'caller' with CONFIG; try mixin helpers
        if caller and hasattr(caller, "CONFIG"):
            try:
                # Use the mixin's instance helpers through the class
                cls._ensure_session(caller)
                if not getattr(tree._fs_session, "logged", False):
                    return bool(cls._login_minibrowser(caller))
                return True
            except AttributeError:
                # If caller doesn't have the mixin methods, fall through to Path B
                pass

        # Path B: headless/session bootstrap via class-level CONFIG
        if not getattr(tree, "_fs_session", None):
            lang = getattr(cls, "lang", "en")
            sn = cls.CONFIG.get("preferences.fs_username") or ""
            pw = cls.CONFIG.get("preferences.fs_pass") or ""
            tree._fs_session = gedcomx_v1.FsSession(
                sn,
                pw,
                verbosity >= 3,
                False,
                2,
                (lang or "en")[:2],
            )
            client_id = cls.CONFIG.get("preferences.fs_client_id") or ""
            if client_id:
                tree._fs_session.client_id = client_id

        # If we got here, at least a session object exists
        return bool(tree._fs_session)

    def _on_login(self, _btn):
        self._ensure_session()
        ok = self._login_minibrowser()
        if ok:
            OkDialog(_("Logged in to FamilySearch."))
        else:
            WarningDialog(_("Login failed."))
        self._refresh_status()
