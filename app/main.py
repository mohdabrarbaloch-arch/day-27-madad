from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .config import get_settings
from .database import Base, engine
from .ratelimit import limiter
from .routers import admin, auth, campaigns, donations

settings = get_settings()

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Madad API",
    description="Transparent medical crowdfunding for Pakistan — verified campaigns, public donation ledger.",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

_allowed = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed if "*" not in _allowed else ["*"],
    allow_credentials=("*" not in _allowed),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests — slow down and try again shortly."},
    )


app.include_router(auth.router)
app.include_router(campaigns.router)
app.include_router(donations.router)
app.include_router(admin.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name, "env": settings.environment}


# Serve the SPA (static files are mounted last so /api stays on top)
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
