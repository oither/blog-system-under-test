from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
from ..schemas import UserCreate, UserResponse
from ..auth import get_password_hash

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # ✅ 同时检查用户名和邮箱，合并查询减少 DB 往返
    existing = db.query(User).filter(
        (User.username == user.username) | (User.email == user.email)
    ).first()

    if existing:
        # ⚠️ 不透露具体哪个字段重复，防止用户/邮箱枚举攻击
        raise HTTPException(
            status_code=400,
            detail="Username or email already registered"
        )

    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=get_password_hash(user.password)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user