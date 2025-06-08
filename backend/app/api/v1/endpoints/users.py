from typing import Any, List

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic.networks import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import User as UserSchema
from app.schemas.user import UserCreate, UserUpdate
from app.services.user import user_service

router = APIRouter()


@router.get("/", response_model=List[UserSchema])
async def read_users(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Retrieve users."""
    if not user_service.is_superuser(current_user):
        raise HTTPException(
            status_code=400, detail="The user doesn't have enough privileges"
        )
    users = await user_service.get_multi(db, skip=skip, limit=limit)
    return users


@router.post("/", response_model=UserSchema)
async def create_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: UserCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Create new user."""
    if not user_service.is_superuser(current_user):
        raise HTTPException(
            status_code=400, detail="The user doesn't have enough privileges"
        )
    user = await user_service.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    user = await user_service.create(db, obj_in=user_in)
    return user


@router.put("/me", response_model=UserSchema)
async def update_user_me(
    *,
    db: AsyncSession = Depends(get_db),
    password: str = Body(None),
    full_name: str = Body(None),
    email: EmailStr = Body(None),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Update own user."""
    current_user_data = jsonable_encoder(current_user)
    user_in = UserUpdate(**current_user_data)
    if password is not None:
        user_in.password = password
    if full_name is not None:
        user_in.full_name = full_name
    if email is not None:
        user_in.email = email
    user = await user_service.update(db, db_obj=current_user, obj_in=user_in)
    return user


@router.get("/me", response_model=UserSchema)
async def read_user_me(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Get current user."""
    return current_user


@router.get("/{user_id}", response_model=UserSchema)
async def read_user_by_id(
    user_id: int,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get a specific user by id."""
    user = await user_service.get(db, id=user_id)
    if user == current_user:
        return user
    if not user_service.is_superuser(current_user):
        raise HTTPException(
            status_code=400, detail="The user doesn't have enough privileges"
        )
    return user
