from fastapi import FastAPI
from database import supabase

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}