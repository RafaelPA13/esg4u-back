import resend
import os

resend.api_key = os.getenv("RESEND_API_KEY")

class EmailService:

    def send_email(self, to: str, subject: str, html: str):
        resend.Emails.send({
            "from": os.getenv("EMAIL_FROM"),
            "to": to,
            "subject": subject,
            "html": html
        })

email_service = EmailService()