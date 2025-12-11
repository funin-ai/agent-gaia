"""OAuth authentication routes for Google and GitHub."""

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from pydantic import BaseModel

from src.core.settings import get_settings
from src.core.auth import (
    create_access_token,
    get_current_user,
    TokenData,
    generate_state_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from src.core.user_repository import UserRepository
from src.core.auth import UserCreate
from src.utils.logger import logger

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# OAuth client setup
oauth = OAuth()


def setup_oauth():
    """Configure OAuth providers."""
    settings = get_settings()

    # Google OAuth
    if settings.auth.google_client_id:
        oauth.register(
            name='google',
            client_id=settings.auth.google_client_id,
            client_secret=settings.auth.google_client_secret,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={
                'scope': 'openid email profile'
            }
        )
        logger.info("Google OAuth configured")

    # GitHub OAuth
    if settings.auth.github_client_id:
        oauth.register(
            name='github',
            client_id=settings.auth.github_client_id,
            client_secret=settings.auth.github_client_secret,
            authorize_url='https://github.com/login/oauth/authorize',
            access_token_url='https://github.com/login/oauth/access_token',
            api_base_url='https://api.github.com/',
            client_kwargs={
                'scope': 'read:user user:email'
            }
        )
        logger.info("GitHub OAuth configured")


# Initialize OAuth on module load
setup_oauth()


class AuthStatus(BaseModel):
    """Authentication status response."""
    authenticated: bool
    user: Optional[dict] = None


class TokenResponse(BaseModel):
    """Token response for successful authentication."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60
    user: dict


@router.get("/status")
async def auth_status(request: Request) -> AuthStatus:
    """Check authentication status.

    Returns current user info if authenticated.
    """
    # Check for token in cookie or header
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        return AuthStatus(authenticated=False)

    from src.core.auth import decode_access_token
    token_data = decode_access_token(token)

    if not token_data:
        return AuthStatus(authenticated=False)

    # Get full user from database
    user = await UserRepository.get_by_id(token_data.user_id)

    if not user:
        return AuthStatus(authenticated=False)

    return AuthStatus(
        authenticated=True,
        user={
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "picture": user.picture,
            "provider": user.provider,
        }
    )


@router.get("/google/login")
async def google_login(request: Request):
    """Initiate Google OAuth flow."""
    settings = get_settings()

    if not settings.auth.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth not configured"
        )

    redirect_uri = settings.auth.callback_url.format(provider="google")

    # Store state in session for CSRF protection
    state = generate_state_token()
    request.session["oauth_state"] = state

    return await oauth.google.authorize_redirect(request, redirect_uri, state=state)


@router.get("/google/callback")
async def google_callback(request: Request):
    """Handle Google OAuth callback."""
    settings = get_settings()

    try:
        # Verify state
        stored_state = request.session.get("oauth_state")
        received_state = request.query_params.get("state")

        if not stored_state or stored_state != received_state:
            logger.warning("OAuth state mismatch - possible CSRF attack")
            raise HTTPException(status_code=400, detail="Invalid state parameter")

        # Exchange code for token
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')

        if not user_info:
            # Fetch user info if not in token
            resp = await oauth.google.get('https://www.googleapis.com/oauth2/v3/userinfo', token=token)
            user_info = resp.json()

        # Create or update user
        user_data = UserCreate(
            email=user_info.get('email'),
            name=user_info.get('name'),
            picture=user_info.get('picture'),
            provider='google',
            provider_id=user_info.get('sub')
        )

        user = await UserRepository.upsert_from_oauth(user_data)

        if not user:
            raise HTTPException(status_code=500, detail="Failed to create user")

        # Create JWT token
        access_token = create_access_token(
            data={
                "user_id": user.id,
                "email": user.email,
                "provider": "google"
            },
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        # Redirect to frontend with token
        response = RedirectResponse(
            url=f"{settings.auth.frontend_url}?auth_success=true",
            status_code=302
        )

        # Set token in HTTP-only cookie
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=settings.app_env == "prod",
            samesite="lax",
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

        # Clear session state
        request.session.pop("oauth_state", None)

        logger.info(f"User logged in via Google: {user.email}")
        return response

    except Exception as e:
        logger.error(f"Google OAuth callback error: {e}")
        return RedirectResponse(
            url=f"{settings.auth.frontend_url}?auth_error={str(e)}",
            status_code=302
        )


@router.get("/github/login")
async def github_login(request: Request):
    """Initiate GitHub OAuth flow."""
    settings = get_settings()

    if not settings.auth.github_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth not configured"
        )

    redirect_uri = settings.auth.callback_url.format(provider="github")

    # Store state in session for CSRF protection
    state = generate_state_token()
    request.session["oauth_state"] = state

    return await oauth.github.authorize_redirect(request, redirect_uri, state=state)


@router.get("/github/callback")
async def github_callback(request: Request):
    """Handle GitHub OAuth callback."""
    settings = get_settings()

    try:
        # Verify state
        stored_state = request.session.get("oauth_state")
        received_state = request.query_params.get("state")

        if not stored_state or stored_state != received_state:
            logger.warning("OAuth state mismatch - possible CSRF attack")
            raise HTTPException(status_code=400, detail="Invalid state parameter")

        # Exchange code for token
        token = await oauth.github.authorize_access_token(request)

        # Fetch user info from GitHub API
        resp = await oauth.github.get('user', token=token)
        user_info = resp.json()

        # GitHub might not return email in user endpoint, need separate call
        email = user_info.get('email')
        if not email:
            emails_resp = await oauth.github.get('user/emails', token=token)
            emails = emails_resp.json()
            # Get primary verified email
            for e in emails:
                if e.get('primary') and e.get('verified'):
                    email = e.get('email')
                    break

        if not email:
            raise HTTPException(status_code=400, detail="Could not get email from GitHub")

        # Create or update user
        user_data = UserCreate(
            email=email,
            name=user_info.get('name') or user_info.get('login'),
            picture=user_info.get('avatar_url'),
            provider='github',
            provider_id=str(user_info.get('id'))
        )

        user = await UserRepository.upsert_from_oauth(user_data)

        if not user:
            raise HTTPException(status_code=500, detail="Failed to create user")

        # Create JWT token
        access_token = create_access_token(
            data={
                "user_id": user.id,
                "email": user.email,
                "provider": "github"
            },
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        # Redirect to frontend with token
        response = RedirectResponse(
            url=f"{settings.auth.frontend_url}?auth_success=true",
            status_code=302
        )

        # Set token in HTTP-only cookie
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=settings.app_env == "prod",
            samesite="lax",
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

        # Clear session state
        request.session.pop("oauth_state", None)

        logger.info(f"User logged in via GitHub: {user.email}")
        return response

    except Exception as e:
        logger.error(f"GitHub OAuth callback error: {e}")
        return RedirectResponse(
            url=f"{settings.auth.frontend_url}?auth_error={str(e)}",
            status_code=302
        )


@router.post("/logout")
async def logout(response: Response):
    """Logout user by clearing the access token cookie."""
    response.delete_cookie(key="access_token")
    return {"message": "Logged out successfully"}


@router.get("/providers")
async def list_providers():
    """List available OAuth providers."""
    settings = get_settings()

    providers = []

    if settings.auth.google_client_id:
        providers.append({
            "name": "google",
            "display_name": "Google",
            "login_url": "/api/v1/auth/google/login"
        })

    if settings.auth.github_client_id:
        providers.append({
            "name": "github",
            "display_name": "GitHub",
            "login_url": "/api/v1/auth/github/login"
        })

    return {
        "enabled": settings.auth.enabled,
        "providers": providers
    }
