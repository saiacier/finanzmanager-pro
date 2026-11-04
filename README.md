# FinanzManager Pro für macOS und Windows
Freie Software unter der GNU General Public License v3.0 oder später (siehe LICENSE). Namen und Logos sind ausgenommen (siehe [Namen und Logos](#namen-und-logos)).

Lokale Haushalts- und Budgetsoftware: Buchungen, CSV-Import, Budgets, Sparziele und Dashboards. Kostenlos, ohne Konto, ohne Cloud und ohne Internetverbindung.

## Aufbau

| Ordner | Inhalt |
|---|---|
| `apps/FinanzManager/Web` | Oberfläche: HTML-Vorlage, CSS, JavaScript. Die einzige Oberfläche, für alle Systeme gleich. |
| `apps/FinanzManager/desktop` | Programmfenster (`finanzmanager_desktop.py`) |
| `apps/FinanzManager/Resources` | App-Symbol |
| `platform/python/financecore` | Programmkern in Python: Datenbank (`store.py`), Datenordner und Zustimmung (`platform.py`), Rechtstexte (`documents.py`), Fenster und Dialoge (`host.py`, `desktop.py`), lokaler Seitenserver (`pageserver.py`) |
| `platform/terms` | Nutzungsbedingungen, Datenschutz, Impressum, Lizenz- und Sicherheitshinweise. Werden beim Bau eingebettet. |
| `platform/compliance` | Freigabeliste der Python-Komponenten und zusätzliche Lizenztexte |
| `scripts` | Bauen (`build.py`), Downloadpaket (`prepare_download.py`), Prüfung (`audit_download.py`) |
| `tests` | Datenbankprüfungen (`test_store.py`) und Oberflächentests (`*.cjs`, benötigen Node.js) |

Das Programmfenster nutzt pywebview mit dem Browser-Baustein des Systems: WebKit unter macOS, WebView2 unter Windows. Die Oberfläche kommt von einem lokalen Seitenserver nur auf 127.0.0.1 mit Zufallsschlüssel; ihre Aufrufe erreichen den Programmkern über `/api/host/<funktion>`.

## Daten

| System | Datenordner |
|---|---|
| macOS | `~/Library/Application Support/IT-Smarthome/FinanzManager` |
| Windows | `%LOCALAPPDATA%\IT-Smarthome\FinanzManager` |

Darin liegen `finanzmanager.sqlite3` (Schema 1, Speicherprotokoll 1), `programm.json` (Zustimmung zu den Nutzungsbedingungen mit Version und Prüfsumme), `Sicherungen/` und `webview/`. Datenbanken der Versionen 1.2.x werden unverändert weiterverwendet. Vor jedem Versionswechsel ein vollständiges Backup exportieren.

## Bauen

PyInstaller baut nur für das System, auf dem es läuft. Die Mac-Version wird auf einem Mac gebaut, die Windows-Version auf Windows.

macOS (Python 3.12 oder neuer):

```bash
python3 -m venv work/build-env
work/build-env/bin/python -m pip install -r scripts/requirements-macos.txt
work/build-env/bin/python -m unittest discover -s tests
work/build-env/bin/python scripts/build.py
work/build-env/bin/python scripts/prepare_download.py
work/build-env/bin/python scripts/audit_download.py
```

Windows (Python 3.12 oder neuer von python.org, PowerShell):

```powershell
py -3 -m venv work\build-env
work\build-env\Scripts\python -m pip install -r scripts\requirements-windows.txt
work\build-env\Scripts\python -m unittest discover -s tests
work\build-env\Scripts\python scripts\build.py
```

`build.py` prüft jede mitgelieferte Python-Komponente gegen `platform/compliance/python-policy.json`, legt die Lizenztexte unter `Legal/PythonProgram` ab, sucht nach verbotenen Dateien, signiert (macOS ad hoc oder mit `FINANCE_CODESIGN_IDENTITY`, Windows mit `FINANCE_SIGNTOOL_CERT`), startet das fertige Programm einmal isoliert mit einem temporären Datenordner und schreibt das ZIP nach `releases/`. Zwischendateien und das fertige Programm liegen außerhalb synchronisierter Ordner: macOS `~/Library/Caches/FinanzManager-build`, Windows `%LOCALAPPDATA%\FinanzManager-build` (änderbar mit `FINANCE_BUILD_DIR`). Danach auf einem Rechner `prepare_download.py` und `audit_download.py` ausführen, nachdem beide ZIPs in `releases/` liegen.

## Entwicklung mit KI-Unterstützung

Dieses Programm wurde mit Unterstützung von KI-Werkzeugen entwickelt und vom Anbieter geprüft und zusammengestellt. Das Programm selbst enthält keine KI-Funktion und überträgt keine Daten an KI-Dienste.

Interne Herkunftsunterlagen (nur im Projektarchiv, nicht Teil des Quellcode-Downloads): docs/HERKUNFT-UND-RECHTE.md, docs/HERKUNFT-UND-RECHTE.json und docs/BEITRAGSREGISTER.md.

## Namen und Logos

Der Quellcode des FinanzManagers steht unter der GNU General Public License v3.0 oder später (siehe LICENSE).

Nach Abschnitt 7 Buchstabe c und e der GPL-3.0 sind folgende Kennzeichen von der Lizenz ausgenommen: die Namen „FinanzManager Pro“ und „IT-Smarthome“, das IT-Smarthome-Logo (apps/FinanzManager/Web/assets/developer-logo*.png) und das FinanzManager-App-Symbol (apps/FinanzManager/Web/assets/app-icon.png, apps/FinanzManager/Resources/AppIcon.icns). Sie liegen nur bei, damit die offizielle Ausgabe gebaut werden kann.

Veränderte Fassungen müssen als verändert gekennzeichnet und unter einem anderen Namen und ohne diese Logos und Symbole weitergegeben werden.
