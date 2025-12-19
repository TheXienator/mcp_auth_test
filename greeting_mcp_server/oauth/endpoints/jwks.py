"""JWKS (JSON Web Key Set) endpoint."""

from fastapi import APIRouter
from oauth.jwt_utils import get_or_create_keypair, public_key_to_jwk, DEFAULT_KID

router = APIRouter()


@router.get("/.well-known/jwks.json")
async def jwks_endpoint():
    """JSON Web Key Set endpoint.

    Returns the public key(s) used to verify JWT signatures.
    FastMCP's JWTVerifier will fetch this to validate tokens.

    Returns:
        JWKS with list of public keys
    """
    # Get or create keypair
    _, public_key_pem = get_or_create_keypair()

    # Convert to JWK format
    jwk = public_key_to_jwk(public_key_pem, kid=DEFAULT_KID)

    # Return JWKS (list of keys)
    return {
        "keys": [jwk]
    }
