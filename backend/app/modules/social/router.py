from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.modules.auth.router import get_current_user
from app.modules.auth.models import User
from app.modules.social import service
from app.modules.social.models import Post
from app.modules.social.schemas import (
    PostCreate,
    PostOut,
    CommentCreate,
    CommentOut,
    FollowOut,
)

router = APIRouter(prefix="/social", tags=["Réseau social"])


def _to_post_out(db: Session, post: Post, viewer_id: str) -> PostOut:
    return PostOut(
        id=post.id,
        author_id=post.author_id,
        content=post.content,
        media_url=post.media_url,
        visibility=post.visibility,
        created_at=post.created_at,
        updated_at=post.updated_at,
        likes_count=service.count_likes(db, post.id),
        comments_count=service.count_comments(db, post.id),
        liked_by_current_user=service.has_liked(db, post.id, viewer_id),
    )


@router.post(
    "/posts",
    response_model=PostOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
)
def create_post(
    data: PostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = service.create_post(db, current_user.id, data.content, data.media_url, data.visibility)
    return _to_post_out(db, post, current_user.id)


@router.get("/feed", response_model=list[PostOut])
def get_feed(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    posts = service.get_feed(db, current_user.id, limit=limit, offset=offset)
    return [_to_post_out(db, p, current_user.id) for p in posts]


@router.get("/users/{user_id}/posts", response_model=list[PostOut])
def get_user_posts(
    user_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    posts = service.get_user_posts(db, user_id, current_user.id, limit=limit, offset=offset)
    return [_to_post_out(db, p, current_user.id) for p in posts]


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service.delete_post(db, post_id, current_user.id)
    except service.PostNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except service.NotAuthorError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.post(
    "/posts/{post_id}/like",
    response_model=dict,
    dependencies=[Depends(rate_limit(max_requests=60, window_seconds=60))],
)
def toggle_like(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        liked = service.toggle_like(db, post_id, current_user.id)
    except service.PostNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return {"liked": liked, "likes_count": service.count_likes(db, post_id)}


@router.post("/posts/{post_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def add_comment(
    post_id: str,
    data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.add_comment(db, post_id, current_user.id, data.content)
    except service.PostNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/posts/{post_id}/comments", response_model=list[CommentOut])
def list_comments(
    post_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return service.list_comments(db, post_id, limit=limit, offset=offset)


@router.post(
    "/users/{user_id}/follow",
    response_model=FollowOut,
    dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60))],
)
def follow_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service.follow_user(db, current_user.id, user_id)
    except service.CannotFollowSelfError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return service.get_follow_status(db, current_user.id, user_id)


@router.delete("/users/{user_id}/follow", response_model=FollowOut)
def unfollow_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service.unfollow_user(db, current_user.id, user_id)
    return service.get_follow_status(db, current_user.id, user_id)


@router.get("/users/{user_id}/follow-status", response_model=FollowOut)
def follow_status(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.get_follow_status(db, current_user.id, user_id)
