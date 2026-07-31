# Recovery Radar Pilot 2.0

Kostenloser Testbetrieb mit GitHub Actions, EODHD Free API und Netlify.

## Funktionsweise

- 100 vordefinierte Aktien aus Deutschland, Europa und den USA
- täglich rotierende Aktualisierung von standardmäßig 15 Aktien
- Kursbasierter Recovery Score aus 1M-, 3M-, 6M- und 12M-Performance, Abstand zum Jahrestief/-hoch, Volatilität und Erholungsdynamik
- Ergebnisse werden in `data/results.json` gespeichert
- statische Netlify-Seite liest ausschließlich die vorberechneten Daten
- Watchlist wird lokal im Browser gespeichert

## Einrichtung

1. Neues GitHub-Repository erstellen.
2. Den gesamten Inhalt dieses Ordners in das Repository hochladen.
3. Unter **Settings → Secrets and variables → Actions** ein Repository Secret anlegen:
   - Name: `EODHD_API_KEY`
   - Wert: dein EODHD API-Schlüssel
4. Unter **Actions** den Workflow `Recovery Radar Daily Screening` einmal manuell starten.
5. In Netlify **Add new project → Import an existing project** wählen und das GitHub-Repository verbinden.
6. Build command leer lassen, Publish directory: `.`

## Zeitplan

Der Workflow läuft täglich um 04:17 UTC. Der Zeitpunkt ist bewusst nicht zur vollen Stunde gewählt, da geplante GitHub-Actions-Läufe zu Stoßzeiten verzögert starten können.

## Kostenloses API-Kontingent

Standardmäßig werden 15 Aktien pro Lauf aktualisiert. Das passt mit Reserve in ein Free-Kontingent von 20 Calls pro Tag. Änderbar über `BATCH_SIZE` im Workflow.

## Manuelles Testen lokal

```bash
python -m http.server 8000
```

Dann `http://localhost:8000` öffnen.

## Manuelles Screening lokal

```bash
EODHD_API_KEY=dein_key python scripts/screen.py --batch-size 3
```

Unter Windows PowerShell:

```powershell
$env:EODHD_API_KEY="dein_key"
python scripts/screen.py --batch-size 3
```

## Hinweis

Der Pilot ist ein technischer und methodischer Test. Der Score ist keine Anlageberatung und ersetzt keine eigene Prüfung.
