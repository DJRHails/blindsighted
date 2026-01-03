# Blindsighted

Mobile app with FastAPI backend.

## Project Structure

```
blindsighted/
├── app/          # Expo app (TypeScript)
└── api/          # FastAPI backend (Python)
```

## Quick Start

### App Setup

1. Navigate to the app directory:
```bash
cd app
```

2. Install dependencies:
```bash
yarn install
```

3. Start the development server:
```bash
yarn start
```

### API Setup

1. Navigate to the api directory:
```bash
cd api
```

2. Install dependencies using uv:
```bash
uv pip install -e ".[dev]"
```

3. Run the API:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000` with documentation at `http://localhost:8000/docs`

## Development

See individual README files in `app/` and `api/` directories for more details.
