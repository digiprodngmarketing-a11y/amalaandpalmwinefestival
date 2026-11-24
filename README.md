# Amala & Palmwine Festival + Waves Stem Lab

This repository contains two independent applications:

1. The Amala & Palmwine Festival public marketing website.
2. Waves Stem Lab, a separate audio-analysis and Demucs stem-separation service.

## Festival website
- Main deployable site: docs/index.html
- Editable source copy: index.html
- Responsive festival marketing design and top-of-page vendor-category carousel.
- Sections for the event story, food and culture, vendor participation, event details and online live-stream area.
- Public event listing information used in this draft: Sunday, 13 December 2026, 12 noon, The Stable, 41 Bode Thomas Street, Surulere, Lagos. Confirm all event details with the organiser before publishing final ticketing or travel information.
- Vendor cards are illustrative food categories, not confirmed individual vendor identities. Add approved vendor names, menus and photographs when supplied.
- The live broadcast area is prepared but needs the organiser's official streaming URL before it can play a live event.

## Publish the festival website
The repository owner is digiprodngmarketing-a11y. To publish this project site from this repository, open Settings → Pages and choose:
- Source: Deploy from a branch
- Branch: main
- Folder: /docs
- Save

The normal project URL for this repository will be:
https://digiprodngmarketing-a11y.github.io/amalaandpalmwinefestival/

The exact requested address https://amalaandpalmwinefestival.github.io is a GitHub user/organisation site address. GitHub requires the repository to be named amalaandpalmwinefestival.github.io and owned by a GitHub user or organisation whose account name is amalaandpalmwinefestival. The current connected owner is digiprodngmarketing-a11y, so it cannot publish to that exact hostname. See GitHub's official Pages documentation.

## Waves Stem Lab
See stem-lab/README.md for installation, API routes and deployment. The backend uses Demucs htdemucs for vocals, drums, bass and other stems, accepts batches of up to 30 files and packages results as ZIP archives. It is independent of the festival site.

GitHub Pages only hosts static files; it cannot run Python, Demucs, PyTorch or process uploaded audio. Deploy the stem-lab backend separately to a Python-capable host with persistent storage and adequate compute. The backend code is committed but not yet deployed as a public processing service.
