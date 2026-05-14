from fastapi import FastAPI

app = FastAPI(title="Insight ECG API", version="0.1.0")

@app.get("/health")
def health_check():
    return {
            "status": "ok", 
            "message": "ta rodando"
        }
