from fastapi import FastAPI

app = FastAPI(title="IoT Greenhouse API")

@app.get("/")
def root():
    return {"message": "IoT Greenhouse API running"}