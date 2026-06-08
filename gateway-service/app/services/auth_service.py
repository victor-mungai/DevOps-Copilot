import os
import jwt


def decode_token(token: str) -> dict:
    secret = os.getenv("JWT_SECRET", "dev-secret")
    algorithms = [os.getenv("JWT_ALGORITHM", "HS256")]
    return jwt.decode(token, secret, algorithms=algorithms)
