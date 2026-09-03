# Pi Cookbook

Pi Cookbook is a small FastAPI web application for saving a personal recipe collection. It serves a lightweight frontend, imports recipe details from supported recipe URLs, and can receive URLs from a device's Web Share workflow.

## Features

- Browse recipes with ingredients, instructions, ratings, and notes.
- Import recipes from URLs using `recipe-scrapers`.
- Check asynchronous import status through the API.
- Share recipe links to the app from supported devices and browsers.

## Run locally

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

Start the app:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` in a browser. The health endpoint is available at `GET /api/health`.

## Test

```bash
pytest
```

## Configuration

Copy `.env.example` to `.env` and adjust its values for your environment. Local `.env` files and the SQLite database are ignored by Git.