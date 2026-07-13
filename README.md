# Family Tree

A self-hosted family tree / genealogy web app — a simplified, self-hosted alternative to Ancestry.com. Built with Flask and SQLite so it can eventually run on modest hardware (e.g. a Raspberry Pi).

## Features

- **People & profiles** — add people with names, sex, birth/death dates & places, notes.
- **Family relationships** — link parents, spouses (including multiple marriages), and children. Existing people can be linked via a live search instead of re-entering them.
- **Interactive family tree** — pan/zoom SVG pedigree view centered on any person, showing ancestors to the left and descendants to the right. Click any card to re-center the tree on that person.
- **Life events** — free-form events (residence, occupation, baptism, etc.) beyond birth/death.
- **Photos & documents** — upload and attach files to a person's profile; the first photo becomes their profile picture automatically (can be changed).
- **GEDCOM import/export** — download your tree as a standard `.ged` file (readable by Ancestry.com, FamilySearch, Gramps, etc.), or import one to merge or replace your data.
- **Search** — find people by name from the header search box.

## Running it locally

Prerequisite: install [`uv`](https://docs.astral.sh/uv/) if you don't already have it.

```
$ curl -LsSf https://astral.sh/uv/install.sh | sh
```

1. Sync the dependencies

   ```
   $ uv sync
   ```

2. Run the app

   ```
   $ uv run python run.py
   ```

3. Open http://localhost:5000 in your browser.

Data is stored in a local SQLite database and uploaded files under `instance/` (both are git-ignored).

## Running the tests

```
$ uv run pytest
```

## Project layout

```
app/
  models.py          SQLAlchemy models (Person, Family, FamilyChild, Event, Media, MediaLink)
  routes/            Flask blueprints (people, families, tree, media, gedcom)
  gedcom_import.py    GEDCOM 5.5.1 parser
  gedcom_export.py    GEDCOM 5.5.1 writer
  templates/          Jinja2 templates
  static/             CSS and vanilla JS (family tree renderer, relative-picker autocomplete)
run.py                Dev server entry point
```

## Deploying to a Raspberry Pi

See [DEPLOY.md](DEPLOY.md) for step-by-step instructions to install this as a `systemd` service on a Raspberry Pi (or any Debian-based Linux), running under `gunicorn` so it starts on boot and restarts on failure.
