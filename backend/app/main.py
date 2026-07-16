from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import (
    account,
    activities,
    auth,
    billing,
    health,
    notifications,
    quality,
    reviews,
    saved_searches,
    scouts,
    selfcare,
    training,
    videos,
    watchlist,
)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番では制限すること
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(videos.router, prefix="/api/videos", tags=["videos"])
app.include_router(scouts.router, prefix="/api/scouts", tags=["scouts"])
app.include_router(watchlist.router, prefix="/api/scouts/watchlist", tags=["watchlist"])
app.include_router(
    saved_searches.router, prefix="/api/scouts/saved-searches", tags=["saved-searches"]
)
app.include_router(activities.router, prefix="/api/activities", tags=["activities"])
app.include_router(selfcare.router, prefix="/api/selfcare", tags=["selfcare"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(training.router, prefix="/api/training", tags=["training"])
app.include_router(reviews.router, prefix="/api/reviews", tags=["reviews"])
app.include_router(account.router, prefix="/api/account", tags=["account"])
app.include_router(billing.router, prefix="/api/billing", tags=["billing"])
app.include_router(quality.router, prefix="/api/quality", tags=["quality"])


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "version": settings.APP_VERSION}
