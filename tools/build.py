"""Baut eine Offline-Kopie der Spirit-Island-Wiki-Spiritseiten aus dem Internet Archive."""
import hashlib
import html
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

TS = "20250427153313"
SITE = "https://spiritislandwiki.com"
ARCHIVE_RAW = f"https://web.archive.org/web/{TS}id_/{SITE}"
ARCHIVE_VIEW = f"https://web.archive.org/web/{TS}/{SITE}"

CACHE = sys.argv[1]
OUT = sys.argv[2]
ASSETS = os.path.dirname(os.path.abspath(__file__))
os.makedirs(CACHE, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

lock = threading.Lock()
failed = []


def log(msg):
    with lock:
        print(msg, flush=True)


def fetch(path):
    """Lädt SITE+path aus dem Archiv (mit Cache). Liefert bytes oder None."""
    key = hashlib.sha1(path.encode()).hexdigest()
    cp = os.path.join(CACHE, key)
    if os.path.exists(cp):
        with open(cp, "rb") as f:
            return f.read()
    if os.path.exists(cp + ".missing"):
        return None
    url = ARCHIVE_RAW + path
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (offline-copy script)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            with open(cp, "wb") as f:
                f.write(data)
            time.sleep(1.0)  # archive.org drosselt sonst
            return data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                open(cp + ".missing", "w").close()
                log(f"  404 {path}")
                return None
            wait = 60 if e.code == 429 else 10 * (attempt + 1)
            log(f"  HTTP {e.code} {path} -> warte {wait}s")
            time.sleep(wait)
        except Exception as e:  # Netzwerkfehler
            log(f"  Fehler {e} {path}")
            time.sleep(20 * (attempt + 1))
    failed.append(path)
    return None


# ---------- Seiten ----------
def title_of(href):
    """'/index.php?title=Foo%27s&x=1#a' -> ('Foo's', '#a') oder None."""
    m = re.match(r"^(?:https?://spiritislandwiki\.com)?/index\.php\?title=([^&#?]+)[^#]*(#.*)?$", href)
    if not m:
        return None
    return urllib.parse.unquote(m.group(1)).replace(" ", "_"), (m.group(2) or "")


def safe_name(s):
    return re.sub(r'[<>:"/\\|?*]', "_", s)


def page_file(title):
    return "index.html" if title == "List_of_Spirits" else safe_name(title) + ".html"


list_html = fetch("/index.php?title=List_of_Spirits").decode("utf-8")
table = list_html[list_html.find("wikitable sortable"):]
table = table[:table.find("</table></center>") if "</table></center>" in table else len(table)]
spirits = []
for href, _t in re.findall(r'<td><a href="(/index\.php\?title=[^"]+)" title="([^"]+)">', table):
    t = title_of(href)[0]
    if t not in spirits:
        spirits.append(t)
log(f"{len(spirits)} Spirits gefunden")
LOCAL_PAGES = set(spirits) | {"List_of_Spirits"}

pages = {"List_of_Spirits": list_html}
with ThreadPoolExecutor(1) as ex:
    for t, data in zip(spirits, ex.map(lambda t: fetch("/index.php?title=" + urllib.parse.quote(t, safe="_-()")), spirits)):
        if data is None:
            log(f"!! Seite fehlt: {t}")
            continue
        pages[t] = data.decode("utf-8")
log(f"{len(pages)} Seiten geladen")


# ---------- Bilder ----------
def original_path(filename):
    """MediaWiki-Hashpfad des Originals zu 'File:Name.png'."""
    name = filename.replace(" ", "_")
    h = hashlib.md5(name.encode("utf-8")).hexdigest()
    return f"/images/{h[0]}/{h[:2]}/" + urllib.parse.quote(name, safe="_-().,'!")


def local_asset(path):
    """Wiki-Pfad '/images/a/ab/X.png' -> relativer lokaler Pfad 'images/a/ab/X.png'."""
    p = urllib.parse.unquote(path.split("?")[0]).lstrip("/")
    return "/".join(safe_name(seg) for seg in p.split("/"))


def norm(path):
    """Einheitliche URL-Kodierung für Downloads."""
    return urllib.parse.quote(urllib.parse.unquote(path), safe="/_-().,'!?=&%")


need = set()  # Wiki-Pfade, die heruntergeladen werden müssen


def store(path):
    data = fetch(norm(path))
    if data is None:
        return False
    lp = os.path.join(OUT, *local_asset(path).split("/"))
    os.makedirs(os.path.dirname(lp), exist_ok=True)
    if not os.path.exists(lp):
        with open(lp, "wb") as f:
            f.write(data)
    return True


# 1. Durchlauf: benötigte Bilder sammeln
for t, h in pages.items():
    for src in re.findall(r'<img [^>]*src="(/[^"]+)"', h):
        need.add(html.unescape(src))
    for fn in re.findall(r'href="/index\.php\?title=File:([^"&#]+)"', h):
        need.add(original_path(urllib.parse.unquote(html.unescape(fn))))
    for u in re.findall(r"url\(['\"]?(/[^'\")]+)['\"]?\)", h):
        need.add(html.unescape(u))

# CSS
css_files = {}
for t, h in pages.items():
    for href in re.findall(r'<link rel="stylesheet" href="(/load\.php[^"]+)"', h):
        href = html.unescape(href)
        if href not in css_files:
            css_files[href] = None
for i, href in enumerate(css_files):
    data = fetch(href)
    css = data.decode("utf-8") if data else ""
    for u in re.findall(r"url\(['\"]?(/[^'\")]+)['\"]?\)", css):
        need.add(u)
    css_files[href] = (f"css/wiki{i}.css", css)

log(f"{len(need)} Bilder/Dateien zu laden")
ok = {}
done = [0]


def job(p):
    r = store(p)
    with lock:
        ok[p] = r
        done[0] += 1
        if done[0] % 50 == 0:
            print(f"  {done[0]}/{len(need)}", flush=True)


with ThreadPoolExecutor(1) as ex:
    list(ex.map(job, sorted(need)))
log(f"Bilder fertig: {sum(ok.values())} ok, {len(need) - sum(ok.values())} fehlen")


# ---------- Umschreiben ----------
def rel(target, depth=0):
    return urllib.parse.quote(target, safe="/._-()',!")


def rewrite_url(u):
    u = html.unescape(u)
    if u.startswith("#") or u.startswith("data:") or u.startswith("mailto:"):
        return u
    if u.startswith("//"):
        return "https:" + u
    t = title_of(u)
    if t:
        title, frag = t
        if title in LOCAL_PAGES:
            return rel(page_file(title)) + frag
        if title.startswith("File:"):
            op = original_path(title[5:])
            if ok.get(op):
                return rel(local_asset(op))
        return ARCHIVE_VIEW + u if u.startswith("/") else ARCHIVE_VIEW + u[len(SITE):]
    if u.startswith(SITE):
        u = u[len(SITE):] or "/"
    if u.startswith("/"):
        if ok.get(u) or ok.get(html.unescape(u)):
            return rel(local_asset(u))
        return ARCHIVE_VIEW + u
    return u


def attr_sub(m):
    name, q, val = m.group(1), m.group(2), m.group(3)
    return f'{name}={q}{html.escape(rewrite_url(val), quote=True)}{q}'


def fix_img(m):
    tag = m.group(0)
    tag = re.sub(r'\s(srcset|loading|decoding)="[^"]*"', "", tag)
    return tag


def fix_file_links(h):
    """Große Bilder direkt in Originalauflösung anzeigen (schärfer)."""
    def sub(m):
        fn, attrs, img = m.group(1), m.group(2), m.group(3)
        op = original_path(urllib.parse.unquote(html.unescape(fn)))
        w = re.search(r'width="(\d+)"', img)
        if ok.get(op) and w and int(w.group(1)) >= 150:
            img = re.sub(r'src="[^"]+"', f'src="{op}"', img, count=1)
        return f'<a href="/index.php?title=File:{fn}"{attrs}>{img}</a>'
    return re.sub(r'<a href="/index\.php\?title=File:([^"]+)"([^>]*)>(<img [^>]*>)</a>', sub, h)


nav_items = "".join(
    f'<li><a href="{rel(page_file(t))}">{html.escape(t.replace("_", " "))}</a></li>' for t in spirits)


BANNER = (
    '<div id="offline-hinweis">Inoffizielle, nicht-kommerzielle Kopie des '
    '<a href="https://spiritislandwiki.com/">Spirit Island Wiki</a> (Stand April 2025, gesichert über das '
    '<a href="https://web.archive.org/web/20250427153313/https://spiritislandwiki.com/index.php?title=List_of_Spirits">Internet Archive</a>). '
    'Wiki-Texte unter <a href="https://creativecommons.org/licenses/by-nc-sa/3.0/">CC BY-NC-SA</a>; '
    'Spirit Island, Karten und Artwork © Greater Than Games, LLC. Kein offizielles Angebot.</div>')


def build(title, h):
    h = re.sub(r"<script\b.*?</script>", "", h, flags=re.S)
    h = re.sub(r'<link rel="stylesheet" href="([^"]+)"\s*/?>',
               lambda m: f'<link rel="stylesheet" href="{css_files[html.unescape(m.group(1))][0]}"/>', h)
    h = re.sub(r"<link [^>]*rel=\"(?:alternate|EditURI|search|license|canonical|edit|shortcut icon|apple-touch-icon)\"[^>]*>", "", h)
    h = h.replace("</head>", '<link rel="stylesheet" href="css/offline.css"/>\n</head>', 1)
    h = h.replace("</body>", '<script src="js/offline.js"></script>\n</body>', 1)
    h = re.sub(r'<span class="ht-editsection"[^>]*>.*?</span>', "", h, flags=re.S)
    h = re.sub(r'<span class="mw-editsection">.*?</span></span>', "", h, flags=re.S)
    h = re.sub(r'<div id="p-search".*?</form>\s*</div>\s*</div>', "", h, flags=re.S)
    h = fix_file_links(h)
    h = re.sub(r"<img [^>]*>", fix_img, h)
    h = re.sub(r'\b(href|src)=(["\'])(.*?)\2', attr_sub, h)
    h = re.sub(r"url\(['\"]?(/[^'\")]+)['\"]?\)",
               lambda m: f"url('{rewrite_url(m.group(1))}')", h)
    # Sidebar: Liste aller Spirits ergänzen
    h = h.replace('<nav id="p-navigation"',
                  '<nav id="p-offline-spirits" class="mw-portlet vector-menu vector-menu-portal portal">'
                  '<h3 class="vector-menu-heading"><span>Spirits (offline)</span></h3>'
                  '<div class="vector-menu-content"><ul class="vector-menu-content-list">'
                  f'<li><a href="index.html"><b>List of Spirits</b></a></li>{nav_items}</ul></div></nav>'
                  '<nav id="p-navigation"', 1)
    h = h.replace('<a id="top"></a>', '<a id="top"></a>' + BANNER, 1)
    return h


os.makedirs(os.path.join(OUT, "css"), exist_ok=True)
os.makedirs(os.path.join(OUT, "js"), exist_ok=True)
for href, (fn, css) in css_files.items():
    css = re.sub(r"url\(['\"]?(/[^'\")]+)['\"]?\)",
                 lambda m: f"url('../{rewrite_url(m.group(1))}')" if not rewrite_url(m.group(1)).startswith("http")
                 else f"url('{rewrite_url(m.group(1))}')", css)
    with open(os.path.join(OUT, fn), "w", encoding="utf-8") as f:
        f.write(css)
for name, sub in (("offline.css", "css"), ("offline.js", "js")):
    with open(os.path.join(ASSETS, name), encoding="utf-8") as src, \
            open(os.path.join(OUT, sub, name), "w", encoding="utf-8") as dst:
        dst.write(src.read())

for t, h in pages.items():
    with open(os.path.join(OUT, page_file(t)), "w", encoding="utf-8") as f:
        f.write(build(t, h))
log(f"{len(pages)} HTML-Seiten geschrieben nach {OUT}")
if failed:
    log("Endgültig fehlgeschlagen:\n  " + "\n  ".join(failed))
