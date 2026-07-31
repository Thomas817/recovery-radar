# Recovery Radar – GitHub-ready

## Installation

1. ZIP auf dem Computer entpacken.
2. Den **Inhalt** des entpackten Ordners in das Hauptverzeichnis des GitHub-Repositorys hochladen.
3. Nicht die ZIP-Datei selbst hochladen.

Direkt sichtbar sein müssen: `.github`, `data`, `scripts`, `index.html`, `netlify.toml`, `README.md`.

## API-Key

`Settings → Secrets and variables → Actions → New repository secret`

Name: `EODHD_API_KEY`

Wert: ausschließlich der API-Schlüssel.

## Erster Lauf

`Actions → Recovery Radar Daily Screening → Run workflow`

Zum Testen Batch-Größe `3` verwenden. Der tägliche Lauf verarbeitet 15 Unternehmen rotierend.
