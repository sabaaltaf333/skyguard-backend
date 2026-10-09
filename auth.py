from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta

# bcrypt se password hash karenge
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token banane ke settings
SECRET_KEY = "my-secret-key-change-later"
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 8

# Password ko hash (chhupa) karna
def hash_password(password: str) -> str:
    # bcrypt sirf 72 bytes leta hai -- isi wajah se error aa rahi thi.
    # Isliye pehle 72 bytes tak cut karte hain.
    pw_bytes = password.encode("utf-8")[:72]
    return pwd_context.hash(pw_bytes)

# Password check karna (login ke waqt kaam aayega)
def verify_password(plain_password: str, hashed_password: str) -> bool:
    pw_bytes = plain_password.encode("utf-8")[:72]
    return pwd_context.verify(pw_bytes, hashed_password)

# Login kamyab hone par token banana
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Token ke andar se user ki maloomat nikaalna (verify karna)
def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload   # ismein user_id aur role hote hain
    except JWTError:
        return None      # token galat ya expire ho gaya