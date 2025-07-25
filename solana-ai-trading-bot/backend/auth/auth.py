from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from loguru import logger

# Configuration for token
SECRET_KEY = "your-super-secret-key" # TODO: Load from environment variable in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class UserInDB:
    def __init__(self, username: str, hashed_password: str):
        self.username = username
        self.hashed_password = hashed_password

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(stored_username, stored_password_hash, username, password):
    if username != stored_username:
        return None
    if not verify_password(password, stored_password_hash):
        return None
    return UserInDB(username=username, hashed_password=stored_password_hash)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        # In a real app, you'd fetch the user from a DB
        # For this project, we'll use the hardcoded username from settings
        from ..config.settings import initiate_settings
        settings = initiate_settings()
        if username != settings.WEB_USERNAME:
            raise credentials_exception
        # Vérification du mot de passe stocké (hashé ou non)
        stored_password = settings.WEB_PASSWORD
        stored_password_hash = get_password_hash(stored_password) if not stored_password.startswith("$2b$") else stored_password
        return UserInDB(username=username, hashed_password=stored_password_hash)
    except JWTError:
        raise credentials_exception