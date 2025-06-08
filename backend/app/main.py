import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt

# Import settings properly
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# JWT Configuration - Use settings instead of hardcoded values
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


# Simple password hashing (no bcrypt dependency issues)
def hash_password(password: str) -> str:
    """Simple password hashing using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return hash_password(plain_password) == hashed_password


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Fake user database (we'll replace with real DB later)
# Note: In production, you'd load this from a real database
fake_users_db: Dict[str, Dict[str, str]] = {
    "test@example.com": {
        "username": "test@example.com",
        "full_name": "Test User",
        "email": "test@example.com",
        # This is just for development
        "hashed_password": hash_password("testpass"),
    }
}

# CORS middleware - use settings for origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        [str(origin) for origin in settings.BACKEND_CORS_ORIGINS]
        if settings.BACKEND_CORS_ORIGINS
        else ["*"]
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_user(username: str) -> Optional[Dict[str, str]]:
    if username in fake_users_db:
        user_dict = fake_users_db[username]
        return user_dict
    return None


def authenticate_user(
    username: str, password: str
) -> Optional[Dict[str, str]]:
    """Authenticate user and return user data if successful, None if failed."""
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> Dict[str, str]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(username=username)
    if user is None:
        raise credentials_exception
    return user


@app.get("/")
async def root() -> Dict[str, str]:
    return {
        "message": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
    }


@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "healthy", "version": settings.VERSION}


# Test configuration
@app.get("/config-test")
async def config_test() -> Dict[str, Any]:
    return {
        "project_name": settings.PROJECT_NAME,
        "debug": settings.DEBUG,
        "environment": settings.ENVIRONMENT,
    }


@app.post("/api/v1/auth/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Dict[str, str]:
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/v1/auth/me")
async def read_users_me(
    current_user: Dict[str, str] = Depends(get_current_user),
) -> Dict[str, str]:
    return {
        "username": current_user["username"],
        "email": current_user["email"],
        "full_name": current_user["full_name"],
    }


@app.get("/api/v1/protected")
async def protected_route(
    current_user: Dict[str, str] = Depends(get_current_user),
) -> Dict[str, str]:
    return {
        "message": f"Hello {
            current_user['full_name']}, this is a protected route!"
    }


@app.get("/api/v1/test-protected")
async def protected_endpoint(
    current_user: Dict[str, str] = Depends(get_current_user),
) -> Dict[str, str]:
    return {
        "message": "This is now properly protected!",
        "user": current_user["username"],
    }


# Debug endpoint to test password hashing - only available in development
@app.get("/api/v1/debug/test-hash")
async def test_hash() -> Dict[str, Any]:
    if settings.ENVIRONMENT != "development":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debug endpoints not available in production",
        )

    test_password = "testpass"  # nosec B105
    hashed = hash_password(test_password)
    return {
        "original_password": test_password,
        "hashed_password": hashed,
        "stored_hash": fake_users_db["test@example.com"]["hashed_password"],
        "passwords_match": hashed
        == fake_users_db["test@example.com"]["hashed_password"],
    }
