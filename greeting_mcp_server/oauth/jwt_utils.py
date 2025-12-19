"""JWT utilities for RSA key management and token creation."""

import base64
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Tuple

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend


# Default key paths
DEFAULT_PRIVATE_KEY_PATH = Path("keys/private_key.pem")
DEFAULT_PUBLIC_KEY_PATH = Path("keys/public_key.pem")
DEFAULT_KID = "default-key-2025"


def generate_rsa_keypair() -> Tuple[str, str]:
    """Generate RSA key pair.

    Returns:
        Tuple of (private_key_pem, public_key_pem) as strings
    """
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    # Serialize private key to PEM format
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')

    # Get public key
    public_key = private_key.public_key()

    # Serialize public key to PEM format
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')

    return private_pem, public_pem


def save_keypair(private_key_pem: str, public_key_pem: str,
                 private_path: Path = DEFAULT_PRIVATE_KEY_PATH,
                 public_path: Path = DEFAULT_PUBLIC_KEY_PATH) -> None:
    """Save RSA keypair to files.

    Args:
        private_key_pem: Private key in PEM format
        public_key_pem: Public key in PEM format
        private_path: Path to save private key
        public_path: Path to save public key
    """
    # Ensure directory exists
    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)

    # Write keys to files
    private_path.write_text(private_key_pem)
    public_path.write_text(public_key_pem)

    # Set restrictive permissions on private key
    private_path.chmod(0o600)


def load_keypair(private_path: Path = DEFAULT_PRIVATE_KEY_PATH,
                 public_path: Path = DEFAULT_PUBLIC_KEY_PATH) -> Tuple[str, str]:
    """Load RSA keypair from files.

    Args:
        private_path: Path to private key file
        public_path: Path to public key file

    Returns:
        Tuple of (private_key_pem, public_key_pem) as strings

    Raises:
        FileNotFoundError: If key files don't exist
    """
    if not private_path.exists() or not public_path.exists():
        raise FileNotFoundError("Key files not found")

    private_pem = private_path.read_text()
    public_pem = public_path.read_text()

    return private_pem, public_pem


def get_or_create_keypair(private_path: Path = DEFAULT_PRIVATE_KEY_PATH,
                          public_path: Path = DEFAULT_PUBLIC_KEY_PATH) -> Tuple[str, str]:
    """Get existing keypair or create new one.

    Args:
        private_path: Path to private key file
        public_path: Path to public key file

    Returns:
        Tuple of (private_key_pem, public_key_pem) as strings
    """
    try:
        return load_keypair(private_path, public_path)
    except FileNotFoundError:
        print("Generating new RSA keypair...")
        private_pem, public_pem = generate_rsa_keypair()
        save_keypair(private_pem, public_pem, private_path, public_path)
        print(f"Keys saved to {private_path} and {public_path}")
        return private_pem, public_pem


def public_key_to_jwk(public_key_pem: str, kid: str = DEFAULT_KID) -> dict:
    """Convert public key PEM to JWK format.

    Args:
        public_key_pem: Public key in PEM format
        kid: Key ID

    Returns:
        JWK as dictionary
    """
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    # Load public key
    public_key = load_pem_public_key(public_key_pem.encode(), backend=default_backend())

    # Get public numbers
    numbers = public_key.public_numbers()

    # Convert to base64url encoding
    def int_to_base64url(num: int) -> str:
        # Convert int to bytes
        num_bytes = num.to_bytes((num.bit_length() + 7) // 8, byteorder='big')
        # Base64url encode
        return base64.urlsafe_b64encode(num_bytes).rstrip(b'=').decode('utf-8')

    # Create JWK
    jwk = {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": kid,
        "n": int_to_base64url(numbers.n),
        "e": int_to_base64url(numbers.e)
    }

    return jwk


def create_access_token(
    client_id: str,
    issuer: str,
    audience: str,
    private_key_pem: str,
    kid: str = DEFAULT_KID,
    expires_delta: timedelta = timedelta(hours=1),
    scope: str = "mcp:tools"
) -> str:
    """Create RS256 signed JWT access token.

    Args:
        client_id: Client ID (will be 'sub' claim)
        issuer: Token issuer URL
        audience: Token audience
        private_key_pem: Private key in PEM format
        kid: Key ID for JWT header
        expires_delta: Token expiration time
        scope: OAuth scope

    Returns:
        Encoded JWT token
    """
    now = datetime.now(timezone.utc)

    # Create claims
    claims = {
        "iss": issuer,
        "sub": client_id,
        "aud": audience,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "scope": scope
    }

    # Create JWT with RS256
    token = jwt.encode(
        claims,
        private_key_pem,
        algorithm="RS256",
        headers={"kid": kid}
    )

    return token


def verify_token(token: str, public_key_pem: str, issuer: str, audience: str) -> dict:
    """Verify and decode JWT token.

    Args:
        token: JWT token to verify
        public_key_pem: Public key in PEM format
        issuer: Expected issuer
        audience: Expected audience

    Returns:
        Decoded token claims

    Raises:
        jwt.InvalidTokenError: If token is invalid
    """
    claims = jwt.decode(
        token,
        public_key_pem,
        algorithms=["RS256"],
        issuer=issuer,
        audience=audience
    )

    return claims
