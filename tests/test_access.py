from access import (
    UserContext,
    get_accessible_projects,
    has_access,
    user_context_from_supabase_user,
)


def test_has_access_denies_signed_out_user():
    assert has_access(None, "generate_report") is False


def test_has_access_allows_signed_in_user():
    user = UserContext(
        id="user-1",
        email="user@example.com",
        signed_in=True,
        display_name=None,
        avatar_url=None,
    )
    assert has_access(user, "generate_report") is True


def test_user_context_from_supabase_user_requires_email():
    raw_user = {"id": "abc-123"}
    assert user_context_from_supabase_user(raw_user) is None


def test_user_context_from_supabase_user_maps_google_metadata():
    raw_user = {
        "id": "abc-123",
        "email": "user@example.com",
        "user_metadata": {
            "full_name": "Alex H",
            "avatar_url": "https://example.com/avatar.png",
        },
    }

    user = user_context_from_supabase_user(raw_user)

    assert user is not None
    assert user.id == "abc-123"
    assert user.email == "user@example.com"
    assert user.display_name == "Alex H"
    assert user.avatar_url == "https://example.com/avatar.png"
    assert user.signed_in is True


def test_get_accessible_projects_returns_only_owner_projects():
    user = UserContext(
        id="user-1",
        email="user@example.com",
        signed_in=True,
        display_name=None,
        avatar_url=None,
    )
    projects = [
        {"id": "p1", "owner_id": "user-1", "name": "Mine"},
        {"id": "p2", "owner_id": "user-2", "name": "Other"},
    ]

    visible = get_accessible_projects(user, projects)

    assert visible == [{"id": "p1", "owner_id": "user-1", "name": "Mine"}]
