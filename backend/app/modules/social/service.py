from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.social.models import Post, Comment, Like, Follow


class PostNotFoundError(Exception):
    """Levée quand une publication n'existe pas."""


class NotAuthorError(Exception):
    """Levée quand un utilisateur tente de modifier une publication qui ne lui appartient pas."""


class CannotFollowSelfError(Exception):
    """Levée quand un utilisateur tente de s'abonner à lui-même."""


def create_post(db: Session, author_id: str, content: str, media_url: str | None, visibility: str) -> Post:
    post = Post(author_id=author_id, content=content, media_url=media_url, visibility=visibility)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def get_post(db: Session, post_id: str) -> Post:
    post = db.query(Post).filter(Post.id == post_id).first()
    if post is None:
        raise PostNotFoundError("Publication introuvable.")
    return post


def delete_post(db: Session, post_id: str, requesting_user_id: str) -> None:
    post = get_post(db, post_id)
    if post.author_id != requesting_user_id:
        raise NotAuthorError("Vous ne pouvez supprimer que vos propres publications.")
    db.delete(post)
    db.commit()


def _visible_posts_query(db: Session, viewer_id: str):
    """
    Construit la requête des publications visibles par `viewer_id` :
    publiques, ou de type "followers" si l'utilisateur suit l'auteur,
    ou les siennes propres quelle que soit leur visibilité.
    """
    followed_ids_subquery = (
        select(Follow.followed_id).where(Follow.follower_id == viewer_id)
    )
    return db.query(Post).filter(
        (Post.visibility == "public")
        | (Post.author_id == viewer_id)
        | ((Post.visibility == "followers") & (Post.author_id.in_(followed_ids_subquery)))
    )


def get_feed(db: Session, viewer_id: str, limit: int = 20, offset: int = 0) -> list[Post]:
    """
    Fil d'actualité : publications des personnes suivies + les siennes,
    triées des plus récentes aux plus anciennes.
    """
    followed_ids_subquery = select(Follow.followed_id).where(Follow.follower_id == viewer_id)
    return (
        db.query(Post)
        .filter((Post.author_id == viewer_id) | (Post.author_id.in_(followed_ids_subquery)))
        .order_by(Post.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_user_posts(db: Session, author_id: str, viewer_id: str, limit: int = 20, offset: int = 0) -> list[Post]:
    """Publications d'un profil donné, filtrées selon ce que le visiteur a le droit de voir."""
    return (
        _visible_posts_query(db, viewer_id)
        .filter(Post.author_id == author_id)
        .order_by(Post.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def count_likes(db: Session, post_id: str) -> int:
    return db.query(func.count(Like.id)).filter(Like.post_id == post_id).scalar() or 0


def count_comments(db: Session, post_id: str) -> int:
    return db.query(func.count(Comment.id)).filter(Comment.post_id == post_id).scalar() or 0


def has_liked(db: Session, post_id: str, user_id: str) -> bool:
    return (
        db.query(Like).filter(Like.post_id == post_id, Like.user_id == user_id).first() is not None
    )


def toggle_like(db: Session, post_id: str, user_id: str) -> bool:
    """Ajoute ou retire un like. Retourne True si désormais aimé, False sinon."""
    get_post(db, post_id)  # vérifie l'existence, lève PostNotFoundError sinon
    existing = db.query(Like).filter(Like.post_id == post_id, Like.user_id == user_id).first()
    if existing:
        db.delete(existing)
        db.commit()
        return False

    db.add(Like(post_id=post_id, user_id=user_id))
    db.commit()
    return True


def add_comment(db: Session, post_id: str, author_id: str, content: str) -> Comment:
    get_post(db, post_id)  # vérifie l'existence
    comment = Comment(post_id=post_id, author_id=author_id, content=content)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def list_comments(db: Session, post_id: str, limit: int = 50, offset: int = 0) -> list[Comment]:
    return (
        db.query(Comment)
        .filter(Comment.post_id == post_id)
        .order_by(Comment.created_at.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def follow_user(db: Session, follower_id: str, followed_id: str) -> None:
    if follower_id == followed_id:
        raise CannotFollowSelfError("Vous ne pouvez pas vous abonner à vous-même.")
    existing = (
        db.query(Follow)
        .filter(Follow.follower_id == follower_id, Follow.followed_id == followed_id)
        .first()
    )
    if existing is None:
        db.add(Follow(follower_id=follower_id, followed_id=followed_id))
        db.commit()


def unfollow_user(db: Session, follower_id: str, followed_id: str) -> None:
    existing = (
        db.query(Follow)
        .filter(Follow.follower_id == follower_id, Follow.followed_id == followed_id)
        .first()
    )
    if existing is not None:
        db.delete(existing)
        db.commit()


def get_follow_status(db: Session, viewer_id: str, profile_id: str) -> dict:
    is_following = (
        db.query(Follow)
        .filter(Follow.follower_id == viewer_id, Follow.followed_id == profile_id)
        .first()
        is not None
    )
    followers_count = db.query(func.count(Follow.id)).filter(Follow.followed_id == profile_id).scalar() or 0
    following_count = db.query(func.count(Follow.id)).filter(Follow.follower_id == profile_id).scalar() or 0
    return {
        "is_following": is_following,
        "followers_count": followers_count,
        "following_count": following_count,
    }
