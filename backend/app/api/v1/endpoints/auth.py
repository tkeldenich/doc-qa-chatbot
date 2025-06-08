from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.database import get_db
from app.core.security import create_access_token
from app.schemas.token import Token
from app.services.user import user_service

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Token:
    """Login endpoint."""
    user = await user_service.authenticate(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=user.id)
    return Token(access_token=access_token, token_type="bearer")  # nosec B106


@router.post("/test-token", response_model=dict)
async def test_token(
    current_user=Depends(deps.get_current_active_user),
) -> dict:
    """Test access token."""
    return {"message": "Token is valid", "user_id": current_user.id}
