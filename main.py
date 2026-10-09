from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import Base, engine
from routers import auth_router, goal_router

# ── 创建 FastAPI 应用实例 ──
app = FastAPI(title="PlanAI API")

# ── CORS 中间件（允许所有来源，开发阶段使用） ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 注册路由 ──
app.include_router(auth_router.router)
app.include_router(goal_router.router)


# ── 启动事件：自动创建数据库表 ──
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


# ── 挂载静态文件（前端页面），必须在路由注册之后 ──
app.mount("/", StaticFiles(directory="static", html=True), name="static")
