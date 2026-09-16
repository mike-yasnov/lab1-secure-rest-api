from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Post, User
from app.sanitize import sanitize
from app.schemas import (
    LoginRequest,
    PostCreate,
    PostOut,
    Token,
    UserCreate,
    UserOut,
)
from app.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Secure REST API — ИТМО, работа 1",
    version="1.0.0",
)


@app.get("/health", tags=["service"], summary="Проверка доступности сервиса")
def health() -> dict:
    return {"status": "ok"}


@app.post(
    "/auth/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    tags=["auth"],
    summary="Регистрация пользователя",
)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким логином уже существует",
        )
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post(
    "/auth/login",
    response_model=Token,
    tags=["auth"],
    summary="Аутентификация, выдача JWT",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> Token:
    user = db.query(User).filter(User.username == payload.username).first()
    # Единое сообщение об ошибке — чтобы не раскрывать существование логина.
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )
    token = create_access_token(subject=user.username)
    return Token(access_token=token)


@app.get(
    "/api/data",
    response_model=list[PostOut],
    tags=["api"],
    summary="Список постов (требуется аутентификация)",
)
def get_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Post]:
    return db.query(Post).order_by(Post.created_at.desc()).all()


@app.post(
    "/api/posts",
    response_model=PostOut,
    status_code=status.HTTP_201_CREATED,
    tags=["api"],
    summary="Создать пост (требуется аутентификация)",
)
def create_post(
    payload: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Post:
    post = Post(
        title=sanitize(payload.title),
        content=sanitize(payload.content),
        author_id=current_user.id,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post
