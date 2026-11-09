# CLAUDE.md – Spirit Island Offline-Kopie

Übergabe-Notizen für die nächste Claude-Instanz. Antworten auf Deutsch, Commit-Messages auf Deutsch.
Nie ungefragt committen.

## Worum es geht

Statische Offline-Kopie der 37 Spirit-Seiten des Spirit Island Wiki (Stand April 2025, aus dem Internet Archive).
Repo `mawille/spirit-island`, live über GitHub Pages: https://mawille.github.io/spirit-island/

- Branch `gh-pages` = **live**. Jeder Push dorthin wird nach ca. 4 Minuten veröffentlicht (Workflow „pages build and deployment“).
- Branch `feature/mobile-ansicht` = laufende Arbeit an der Handy-Ansicht (siehe unten), noch nicht live.

## Aufbau

- `index.html` – Spirit-Liste (List of Spirits), `<Spirit_Name>.html` – je Spirit eine Seite
- `images/` – alle Bilder lokal (Wiki-Pfadstruktur `images/<h>/<hh>/Datei`)
- `css/wiki*.css` – Original-Stylesheets des Wikis; `css/offline.css` + `js/offline.js` – eigene Ergänzungen
  (Reiter/HeaderTabs ohne OOUI-JS, sortierbare Tabelle, Hinweisbanner, Mobile-Ansicht, Menü-Button)
- `tools/build.py` – erzeugt alles aus dem Internet Archive; `tools/offline.css|js` sind die Quellen,
  `build.py` kopiert sie nach `css/` bzw. `js/`
- Oben auf jeder Seite steht ein Hinweisbanner (inoffizielle, nicht-kommerzielle Kopie, CC BY-NC-SA,
  © Greater Than Games). Der Nutzer hat ihn ausdrücklich gewollt, nicht entfernen.
- Menüs (Seitenleiste, Logo) zeigen nur auf selbst gehostete Seiten. Links im Fließtext auf nicht gespiegelte
  Wiki-Seiten (Power Cards, Adversaries …) gehen bewusst weiter ins Internet Archive.

## Bauen

```bash
python -I tools/build.py <cache-ordner> .
```

- Der Download-Cache lag auf dem alten PC im Temp-Ordner und ist **nicht im Repo**. Ein voller Neubau lädt
  ca. 1150 Dateien neu aus archive.org (nur 1 Thread + 1 s Pause, ca. 25 Minuten). Parallel drosselt archive.org
  mit „Verbindung verweigert“ (WinError 10061) – das ist keine Firewall.
- **Reine CSS/JS-Änderungen brauchen keinen Neubau:** `tools/offline.css` bzw. `tools/offline.js` ändern und
  nach `css/offline.css` bzw. `js/offline.js` kopieren (beide Stellen synchron halten).
- HTML-Änderungen (Viewport-Tag, Menü-Button, Menü-Umbau, Banner) passieren in `build()` in `tools/build.py`
  und brauchen einen Neubau, also den Cache.

## Prüfen

- Die Chrome-Extension darf keine `file://`-Seiten öffnen. Lokal einen Server starten:
  `python -I -m http.server 8765 --bind 127.0.0.1 --directory .` und `http://127.0.0.1:8765/` öffnen.
- Handy-Ansicht: im eingebauten Browser `resize_window` mit Preset `mobile` (375×812), danach wieder `desktop`.
- Die GitHub-API ohne Login hat nur 60 Anfragen/Stunde – Pages-Status lieber im Actions-Tab im Browser ansehen
  oder die Live-Seite direkt abfragen.

## Aktueller Stand: Handy-Ansicht, Variante 1 (Branch `feature/mobile-ansicht`)

Vereinbart war „Variante 1 – grundtauglich“: Seite auf dem Handy lesbar, breite Blöcke (Growth, Presence,
Innate Powers) dürfen seitlich wischbar bleiben. Alles in `@media (max-width: 800px)` in `offline.css`,
der Desktop bleibt unverändert.

Erledigt und in 375 px geprüft (an Thunderspeaker):
- `<meta name="viewport">` in allen Seiten, Wiki-Kopfleiste ausgeblendet, Inhalt volle Breite
- Button „☰ Spirits“ (sticky) öffnet die Seitenleiste als Overlay; Klick daneben, auf einen Link oder Esc schließt
- Inline-Symbole (Presence, Dahan …) bleiben klein: `height: auto` nur für `a.image img`
- `fieldset` der Reiter hatte `min-width: min-content` und hat die Seite verbreitert → `min-width: 0`
- Reiterleiste ist eine wischbare Zeile

Zuletzt geändert, **noch nicht geprüft**:
- Die Wiki-Regeln heißen `#spirit .growthblock`, `#spirit .topblock`, `#spirit .rightblock`,
  `#spirit .rightblock .innate`, `#spirit .powerblock` und schlugen per ID-Spezifität die Mobile-Regeln
  (Growth-Block blieb 700 px breit). Die Mobile-Regeln haben jetzt das `#spirit`-Präfix.

Nächste Schritte:
1. In 375 px prüfen: Growth-Block muss in sich seitlich scrollen statt die Seite zu verbreitern
   (`document.documentElement.scrollWidth === clientWidth`). Mehrere Spirits ansehen, die sich im Aufbau
   unterscheiden: Thunderspeaker, Lightning's Swift Strike, Fractured Days Split the Sky, Many Minds Move as One,
   Finder of Paths Unseen; außerdem `index.html` (Tabelle) und das Menü auf- und zuklappen.
2. Desktop-Ansicht gegenprüfen (darf sich nicht verändert haben).
3. Nach Freigabe durch den Nutzer `feature/mobile-ansicht` in `gh-pages` mergen und pushen → geht live.

Optional später („Variante 2“, 2–3 Stunden): Growth-Optionen und Presence-Leisten umbrechen statt wischen,
Karten zu zweit nebeneinander, schmale Innate-Tabellen.
