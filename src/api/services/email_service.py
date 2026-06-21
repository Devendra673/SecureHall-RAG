"""
Mock Email Service
Phase 10 — Email Verification & Password Reset
"""

import logging

logger = logging.getLogger("securehall-rag.email")


def send_verification_email(email: str, token: str) -> None:
    """Mock sending a verification email."""
    # In a real app, you would use smtplib, SendGrid, AWS SES, etc.
    # and link to your frontend: f"https://yourdomain.com/verify-email?token={token}"
    verification_link = f"http://localhost:3000/verify-email?token={token}"
    
    msg = f"""
    ========================================================
    [MOCK EMAIL] To: {email}
    Subject: Verify your SecureHall-RAG Account
    ========================================================
    Welcome to SecureHall-RAG!
    
    Please verify your email address by clicking the link below:
    {verification_link}
    
    If you did not request this, please ignore this email.
    ========================================================
    """
    logger.info(msg)


def send_password_reset_email(email: str, token: str) -> None:
    """Mock sending a password reset email."""
    reset_link = f"http://localhost:3000/reset-password?token={token}"
    
    msg = f"""
    ========================================================
    [MOCK EMAIL] To: {email}
    Subject: Password Reset Request
    ========================================================
    We received a request to reset your password.
    
    Click the link below to set a new password:
    {reset_link}
    
    This link will expire in 1 hour.
    If you did not request this, please ignore this email.
    ========================================================
    """
    logger.info(msg)
