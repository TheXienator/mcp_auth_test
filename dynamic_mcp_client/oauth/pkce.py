"""PKCE (Proof Key for Code Exchange) generator for OAuth 2.1."""

import base64
import hashlib
import secrets


def generate_pkce_pair() -> tuple[str, str]:
    """
    Generate PKCE code_verifier and code_challenge pair.

    Returns:
        Tuple of (code_verifier, code_challenge) using S256 method.
    """
    # Generate cryptographically secure random code verifier (43-128 characters)
    code_verifier = base64.urlsafe_b64encode(
        secrets.token_bytes(32)
    ).rstrip(b'=').decode('utf-8')

    # Create SHA256 hash of code verifier for code challenge
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).rstrip(b'=').decode('utf-8')

    return code_verifier, code_challenge
