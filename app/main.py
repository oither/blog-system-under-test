from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .database import engine, Base
from .routers import users, articles, comments, auth

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Blog System Under Test", version="1.0.0")

# ✅ 模板引擎（不涉及路径匹配，位置无影响）
templates = Jinja2Templates(directory="templates")

# 注册 API 路由
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(articles.router)   # Day2 取消注释
app.include_router(comments.router)   # Day3 取消注释


@app.get("/")
def root():
    return {"message": "Blog API is running. Visit /docs for Swagger UI."}


@app.get("/ui")
def ui_page(request: Request):
    # Jinja2 3.x 推荐写法：request 作为显式关键字参数
    return templates.TemplateResponse(name="index.html", context={"request": request})


# 静态文件挂载放在最后，避免拦截 API 路由或产生 404
app.mount("/static", StaticFiles(directory="static"), name="static")