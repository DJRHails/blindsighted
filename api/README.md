# Blindsighted API

FastAPI backend for the Blindsighted app.

## Setup

Install dependencies using uv:
```bash
uv pip install -e ".[dev]"
```

Or install just the production dependencies:
```bash
uv pip install -e .
```

## Development

Format and lint code:
```bash
ruff check --fix .
ruff format .
```

Type check:
```bash
mypy .
```

## Running the API

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

API documentation available at `http://localhost:8000/docs`
