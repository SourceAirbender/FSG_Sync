# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from typing import List, Dict, Any

# GTK / WebKit2
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
try:
    gi.require_version("WebKit2", "4.0")
except ValueError:
    try:
        gi.require_version("WebKit2", "4.0")
    except ValueError:
        pass

try:
    from gi.repository import WebKit2
    _has_webkit = True
except Exception:
    WebKit2 = None
    _has_webkit = False

# Gramps
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gui.dialog import WarningDialog
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.lib import Person

# Plugin deps
import fs_utilities
import fs_compare
import fs_tags

import gedcomx_v1

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

class _CaptureTreeModel:
    def __init__(self):
        self._id_counter = 0
        self._nodes: Dict[int, Dict[str, Any]] = {}
        self._roots: List[int] = []

    def clear(self):
        self._id_counter = 0
        self._nodes.clear()
        self._roots.clear()

    def add(self, row: list, node: int | None = None):
        self._id_counter += 1
        nid = self._id_counter
        self._nodes[nid] = {"row": list(row), "children": []}
        if node is None:
            self._roots.append(nid)
        else:
            if node in self._nodes:
                self._nodes[node]["children"].append(nid)
            else:
                self._roots.append(nid)
        return nid

    def export_groups(self) -> List[dict]:
        out = []
        for rid in self._roots:
            node = self._nodes[rid]
            header = node["row"]
            title = header[1] if len(header) > 1 else ""
            color = header[0] if len(header) > 0 else "white"
            rows = []
            for cid in node["children"]:
                rows.append({"columns": self._nodes[cid]["row"]})
            out.append({"title": title, "color": color, "header": header, "rows": rows})
        return out

class _CaptureFlatModel:
    def __init__(self):
        self.rows: List[list] = []

    def clear(self):
        self.rows.clear()

    def add(self, row: list, node: int | None = None):
        self.rows.append(list(row))
        return len(self.rows)

class CompareWebMixin:
    def _on_compare_web(self, _btn):
        if not _has_webkit:
            WarningDialog(_("WebKit2 GTK is not available on this system. Install webkit2gtk and try again."))
            return

        active = self.get_active('Person')
        if not active:
            WarningDialog(_("Select a person first."))
            return
        import tree
        if not (tree._fs_session and tree._fs_session.logged):
            WarningDialog(_("You must login first."))
            return

        gr = self.dbstate.db.get_person_from_handle(active)
        fsid = fs_utilities.get_fsftid(gr)
        if not fsid:
            WarningDialog(_("This Gramps person is not linked to FamilySearch yet. Use ‘Link person’."))
            return

        self._ensure_person_cached(fsid, with_relatives=True)

        try:
            data = self._build_compare_json(gr, fsid)
        except Exception as e:
            WarningDialog(_("Failed to prepare comparison data: {e}").format(e=str(e)))
            return
        
        # auto-tag on initial open (web)
        try:
            is_synced = fs_tags.compute_sync_from_payload(data)
            fs_tags.set_sync_status_for_person(self.dbstate.db, gr, is_synced=is_synced)
        except Exception:
            pass
            
        self._open_compare_webview(data, gr, fsid)

    def _build_compare_json(self, gr: Person, fsid: str) -> dict:
        fsP = gedcomx_v1.Person._index.get(fsid) or gedcomx_v1.Person()
        cap_overview = _CaptureTreeModel()
        try:
            fs_compare.compare_fs_to_gramps(fsP, gr, self.dbstate.db, model=cap_overview, dupdoc=True)
        except Exception:
            cap_overview.clear()

        cap_notes = _CaptureFlatModel()
        cap_sources = _CaptureFlatModel()
        try:
            self._fill_notes(cap_notes, gr, fsid)
        except Exception:
            cap_notes.clear()
        try:
            self._fill_sources(cap_sources, gr, fsid)
        except Exception:
            cap_sources.clear()

        disp_name = name_displayer.display(gr)
        gid = getattr(gr, "gramps_id", None) or ""
        person_block = {
            "name": disp_name,
            "gramps_id": gid,
            "fsid": fsid,
        }
        sr_meta = self._gather_sr_meta(fsid)

        return {
            "person": person_block,
            "overview": cap_overview.export_groups(),
            "notes": cap_notes.rows,
            "sources": cap_sources.rows,
            "sr_meta": sr_meta,
        }

    def _open_compare_webview(self, data: dict, gr: Person, fsid: str):
        url_pref = (self.CONFIG.get("preferences.fs_web_compare_url") or "").strip()

        win = Gtk.Window(title=_("FamilySearch Web Comparison"))
        win.set_transient_for(self.uistate.window)
        win.set_default_size(1200, 780)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, margin=6)
        btn_refresh = Gtk.Button(label=_("Refresh from FamilySearch"))
        btn_import = Gtk.Button(label=_("Import sources…"))
        btn_close = Gtk.Button(label=_("Close"))
        header.pack_start(btn_refresh, False, False, 0)
        header.pack_start(btn_import, False, False, 0)
        header.pack_end(btn_close, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        webview = WebKit2.WebView()
        scrolled.add(webview)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        vbox.pack_start(header, False, False, 0)
        vbox.pack_start(scrolled, True, True, 0)
        win.add(vbox)

        def _inject_payload():
            try:
                js = (
                    "try {"
                    "window.FS_COMPARE_DATA = " + json.dumps(data, ensure_ascii=False) + ";"
                    "window.dispatchEvent && window.dispatchEvent(new CustomEvent('fs-compare-data', {detail: window.FS_COMPARE_DATA}));"
                    "} catch (e) { console.error('inject failed', e); }"
                )
                webview.run_javascript(js, None, None, None)
            except Exception:
                pass

        def _load_fallback_html():
            html = self._default_compare_html()
            webview.load_html(html, "about:blank")

        def _on_load_changed(view, event):
            if event == WebKit2.LoadEvent.FINISHED:
                _inject_payload()

        webview.connect("load-changed", _on_load_changed)

        def do_refresh(_w):
            self._ensure_person_cached(fsid, with_relatives=True, force=True)
            new_data = self._build_compare_json(gr, fsid)
            data.clear(); data.update(new_data)
            # auto-tag on each refresh
            try:
                is_synced = fs_tags.compute_sync_from_payload(new_data)
                fs_tags.set_sync_status_for_person(self.dbstate.db, gr, is_synced=is_synced)
            except Exception:
                pass
            webview.reload() if url_pref else _inject_payload()

        def do_import(_w):
            self._import_sources_dialog(gr, fsid)

        btn_refresh.connect("clicked", do_refresh)
        btn_import.connect("clicked", do_import)
        btn_close.connect("clicked", lambda *_: win.destroy())

        loaded = False
        if url_pref:
            try:
                if url_pref.startswith(("http://", "https://", "file://")):
                    webview.load_uri(url_pref)
                    loaded = True
                else:
                    import os
                    if os.path.exists(url_pref):
                        uri = "file://" + os.path.abspath(url_pref)
                        webview.load_uri(uri)
                        loaded = True
            except Exception:
                loaded = False

        if not loaded:
            _load_fallback_html()

        win.show_all()

    def _default_compare_html(self) -> str:
        css = """
        body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, 'Noto Sans', Arial, sans-serif; margin: 0; background: #0b0f14; color: #e5eef5; }
        header { padding: 14px 18px; background: linear-gradient(90deg, #101826, #0b1220); border-bottom: 1px solid #1b2a3d; position: sticky; top: 0; z-index: 2;}
        .title { font-size: 16px; font-weight: 600; opacity: .95; }
        .muted { opacity: .7; font-size: 12px; margin-left: 10px; }
        .wrap { padding: 16px; }
        .tabs { display: flex; gap: 8px; margin-bottom: 12px; }
        .tab { padding: 8px 12px; border: 1px solid #1b2a3d; border-radius: 10px; cursor: pointer; background: #0e1623; }
        .tab.active { background: #132033; border-color: #27466f; }
        .panel { display: none; }
        .panel.active { display: block; }
        .group { margin-bottom: 14px; border: 1px solid #1b2a3d; border-radius: 12px; overflow: hidden; }
        .group .head { padding: 10px 12px; font-weight: 600; background: #0e1623; border-bottom: 1px solid #152235; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 8px 10px; border-bottom: 1px solid #122132; vertical-align: top; }
        th { text-align: left; font-size: 12px; letter-spacing: .02em; opacity: .8; }
        .row { background: #0b1019; }
        .chip { display:inline-block; padding: 2px 8px; border-radius: 999px; font-size: 12px; border: 1px solid #23405f; background: #0d1726; margin-right: 6px; }
        .colorbox { display:inline-block; width:10px; height:10px; border-radius:2px; margin-right: 6px; vertical-align: middle;}
        .c-green { background:#1bb570; } .c-yellow { background:#e7b93b; } .c-yellow3 { background:#db7d1f; }
        .c-orange { background:#e77a47; } .c-red { background:#d94b64; } .c-white { background:#d2dbe7; }
        code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; font-size: 12px; }
        a { color: #9ecbff; text-decoration: none }
        a:hover { text-decoration: underline }
        """
        js = """
        (function() {
          const S = {
            el: (sel, root=document) => root.querySelector(sel),
            els: (sel, root=document) => Array.from(root.querySelectorAll(sel)),
            esc: (s) => (s==null?'':String(s))
          };
          function colorClass(c) {
            if (!c) return 'c-white';
            c = String(c).toLowerCase();
            if (c.indexOf('green')>=0) return 'c-green';
            if (c.indexOf('yellow3')>=0) return 'c-yellow3';
            if (c.indexOf('yellow')>=0) return 'c-yellow';
            if (c.indexOf('orange')>=0) return 'c-orange';
            if (c.indexOf('red')>=0) return 'c-red';
            return 'c-white';
          }
          function h(tag, attrs={}, ...children){
            const el = document.createElement(tag);
            for (const [k,v] of Object.entries(attrs||{})) {
              if (k==='class') el.className = v;
              else if (k==='html') el.innerHTML = v;
              else el.setAttribute(k, v);
            }
            for (const ch of children){
              if (ch==null) continue;
              if (typeof ch==='string') el.appendChild(document.createTextNode(ch));
              else el.appendChild(ch);
            }
            return el;
          }
          function renderOverview(groups) {
            const root = h('div');
            (groups||[]).forEach(g=>{
              const box = h('div', {class:'group'});
              const head = h('div', {class:'head'},
                h('span', {class:'colorbox '+colorClass(g.color)}),
                S.esc(g.title||'')
              );
              box.appendChild(head);
              const tbl = h('table');
              const thead = h('thead', {}, h('tr', {},
                h('th', {}, 'Property'),
                h('th', {}, 'Date (Gramps)'),
                h('th', {}, 'Value (Gramps)'),
                h('th', {}, 'Date (FS)'),
                h('th', {}, 'Value (FS)'),
              ));
              tbl.appendChild(thead);
              const tb = h('tbody');
              (g.rows||[]).forEach(r=>{
                const c = r.columns || [];
                const tr = h('tr', {class:'row'});
                tr.appendChild(h('td', {}, c[1] ?? ''));
                tr.appendChild(h('td', {}, c[2] ?? ''));
                tr.appendChild(h('td', {}, c[3] ?? ''));
                tr.appendChild(h('td', {}, c[4] ?? ''));
                tr.appendChild(h('td', {}, c[5] ?? ''));
                tb.appendChild(tr);
              });
              tbl.appendChild(tb);
              box.appendChild(tbl);
              root.appendChild(box);
            });
            return root;
          }
          function renderNotes(rows) {
            const tbl = h('table');
            tbl.appendChild(h('thead',{}, h('tr',{},
              h('th',{},''), h('th',{},'Scope'), h('th',{},'Title'),
              h('th',{},'Gramps Value'), h('th',{},'FS Title'), h('th',{},'FS Value')
            )));
            const tb = h('tbody');
            (rows||[]).forEach(r=>{
              const tr = h('tr', {class:'row'});
              tr.appendChild(h('td',{}, h('span', {class:'colorbox '+colorClass(r[0])})));
              tr.appendChild(h('td',{}, r[1] ?? ''));
              tr.appendChild(h('td',{}, r[2] ?? ''));
              tr.appendChild(h('td',{}, r[3] ?? ''));
              tr.appendChild(h('td',{}, r[4] ?? ''));
              tr.appendChild(h('td',{}, r[5] ?? ''));
              tb.appendChild(tr);
            });
            tbl.appendChild(tb);
            return tbl;
          }
          function renderSources(rows) {
            const tbl = h('table');
            tbl.appendChild(h('thead',{}, h('tr',{},
              h('th',{},''), h('th',{},'Kind'), h('th',{},'Date'),
              h('th',{},'Title'), h('th',{},'Gramps URL'),
              h('th',{},'FS Date'), h('th',{},'FS Title'),
              h('th',{},'FS URL'), h('th',{},'Tags'),
              h('th',{},'Contributor'), h('th',{},'Modified')
            )));
            const tb = h('tbody');
            (rows||[]).forEach(r=>{
              const tr = h('tr', {class:'row'});
              tr.appendChild(h('td',{}, h('span', {class:'colorbox '+colorClass(r[0])})));
              tr.appendChild(h('td',{}, r[1] ?? ''));
              tr.appendChild(h('td',{}, r[2] ?? ''));
              tr.appendChild(h('td',{}, r[3] ?? ''));
              tr.appendChild(h('td',{}, r[4] ?? ''));
              tr.appendChild(h('td',{}, r[5] ?? ''));
              tr.appendChild(h('td',{}, r[6] ?? ''));
              const fsurl = r[7] ?? '';
              if (fsurl && /^https?:\\/\\//.test(fsurl)) {
                tr.appendChild(h('td',{}, h('a', {href:fsurl}, fsurl)));
              } else {
                tr.appendChild(h('td',{}, fsurl));
              }
              tr.appendChild(h('td',{}, r[8] ?? ''));
              tr.appendChild(h('td',{}, r[9] ?? ''));
              tr.appendChild(h('td',{}, r[10] ?? ''));
              tb.appendChild(tr);
            });
            tbl.appendChild(tb);
            return tbl;
          }
          function switchTab(id) {
            document.querySelectorAll('.tab').forEach(b => b.classList.toggle('active', b.dataset.id===id));
            document.querySelectorAll('.panel').forEach(p => p.classList.toggle('active', p.id===id));
          }
          function renderAll(data) {
            const person = data.person || {};
            document.getElementById('title-name').textContent = person.name || '(Unnamed)';
            document.getElementById('title-meta').textContent = [
              person.gramps_id ? ('Gramps: '+person.gramps_id) : '',
              person.fsid ? ('FSID: '+person.fsid) : '',
            ].filter(Boolean).join(' • ');

            const ov = document.querySelector('#panel-overview .content'); ov.innerHTML='';
            ov.appendChild(renderOverview(data.overview||[]));

            const nt = document.querySelector('#panel-notes .content'); nt.innerHTML='';
            nt.appendChild(renderNotes(data.notes||[]));

            const sr = document.querySelector('#panel-sources .content'); sr.innerHTML='';
            sr.appendChild(renderSources(data.sources||[]));

            switchTab('panel-overview');
          }
          window.addEventListener('DOMContentLoaded', ()=>{
            document.querySelectorAll('.tab').forEach(b=>{
              b.addEventListener('click', ()=>switchTab(b.dataset.id));
            });
            if (window.FS_COMPARE_DATA) {
              renderAll(window.FS_COMPARE_DATA);
            }
          });
          window.addEventListener('fs-compare-data', (ev)=>{
            const data = ev.detail || window.FS_COMPARE_DATA || {};
            renderAll(data);
          });
        })();
        """
        html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>FamilySearch Web Comparison</title>
  <style>{css}</style>
</head>
<body>
  <header>
    <span class="title" id="title-name">Loading…</span>
    <span class="muted" id="title-meta"></span>
  </header>
  <div class="wrap">
    <div class="tabs">
      <div class="tab active" data-id="panel-overview">Overview</div>
      <div class="tab" data-id="panel-notes">Notes</div>
      <div class="tab" data-id="panel-sources">Sources</div>
    </div>

    <div class="panel active" id="panel-overview">
      <div class="content"></div>
    </div>
    <div class="panel" id="panel-notes">
      <div class="content"></div>
    </div>
    <div class="panel" id="panel-sources">
      <div class="content"></div>
    </div>
  </div>
  <script>{js}</script>
</body>
</html>"""
        return html
