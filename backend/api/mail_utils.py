import os
import logging
from flask import url_for
from flask_mail import Message

logger = logging.getLogger("smarthealth.mail")

def send_status_email(doctor_email, doctor_name, action):
    """
    Sends an automated email notification to the doctor on account approval or rejection.
    """
    try:
        from backend.factory import mail
        
        login_url = url_for("views.login_page", _external=True)
        
        if action == "approve":
            subject = "Smart Health Sync — Account Approved"
            body = (
                f"Dear Dr. {doctor_name},\n\n"
                "We are pleased to inform you that your doctor account at Smart Health Sync "
                "has been approved and is now active.\n\n"
                "You can now log in to the portal and start using our clinical diagnosis tools.\n\n"
                f"Log In Here: {login_url}\n\n"
                "Best regards,\n"
                "The Smart Health Sync Team"
            )
        else:
            subject = "Smart Health Sync — Account Registration Status"
            body = (
                f"Dear Dr. {doctor_name},\n\n"
                "Thank you for registering with Smart Health Sync.\n\n"
                "Unfortunately, your doctor registration request was not approved at this time.\n"
                "Reason: Your uploaded document was rejected or did not meet our verification criteria.\n\n"
                "If you believe this was in error, please log back into your account "
                "to re-submit a valid professional medical certificate or credential for verification.\n\n"
                "Best regards,\n"
                "The Smart Health Sync Team"
            )
            
        msg = Message(
            subject=subject,
            recipients=[doctor_email],
            body=body
        )
        
        mail.send(msg)
        logger.info(f"[Mail] Status email sent to {doctor_email} for action: {action}")
        
    except Exception as e:
        logger.exception(f"[Mail] Failed to send status email to {doctor_email}: {e}")
        # Re-raise so callers can optionally log/handle it
        raise
