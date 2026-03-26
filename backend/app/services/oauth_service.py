"""OAuth 2.0 Authorization Code Flow service — Phase 17"""
import secrets
import string
from datetime import datetime, timezone, timedelta

import aiohttp
from sqlalchemy.orm import Session

from app.models.security import OAuthProvider, OAuthToken
from app.core.security import EncryptionHandler


class OAuth2Service:

    async def get_authorization_url(
        self,
        provider_name: str,
        db: Session,
        state: str = None,
    ) -> str:
        """Return the OAuth authorization URL for the given provider."""
        from urllib.parse import urlencode

        provider = (
            db.query(OAuthProvider)
            .filter(
                OAuthProvider.provider_name == provider_name,
                OAuthProvider.is_enabled == True,
            )
            .first()
        )
        if not provider:
            raise ValueError(f"OAuth provider '{provider_name}' not found or disabled")

        params = {
            "client_id": provider.client_id,
            "redirect_uri": provider.redirect_uri,
            "scope": " ".join(provider.scopes or []),
            "response_type": "code",
            "state": state or self._generate_state_token(),
        }
        return f"{provider.authorize_url}?{urlencode(params)}"

    async def exchange_code_for_token(
        self,
        provider_name: str,
        code: str,
        db: Session,
    ) -> dict:
        """Exchange an authorization code for an access token."""
        provider = (
            db.query(OAuthProvider)
            .filter(OAuthProvider.provider_name == provider_name)
            .first()
        )
        if not provider:
            raise ValueError(f"OAuth provider '{provider_name}' not found")

        client_secret = EncryptionHandler.decrypt(provider.client_secret)

        payload = {
            "client_id": provider.client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": provider.redirect_uri,
            "grant_type": "authorization_code",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                provider.token_url,
                json=payload,
                headers={"Accept": "application/json"},
            ) as resp:
                token_data = await resp.json(content_type=None)
                if resp.status != 200:
                    raise ValueError(f"OAuth token exchange failed: {token_data}")

        return token_data

    async def get_user_info(
        self,
        provider_name: str,
        access_token: str,
        db: Session,
    ) -> dict:
        """Fetch user profile from the OAuth provider."""
        provider = (
            db.query(OAuthProvider)
            .filter(OAuthProvider.provider_name == provider_name)
            .first()
        )
        if not provider:
            raise ValueError(f"OAuth provider '{provider_name}' not found")

        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            }
            async with session.get(provider.user_info_url, headers=headers) as resp:
                return await resp.json(content_type=None)

    async def create_or_update_user_from_oauth(
        self,
        provider_name: str,
        authorization_code: str,
        db: Session,
    ):
        """
        Exchange code, fetch user info, and upsert a User record.

        Returns the User ORM object.
        """
        from app.models.user import User

        token_data = await self.exchange_code_for_token(
            provider_name, authorization_code, db
        )
        access_token = token_data.get("access_token")
        user_info = await self.get_user_info(provider_name, access_token, db)

        provider_user_id = str(
            user_info.get("id") or user_info.get("node_id") or user_info.get("sub", "")
        )

        oauth_token = (
            db.query(OAuthToken)
            .filter(
                OAuthToken.provider == provider_name,
                OAuthToken.provider_user_id == provider_user_id,
            )
            .first()
        )

        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=token_data.get("expires_in", 3600)
        )

        if oauth_token:
            user = oauth_token.user
            oauth_token.access_token = EncryptionHandler.encrypt(access_token)
            if "refresh_token" in token_data:
                oauth_token.refresh_token = EncryptionHandler.encrypt(
                    token_data["refresh_token"]
                )
            oauth_token.expires_at = expires_at
        else:
            # Create user if needed
            email = user_info.get("email") or f"{provider_user_id}@{provider_name}.oauth"
            username = (
                user_info.get("login")
                or user_info.get("name")
                or f"{provider_name}_{provider_user_id}"
            )

            user = db.query(User).filter(User.email == email).first()
            if not user:
                # Generate a random unusable password for OAuth-only accounts
                random_pw = secrets.token_urlsafe(32)
                from app.core.security import PasswordHandler
                user = User(
                    email=email,
                    username=username,
                    hashed_password=PasswordHandler.hash_password(random_pw),
                    is_active=True,
                )
                db.add(user)
                db.flush()

            refresh_token_encrypted = (
                EncryptionHandler.encrypt(token_data["refresh_token"])
                if "refresh_token" in token_data
                else None
            )

            oauth_token = OAuthToken(
                user_id=user.id,
                provider=provider_name,
                provider_user_id=provider_user_id,
                access_token=EncryptionHandler.encrypt(access_token),
                refresh_token=refresh_token_encrypted,
                expires_at=expires_at,
            )
            db.add(oauth_token)

        db.commit()
        return user

    @staticmethod
    def _generate_state_token(length: int = 32) -> str:
        """Generate a CSRF-proof state token."""
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))
