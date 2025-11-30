from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import projects, monitor, homepage, scrutiny

app = FastAPI(title="Gemini Project Dashboard")

# CORS is essential since Frontend (37452) talks to Backend (37453)
origins = [
    "http://localhost:37452",
    "http://127.0.0.1:37452",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api")
app.include_router(monitor.router, prefix="/api")
app.include_router(homepage.router, prefix="/api")
app.include_router(scrutiny.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Gemini Project Dashboard API is running"}
