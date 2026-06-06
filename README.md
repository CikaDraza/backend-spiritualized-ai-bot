# Spiritualized Backend

Ovaj backend je namenjen FastAPI serveru koji služi kao centralni kanal za generisanje odgovora bota i kasnije može da se poveže sa PostgreSQL i MongoDB bazama.

## Pokretanje

1. Kreiraj virtualno okruženje:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Instaliraj zavisnosti:

```bash
pip install -r requirements.txt
```

3. Napravi `.env` fajl koristeći `.env.example` i dodaj `OPENAI_API_KEY`.

4. Pokreni server:

```bash
uvicorn app.main:app --reload --port 8000
```

## API endpoint

- `POST /chat`
  - telo: `{ "message": "...", "history": [{ "role": "user"|"assistant", "content": "..." }]}`
  - responz: `{ "assistant": "..." }`
