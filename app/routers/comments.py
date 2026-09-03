from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Comment, Article, User
from ..schemas import CommentCreate, CommentResponse
from ..auth import get_current_user

router = APIRouter(prefix="/articles/{article_id}/comments", tags=["Comments"])

@router.post("", response_model=CommentResponse, status_code=201)
def add_comment(
    article_id: int,
    comment: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 检查文章是否存在
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    db_comment = Comment(
        content=comment.content,
        article_id=article_id,
        user_id=current_user.id
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment

@router.get("", response_model=List[CommentResponse])
def list_comments(article_id: int, db: Session = Depends(get_db)):
    return db.query(Comment).filter(Comment.article_id == article_id).all()
    
@router.delete("/{comment_id}", status_code=204)
def delete_comment(
    article_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")
    db.delete(comment)
    db.commit()