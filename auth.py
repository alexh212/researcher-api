from collections.abc import Mapping

from fastapi import Header, HTTPException

from access import UserContext, user_context_from_supabase_user
from database import supabase


def fetch_supabase_user(token: str) -> Mapping[str, object] | None:
    auth_response = supabase.auth.get_user(token)
    user_obj = getattr(auth_response, "user", None)
    if user_obj is None:
        return None
    if hasattr(user_obj, "model_dump"):
        raw_user = user_obj.model_dump()
    elif isinstance(user_obj, Mapping):
        raw_user = dict(user_obj)
    else:
        return None
    return raw_user


def get_authenticated_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> UserContext:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    raw_user = fetch_supabase_user(token)
    user = user_context_from_supabase_user(raw_user)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid authentication token")

    return user
