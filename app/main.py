from fastapi import FastAPI
from .database import engine, Base
from .routers import users, articles, comments, auth  # ← 加上 auth


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Blog System Under Test", version="1.0.0")

# 注册路由
app.include_router(auth.router)      
app.include_router(users.router)
app.include_router(articles.router)   # Day2 取消注释
# app.include_router(comments.router)   # Day3 取消注释

@app.get("/")
def root():
    return {"message": "Blog API is running. Visit /docs for Swagger UI."}