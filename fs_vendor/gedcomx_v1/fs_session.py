# Copyright © 2022 Jean Michault
# Copyright © 2024 Gabriel Rios

# License: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
"""
FamilySearch session 

Thin requests-based client for FamilySearch authentication and HTTP calls.
HARDENED: gracefully handles 204 No Content and empty bodies in get_jsonurl().
"""

import sys
import time
import requests
import urllib3
from typing import Any, Optional

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---- Status constants --------------------------------------------
STATUS_INIT = 0
STATUS_LOGIN = 1
STATUS_CONNECTED = 2
STATUS_PASSWORD_ERROR = -1
STATUS_ERROR = -2

# Global verbosity (0 = quiet); some legacy code expects a global level
VERBOSITY = 1


class FsSession:
    """
    Create and manage a FamilySearch session.

    Args:
        username (str): FamilySearch username.
        password (str): FamilySearch password.
        verbose (bool): If True, writes logs to stderr in addition to logfile.
        logfile (file-like): Optional file-like to write logs to.
        timeout (int): Request timeout/backoff base (seconds).
        language (str): Preferred language (e.g., 'en'), used for Accept-Language.
        client_id (str): FamilySearch OAuth client id.
    """

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        verbose: bool = False,
        logfile: bool | object = False,
        timeout: int = 60,
        language: str | None = None,
        client_id: str | None = None,
    ):
        self.username = username
        self.password = password
        self.verbose = verbose
        self.logfile = logfile
        self.timeout = timeout

        # Current user info (filled by set_current)
        self.fid: Optional[str] = None      # Person ID of current user (compat name)
        self.display_name: Optional[str] = None

        self.counter = 0
        self.language = language
        self.status = STATUS_INIT

        self.session = requests.session()
        try:
            from fake_useragent import UserAgent  # type: ignore
            self.session.headers = {"User-Agent": UserAgent().firefox}
        except Exception:
            self.session.headers = {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
                )
            }

        self.logged = False
        self.client_id = client_id

        # OAuth-related fields (used by login flows)
        self.ip_address = None
        self.redirect_uri = None
        self.state = None
        self.private_key = None
        self.xsrf_token = None
        self.access_token = None

    # --------------------------------------------------------------------- #
    # Logging
    # --------------------------------------------------------------------- #
    def write_log(self, text: str) -> None:
        """Write a line to log and, if verbose or VERBOSITY > 0, to stderr."""
        line = "[%s]: %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), text)
        if self.verbose or VERBOSITY > 0:
            sys.stderr.write(line)
        if self.logfile:
            self.logfile.write(line)

    # --------------------------------------------------------------------- #
    # Login flows (unchanged except minor robustness)
    # --------------------------------------------------------------------- #
    def login_client_credentials(self) -> bool:
        """OAuth client_credentials flow (requires client_id and private key)."""
        self.logged = False
        self.status = STATUS_LOGIN

        if not self.client_id:
            print("client_id required for client_credentials authentication")
            self.status = STATUS_ERROR
            return False
        if not self.private_key:
            print("private key required for client_credentials authentication")
            self.status = STATUS_ERROR
            return False

        timestamp = format(time.time(), ".3f").encode("utf-8")
        import rsa, base64  # type: ignore

        secret = base64.b64encode(rsa.sign(timestamp, self.private_key, "SHA-512"))
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": secret,
        }
        url = "https://ident.familysearch.org/cis-web/oauth2/v3/token"
        r = self.post_url(url, data)
        if VERBOSITY:
            print("client_credentials step, r=%s" % str(r))
            if r is not None:
                try:
                    print("r.text=%s" % r.text)
                except Exception:
                    pass
        if not r:
            print("login failed (no response)")
            self.status = STATUS_ERROR
            return False

        j = r.json()
        if j and j.get("access_token"):
            self.access_token = j["access_token"]
            print("FamilySearch token acquired")
            self.logged = True
            self.status = STATUS_CONNECTED
            return True

        print("login failed")
        self.status = STATUS_ERROR
        return False

    def login_password(self) -> bool:
        """OAuth password grant (requires client_id, username, password)."""
        self.logged = False
        self.status = STATUS_LOGIN
        if not self.client_id:
            print("client_id required for password authentication")
            self.status = STATUS_ERROR
            return False

        data = {
            "grant_type": "password",
            "client_id": self.client_id,
            "username": self.username,
            "password": self.password,
        }
        url = "https://ident.familysearch.org/cis-web/oauth2/v3/token"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        r = self.session.post(url, data, headers=headers, verify=False)
        if VERBOSITY:
            print("password step, r=%s" % str(r))
            print("r.text=%s" % r.text)
        j = r.json()
        if j and j.get("access_token"):
            self.access_token = j["access_token"]
            print("FamilySearch token acquired")
            self.logged = True
            self.status = STATUS_CONNECTED
            return True
        return False

    def login(self) -> None:
        """
        Browser-like login to establish session cookies and xsrf token, then
        set current user info (fid, language, display_name).
        """
        self.logged = False
        self.status = STATUS_LOGIN

        # Step 1: hit FS root to initialize cookies
        self.session.get("https://www.familysearch.org/", verify=False)

        # Step 2: auth kick-off to get XSRF-TOKEN
        r = self.session.get("https://www.familysearch.org/auth/familysearch/login", verify=False)
        self.xsrf_token = self.session.cookies.get("XSRF-TOKEN")
        if self.xsrf_token:
            self.write_log("xsrf=%s" % self.xsrf_token)

        # Step 3: credentials submit
        r = self.session.post(
            "https://ident.familysearch.org/login",
            data={"_csrf": self.xsrf_token, "username": self.username, "password": self.password},
            verify=False,
        )

        # Step 4: follow redirectUrl if present
        try:
            data = r.json()
            if "loginError" in data:
                self.write_log(str(data["loginError"]))
                return
            if "redirectUrl" not in data:
                self.write_log(r.text)
                return
            url = data["redirectUrl"]
            try:
                self.session.get(url, verify=False)
            except requests.exceptions.TooManyRedirects:
                pass
        except ValueError:
            self.write_log("Invalid auth response")
            self.write_log("text=%s" % str(r.text))

        self.set_current()
        if not self.fid:
            self.logged = False

    def login_openid(self, app_key: str, redirect: str) -> bool:
        """
        OpenID-like dance to exchange a code for a token.
        Returns True on success.
        """
        self.logged = False
        self.status = STATUS_LOGIN

        # Step 1: get XSRF token
        self.session.get("https://www.familysearch.org/auth/familysearch/login", verify=False)
        self.xsrf_token = self.session.cookies.get("XSRF-TOKEN")
        if self.xsrf_token:
            self.write_log("xsrf=%s" % self.xsrf_token)

        # Step 2: post username/password
        self.session.post(
            "https://ident.familysearch.org/login",
            data={"_csrf": self.xsrf_token, "username": self.username, "password": self.password},
            verify=False,
        )

        # Step 3: authorization code
        url = (
            "https://ident.familysearch.org/cis-web/oauth2/v3/authorization"
            "?response_type=code&scope=profile%20email%20qualifies_for_affiliate_account%20country"
            f"&client_id={app_key}&redirect_uri={redirect}&username={self.username}"
        )
        print(" url1 = " + url)
        r = self.session.get(url, verify=False)
        loc = r.url
        code = None
        pos = loc.find("code=")
        if pos > 0:
            code = loc[pos + 5 :]
        else:
            print("code not found…")
            return False

        # Step 4: exchange the code
        headers = {"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "authorization_code",
            "client_id": app_key,
            "code": code,
            "redirect_uri": redirect,
        }
        url = "https://ident.familysearch.org/cis-web/oauth2/v3/token"
        r = self.post_url(url, data, headers=headers)
        if VERBOSITY and r:
            print("client_credentials step, r=%s" % str(r))
            print("r.text=%s" % (r.text if hasattr(r, "text") else ""))

        if not r:
            print("login failed")
            self.status = STATUS_PASSWORD_ERROR
            return False

        j = r.json()
        if j and j.get("access_token"):
            self.access_token = j["access_token"]
            print("FamilySearch token acquired")
            self.logged = True
            self.status = STATUS_CONNECTED
            return True

        print("login failed")
        print("r.text=%s" % (r.text if hasattr(r, "text") else ""))
        self.status = STATUS_PASSWORD_ERROR
        return False

    # --------------------------------------------------------------------- #
    # HTTP helpers
    # --------------------------------------------------------------------- #
    def _attach_headers(self, headers: dict | None, wants_json: bool = True) -> dict:
        h = dict(headers or {})
        if wants_json:
            h.setdefault("Accept", "application/x-gedcomx-v1+json")
        if "Accept-Language" not in h and self.language:
            h["Accept-Language"] = self.language
        if self.access_token:
            h["Authorization"] = "Bearer " + self.access_token
        return h

    @staticmethod
    def _api_url(url: str) -> str:
        return url if url.startswith("http") else "https://api.familysearch.org" + url

    def post_url(self, url: str, data: dict | str, headers: dict | None = None):
        if not self.logged and self.status == STATUS_INIT:
            self.login()
        headers = self._attach_headers(headers, wants_json=True)
        url = self._api_url(url)

        attempts = 1
        while True:
            try:
                if attempts > 3:
                    self.status = STATUS_ERROR
                    self.logged = False
                    return None
                attempts += 1
                self.write_log("Downloading :" + url)
                r = self.session.post(
                    url, timeout=self.timeout, headers=headers, data=data, allow_redirects=False, verify=False
                )
            except requests.exceptions.ReadTimeout:
                self.write_log("Read timed out")
                continue
            except requests.exceptions.ConnectionError:
                self.write_log("Connection aborted")
                time.sleep(self.timeout)
                continue

            self.write_log("Status code: %s" % r.status_code)
            if r.status_code == 204:
                self.write_log("headers=" + str(r.headers))
                return r
            if r.status_code == 401:
                self.login()
                continue
            if r.status_code == 400:
                self.write_log("WARNING 400: " + url)
                return None
            if r.status_code in {404, 405, 406, 410, 500}:
                self.write_log("WARNING: " + url)
                self.write_log(str(r))
                return r
            try:
                r.raise_for_status()
            except requests.exceptions.HTTPError:
                self.write_log("HTTPError")
                if r.status_code == 403:
                    try:
                        msg = r.json()["errors"][0].get("message")
                    except Exception:
                        msg = None
                    if msg == "Unable to get ordinances.":
                        self.write_log("Unable to get ordinances. Try LDS account or disable that option.")
                        return "error"
                    self.write_log("WARNING: code 403 from %s %s" % (url, msg or ""))
                    return r
                time.sleep(self.timeout)
                continue
            return r

    def put_url(self, url: str, data: dict | str, headers: dict | None = None):
        if not self.logged and self.status == STATUS_INIT:
            self.login()
        headers = self._attach_headers(headers, wants_json=True)
        url = self._api_url(url)

        attempts = 1
        while True:
            try:
                if attempts > 3:
                    self.status = STATUS_ERROR
                    self.logged = False
                    return None
                attempts += 1
                self.write_log("Downloading :" + url)
                r = self.session.put(
                    url, timeout=self.timeout, headers=headers, data=data, allow_redirects=False, verify=False
                )
            except requests.exceptions.ReadTimeout:
                self.write_log("Read timed out")
                continue
            except requests.exceptions.ConnectionError:
                self.write_log("Connection aborted")
                time.sleep(self.timeout)
                continue

            self.write_log("Status code: %s" % r.status_code)
            if r.status_code == 204:
                self.write_log("headers=" + str(r.headers))
                return r
            if r.status_code == 401:
                self.login()
                continue
            if r.status_code == 400:
                self.write_log("WARNING 400: " + url)
                return None
            if r.status_code in {404, 405, 406, 410, 500}:
                self.write_log("WARNING: " + url)
                self.write_log(str(r))
                return r
            try:
                r.raise_for_status()
            except requests.exceptions.HTTPError:
                self.write_log("HTTPError")
                if r.status_code == 403:
                    try:
                        msg = r.json()["errors"][0].get("message")
                    except Exception:
                        msg = None
                    if msg == "Unable to get ordinances.":
                        self.write_log("Unable to get ordinances. Try LDS account or disable that option.")
                        return "error"
                    self.write_log("WARNING: code 403 from %s %s" % (url, msg or ""))
                    return r
                time.sleep(self.timeout)
                continue
            return r

    def head_url(self, url: str, headers: dict | None = None):
        if not self.logged:
            self.login()
        self.counter += 1
        headers = self._attach_headers(headers, wants_json=True)

        attempts = 1
        while True:
            try:
                if attempts > 3:
                    self.status = STATUS_ERROR
                    self.logged = False
                    return None
                attempts += 1
                full = "https://www.familysearch.org" + url
                self.write_log("Downloading :" + full)
                r = self.session.head(full, timeout=self.timeout, headers=headers, verify=False)
            except requests.exceptions.ReadTimeout:
                self.write_log("Read timed out")
                continue
            except requests.exceptions.ConnectionError:
                self.write_log("Connection aborted")
                time.sleep(self.timeout)
                continue
            if r.status_code == 401:
                self.login()
                continue
            return r

    def get_url(self, url: str, headers: dict | None = None):
        if not self.logged and self.status == STATUS_INIT:
            self.login()
        self.counter += 1
        headers = self._attach_headers(headers, wants_json=True)
        url = self._api_url(url)

        attempts = 0
        while True:
            attempts += 1
            if attempts > 3:
                self.status = STATUS_ERROR
                self.logged = False
                return None
            try:
                self.write_log("Downloading :" + url)
                r = self.session.get(
                    url, timeout=self.timeout, headers=headers, allow_redirects=False, verify=False
                )
            except requests.exceptions.ReadTimeout:
                self.write_log("Read timed out")
                continue
            except requests.exceptions.ConnectionError:
                self.write_log("Connection aborted")
                time.sleep(self.timeout)
                continue

            if r.status_code in (204, 301):
                self.write_log("Status code: %s" % r.status_code)
                self.write_log("headers=" + str(r.headers))
                return r
            if r.status_code == 401:
                # return the 401 response to caller.
                return r
            if r.status_code == 400:
                self.write_log("WARNING 400: " + url)
                return None
            if r.status_code in {404, 405, 406, 410, 500}:
                self.write_log("WARNING: " + url)
                try:
                    self.write_log(r.text)
                except Exception:
                    pass
                return None

            try:
                r.raise_for_status()
            except requests.exceptions.HTTPError:
                self.write_log("HTTPError")
                if r.status_code == 403:
                    try:
                        msg = r.json()["errors"][0].get("message")
                    except Exception:
                        msg = None
                    if msg == "Unable to get ordinances.":
                        self.write_log(
                            "Unable to get ordinances. Try with an LDS account or disable that option."
                        )
                        return "error"
                    self.write_log("WARNING: code 403 from %s %s" % (url, msg or ""))
                    return None
                time.sleep(self.timeout)
                continue
            return r

    # empty-body detection --------------------------------- #
    @staticmethod
    def _response_is_empty_json(r: requests.Response) -> bool:
        """
        Return True if response is a JSON-style request with no body:
        - HTTP 204 No Content, or
        - Content-Length: 0, or
        - r.content is empty / r.text is blank.
        """
        try:
            if r.status_code == 204:
                return True
            clen = r.headers.get("Content-Length")
            if clen is not None and clen.strip() == "0":
                return True
            if not r.content:
                return True
            if hasattr(r, "text") and (r.text is None or r.text.strip() == ""):
                return True
        except Exception:
            pass
        return False

    def get_jsonurl(self, url: str, headers: dict | None = None):
        """
        Retrieve JSON from a FamilySearch URL.
        Returns:
            dict on success,
            {}   on 204/empty body (treated as "no content" without warnings),
            None on non-JSON/HTTP errors,
            'error' for special ordinance 403 case.
        """
        r = self.get_url(url, headers)
        if r is None or r == "error":
            return r  # propagate None or 'error'
        if isinstance(r, requests.Response) and self._response_is_empty_json(r):
            # empty responses (e.g., /notes, /sources) as empty dicts
            return {}

        # try to parse JSON; warn only when there's actual content.
        try:
            return r.json()
        except Exception as e:
            # Only warn if there was a non-empty body that failed to parse.
            body_preview = ""
            try:
                if r.content and len(r.content) > 0:
                    body_preview = (r.content[:200] if len(r.content) > 200 else r.content).decode(errors="ignore")
            except Exception:
                pass
            self.write_log(
                "WARNING: JSON decode failed from %s, error: %s%s"
                % (
                    url,
                    e,
                    ("; body preview: " + body_preview) if body_preview else ""
                )
            )
            return None

    # --------------------------------------------------------------------- #
    # Current user info
    # --------------------------------------------------------------------- #
    def set_current(self) -> None:
        """Retrieve current user ID, name and preferred language."""
        url = "/platform/users/current"
        data = self.get_jsonurl(url)
        if data:
            self.fid = data["users"][0]["personId"]
            if not self.language:
                self.language = data["users"][0]["preferredLanguage"]
            self.display_name = data["users"][0]["displayName"]

    # --------------------------------------------------------------------- #
    # translator hook
    # --------------------------------------------------------------------- #
    def _(self, string: str) -> str:
        """Translate via a 'translations' dict if present (compat)."""
        try:
            if string in translations and self.language in translations[string]:  # type: ignore[name-defined]
                return translations[string][self.language]  # type: ignore[index]
        except Exception:
            pass
        return string
