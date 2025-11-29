try:
    from fastapi import FastAPI
except Exception as e:
    raise SystemExit("FastAPI not installed. Add it to pyproject and reinstall.") from e

app = FastAPI(title="IRCI API")

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}
