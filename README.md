# Amala & Palmwine Festival + Waves Stem Lab

This repository contains two independent applications:

1. The Amala & Palmwine Festival public marketing website.
2. Waves Stem Lab, a separate audio-analysis and Demucs stem-separation service.

## Festival website
- Main page: index.html
- Responsive festival marketing design and top-of-page vendor-category carousel.
- Sections for the event story, food and culture, vendor participation, event details and an online live-stream area.
- Public event listing information used in the first draft: Sunday, 13 December 2026, 12 noon, The Stable, 41 Bode Thomas Street, Surulere, Lagos. Confirm all event details with the organiser before publishing final ticketing or travel information.
- Individual vendor profiles and live broadcast player remain ready for official names, photography and stream URL.

## Waves Stem Lab
See stem-lab/README.md for installation, API routes and deployment. The backend uses Demucs htdemucs for vocals, drums, bass and other stems, accepts batches of up to 30 files and packages results as ZIP archives. It is independent of the festival site.

GitHub Pages cannot run the Python audio processor. The stem-lab backend must be deployed separately to a Python-capable server with persistent storage and adequate compute.

## Website deployment
The GitHub Actions workflow in .github/workflows/pages.yml deploys only the static root landing page when index.html changes. GitHub Pages must be enabled for this repository with GitHub Actions as the publishing source.

Important URL note: this repository is owned by the GitHub account digiprodngmarketing-a11y, so its default project-site URL follows that owner's domain and includes the repository path. The exact address amalaandpalmwinefestival.github.io requires a GitHub user or organization named amalaandpalmwinefestival and a repository named amalaandpalmwinefestival.github.io (or a custom domain configured and owned by the project). See GitHub's official Pages documentation.
