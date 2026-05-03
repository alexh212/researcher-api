from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class UserContext:
    id: str
    email: str
    signed_in: bool
    display_name: str | None
    avatar_url: str | None


def user_context_from_supabase_user(raw_user: Mapping[str, object] | None) -> UserContext | None:
    if raw_user is None:
        return None

    user_id = raw_user.get("id")
    email = raw_user.get("email")

    if not isinstance(user_id, str) or not user_id:
        return None
    if not isinstance(email, str) or not email:
        return None

    metadata_obj = raw_user.get("user_metadata")
    metadata = metadata_obj if isinstance(metadata_obj, Mapping) else {}

    full_name = metadata.get("full_name")
    name = metadata.get("name")
    avatar_url = metadata.get("avatar_url")

    display_name: str | None = None
    if isinstance(full_name, str) and full_name:
        display_name = full_name
    elif isinstance(name, str) and name:
        display_name = name

    avatar: str | None = avatar_url if isinstance(avatar_url, str) and avatar_url else None

    return UserContext(
        id=user_id,
        email=email,
        signed_in=True,
        display_name=display_name,
        avatar_url=avatar,
    )


def has_access(user: UserContext | None, action: str) -> bool:
    if user is None or not user.signed_in:
        return False
    if action == "generate_report":
        return True
    return True


def get_accessible_projects(user: UserContext, projects: list[Mapping[str, object]]) -> list[Mapping[str, object]]:
    return [project for project in projects if project.get("owner_id") == user.id]
