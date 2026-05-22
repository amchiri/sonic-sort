# SonicSort

Optimiseur de métadonnées musicales pour **Plex** et **Jellyfin**.

Lit les tags audio existants, identifie chaque morceau via empreinte acoustique (AcoustID + MusicBrainz), normalise titres/artistes/albums, puis range les fichiers dans la structure standard : `Artist/Album (Year)/[Disc-]Track - Title.ext` (compatible Plex & Jellyfin).

## Fonctionnalités

- **Scan récursif** : MP3, FLAC, M4A, AAC, OGG, OPUS, WAV, AIFF
- **Fingerprint AcoustID** via `fpcalc` (chromaprint) — identifie même sans tags
- **Enrichissement MusicBrainz** : titre, artiste, album, année, numéro de piste
- **Normalisation** : casse cohérente (`Title Case` qui respecte articles FR/EN), `feat.` unifié, accents nettoyés
- **Renommage Plex-friendly** : caractères illégaux Windows/Linux échappés
- **Mode dry-run** : prévisualise sans modifier
- **Trigger Plex & Jellyfin auto** après traitement
- **Rapport JSON** exportable

## Pipeline

```
[Scan] → [Lecture tags] → [Fingerprint AcoustID] → [Match MusicBrainz]
       → [Fusion + Normalisation] → [Écriture tags] → [Renommage/Move] → [Plex refresh]
```

## Installation

### Local (Python ≥ 3.9)

```bash
git clone https://github.com/amchiri/sonic-sort.git
cd sonic-sort
pip install -e .
```

Installe `fpcalc` (chromaprint) depuis https://acoustid.org/chromaprint et mets-le dans le PATH.

### Docker

```bash
docker build -t sonic-sort .
docker run --rm \
  -v /chemin/musique:/music \
  -e ACOUSTID_API_KEY=xxx \
  -e MB_CONTACT=ton@email.com \
  sonic-sort run /music --dry-run
```

Ou via `docker-compose.yml` fourni (`docker compose up`).

### unRAID (sans Docker, via Miniforge)

```bash
# install miniforge en user-space
mkdir -p /mnt/user/appdata/sonic-sort
cd /tmp
wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
bash Miniforge3-Linux-x86_64.sh -b -p /mnt/user/appdata/sonic-sort/miniforge
export PATH="/mnt/user/appdata/sonic-sort/miniforge/bin:$PATH"

# clone + install
git clone https://github.com/amchiri/sonic-sort.git /tmp/repo
mv /tmp/repo/* /tmp/repo/.* /mnt/user/appdata/sonic-sort/ 2>/dev/null
cd /mnt/user/appdata/sonic-sort
pip install -e .

# fpcalc
wget https://github.com/acoustid/chromaprint/releases/download/v1.5.1/chromaprint-fpcalc-1.5.1-linux-x86_64.tar.gz
tar xzf chromaprint-fpcalc-1.5.1-linux-x86_64.tar.gz
cp chromaprint-fpcalc-*/fpcalc /usr/local/bin/
chmod +x /usr/local/bin/fpcalc
mkdir -p /boot/extra && cp /usr/local/bin/fpcalc /boot/extra/
```

Pour la persistance au reboot, voir `scripts/unraid-install.sh`.

## Configuration

```bash
cp .env.example .env
nano .env
```

```ini
ACOUSTID_API_KEY=your_app_key  # https://acoustid.org/new-application
MB_APP_NAME=SonicSort
MB_APP_VERSION=1.0.0
MB_CONTACT=your@email.com      # obligatoire (politesse MusicBrainz)
PLEX_URL=http://localhost:32400
PLEX_TOKEN=                     # optionnel, pour --plex-scan
JELLYFIN_URL=http://localhost:8096
JELLYFIN_API_KEY=               # optionnel, pour --jellyfin-scan (Dashboard → API Keys)
MB_RATE_LIMIT_DELAY=1.0
ACOUSTID_CONFIDENCE_THRESHOLD=0.8
```

## Usage

```bash
# Aperçu sans toucher fichiers (dry-run)
sonic-sort run /chemin/musique --dry-run

# Run réel
sonic-sort run /chemin/musique

# Avec scan Plex automatique après traitement
sonic-sort run /chemin/musique --plex-scan --plex-section 1

# Avec scan Jellyfin (refresh global)
sonic-sort run /chemin/musique --jellyfin-scan

# Jellyfin library spécifique
sonic-sort run /chemin/musique --jellyfin-scan --jellyfin-library <library_id>

# Rapport JSON
sonic-sort run /chemin/musique --report report.json

# Sans fingerprint (rapide, normalise tags existants seulement)
sonic-sort run /chemin/musique --no-fingerprint

# Scan rapport (sans modifier)
sonic-sort scan /chemin/musique

# Liste sections Plex
sonic-sort plex-sections

# Liste libraries Jellyfin
sonic-sort jellyfin-libraries
```

Équivalent sans entry point :
```bash
python -m src run /chemin/musique --dry-run
```

## Architecture

```
src/
├── cli.py                      # CLI Click + Rich
├── pipeline.py                 # Orchestration: scan → identify → normalize → write → rename
├── scanner/library_scanner.py  # Walk récursif filesystem
├── metadata/reader.py          # Lecture tags (ID3, Vorbis, MP4, OGG)
├── fingerprint/acoustid_client.py  # fpcalc + AcoustID lookup
├── matcher/musicbrainz_client.py   # MusicBrainz query + extract
├── normalizer/tag_normalizer.py    # Fusion + casse + écriture
├── renamer/file_renamer.py     # Build target path Plex + move
├── plex/plex_trigger.py        # Optional: trigger Plex scan
├── jellyfin/jellyfin_trigger.py # Optional: trigger Jellyfin scan
└── utils/{config,logger}.py
```

## Tests

```bash
python -m pytest tests/ -v
```

## Dépendances clés

- `mutagen` — read/write tags audio multi-format
- `pyacoustid` — wrapper fpcalc + lookup AcoustID
- `musicbrainzngs` — client MusicBrainz officiel
- `click` + `rich` — CLI + progress bars
- `python-dotenv` — config via `.env`

## Limites connues

- Identification AcoustID dépend de la qualité de l'empreinte (audio < 30 s peu fiable)
- Numéro de piste parfois absent si la release MusicBrainz n'a pas la track-list complète (fallback sur tag existant)
- Releases MusicBrainz multiples : pondération `Official` > non-officiel ; pas de scoring `Album` vs `Single` sans include `release-groups` (non valide pour entity recording)

## Licence

MIT
