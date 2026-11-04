# Komponenten und Lizenzhinweise
Geprüfter Umfang: FinanzManager 1.3.0, Projektstand 03.11.2026, Ausgaben für macOS und Windows.

Lizenz des FinanzManagers
FinanzManager Pro – Copyright (C) 2026 Samuele Timoteo Iacierno.
Dieses Programm ist freie Software: Du kannst es unter den Bedingungen der GNU General Public License, wie von der Free Software Foundation veröffentlicht, weitergeben und/oder verändern, entweder gemäß Version 3 der Lizenz oder (nach deiner Wahl) jeder späteren Version. Das Programm wird OHNE JEDE GEWÄHRLEISTUNG bereitgestellt, soweit gesetzlich zulässig; für Nutzer in Deutschland gilt die Haftungsregel in Abschnitt 7 der Nutzungsbedingungen. Den Lizenztext enthält GPL-3.0.txt (Original in englischer Sprache, maßgeblich), siehe auch https://www.gnu.org/licenses/gpl-3.0.html . Quellcode: https://it-smarthome.net/downloads
Ausgenommen von der Lizenz sind Namen und Logos (siehe Abschnitt 2 der Nutzungsbedingungen).

Anwendung und Produktgrafiken
Die eigene FinanzManager-Oberfläche (HTML/CSS/JavaScript) und der Programmkern FinanceCore (Python) stammen aus diesem Projekt. Das App-Icon wurde am 02.11.2026 in derselben geometrischen Form in der FinanzManager-Farbe Violett neu gezeichnet; der Seitenkopf verwendet dieselben PNG-Bilddaten wie der große ICNS-Eintrag. Das IT-Smarthome-Lieferantenlogo wurde vom Anbieter bereitgestellt. Die Berechtigung zur Nutzung dieser Marke wird nicht an App-Nutzer übertragen; Logo und App-Symbol stehen nicht unter der GPL. Der Anbieter hat am 30.10.2026 im Projektchat die zur Weitergabe erforderlichen Rechte an der ursprünglich bereitgestellten HTML-App und den Firmenlogos bestätigt. Das FinanzManager-Icon besteht aus einfachen geometrischen Formen (abgerundetes Quadrat und vier Balken). Diese Dokumentation ersetzt keine unabhängige Marken- oder Rechteprüfung.

Entwicklung
FinanzManager Pro wurde mit Unterstützung von KI-Werkzeugen entwickelt und vom Anbieter geprüft und zusammengestellt. Die App selbst enthält keine KI-Funktion; Auswertungen und Kategorisierung arbeiten mit festen Regeln auf deinem Gerät, und es werden keine Daten an KI-Dienste übertragen.

Gemeinsame Gestaltung
Ein kleiner Stylesheet-Baustein steht unter der mit der GPL vereinbaren MIT-Lizenz; der zugehörige Lizenztext liegt als MIT-Gestaltung.txt bei. Der FinanzManager ist technisch eigenständig und enthält keine Bestandteile anderer Programme des Anbieters. Für andere Programme aus dem Downloadbereich ergeben sich aus dieser App keine Rechte oder Pflichten.

Programmkern und Fenster
Der Programmkern ist in Python geschrieben und wird mit PyInstaller zu einem eigenständigen Programm zusammengestellt; ein separat installiertes Python ist nicht nötig. Das Programmfenster nutzt pywebview (BSD-3-Clause) und darüber den Browser-Baustein des Betriebssystems: WebKit unter macOS, Microsoft Edge WebView2 unter Windows. Diese Systembausteine werden nicht als eigene Kopie mitgeliefert. Unter macOS verbindet PyObjC (MIT) Python mit den Systembibliotheken, unter Windows pythonnet (MIT). Die Oberfläche wird über einen lokalen Seitenserver ausschließlich auf 127.0.0.1 mit Zufallsschlüssel an das eigene Programmfenster geliefert; Finanzdaten werden nicht über diesen Server, sondern nur innerhalb des Programms übergeben. Es gibt keine Verbindung ins Internet.

Mitgelieferte Komponenten
Alle mitgelieferten Python-Komponenten werden beim Paketbau gegen eine Freigabeliste geprüft; unbekannte Komponenten stoppen den Paketbau. Ihre Lizenztexte und eine Komponentenliste (components.json) liegen im Programmpaket unter Legal/PythonProgram, ebenso die Lizenz der Python-Laufzeit (CPython-LICENSE.txt) und Hinweise zu deren Laufzeitbibliotheken (u. a. SQLite, gemeinfrei; OpenSSL, Apache-2.0; zlib, libffi, expat). Das Startprogramm stammt von PyInstaller (GPL-2.0-or-later mit Bootloader-Ausnahme, die die Weitergabe unabhängig von der Programmlizenz erlaubt). Alle Lizenzen sind mit der GPL-3.0 vereinbar.

Systemplattformen
macOS-Systemkomponenten (AppKit, Foundation, WebKit) und Windows-Systemkomponenten (WebView2-Laufzeit, .NET) werden aus dem Betriebssystem verwendet. Sie sind nicht pauschal Open Source oder frei weiterlizenzierbar; maßgeblich sind die Bedingungen des jeweiligen Betriebssystems. Code-Signatur, Notarisierung oder andere Vertriebswege können Kosten verursachen.

Browserfunktionen
CSV-Parser, Diagramme, Kategorisierung und Dashboard-Verwaltung sind lokaler Anwendungscode. Intl, DOM, TextEncoder/TextDecoder, Blob und die Web-Crypto-APIs stellt der Browser-Baustein des Systems bereit. AES-GCM/PBKDF2 verwenden Web Crypto; keine nachgeladene Kryptobibliothek. Keine kostenpflichtigen Charting- oder CSV-Bibliotheken und keine Lizenzgebühr pro Start oder Datensatz.

Freiwillige Unterstützung
PayPal ist ein externer Dienst mit eigenen Bedingungen und möglichen Gebühren. Ein kostenlos nutzbarer Button macht die Zahlungsabwicklung nicht gebührenfrei. Keine Zahlungsdaten werden von der FinanzManager-App selbst verarbeitet.

Prüfgrenze
Dies ist eine dokumentierte Komponentenprüfung, keine pauschale Freigabe aller denkbaren Urheber-, Marken-, Patent- oder Vertragsrechte. Kostenlose Nutzung der App bedeutet nicht uneingeschränkte Freiheit aller Systemkomponenten. Der tatsächliche Paketinhalt und die beigefügten Originaltexte sind vor jeder neuen Veröffentlichung zu prüfen.


Speicherung
Die Daten liegen in einer lokalen SQLite-Datenbank (Schema 1). Datenbanken der Versionen 1.2.x werden unverändert weiterverwendet. SQLite ist Teil der mitgelieferten Python-Laufzeit; das SQLite-Projekt stellt den Code nach eigener Erklärung gemeinfrei bereit: https://www.sqlite.org/copyright.html
