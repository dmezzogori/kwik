import smtplib
import ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path

import kwik
from jinja2 import Template


def send_email(*, email_to: str, subject: str = "", body: str = "") -> None:
    try:
        context = ssl.create_default_context()
        email_from = kwik.settings.EMAILS_FROM_EMAIL
        with smtplib.SMTP_SSL(kwik.settings.SMTP_HOST, kwik.settings.SMTP_PORT, context=context) as server:
            msg = MIMEMultipart("alternative")
            msg["From"] = formataddr((str(Header(email_from, "utf-8")), kwik.settings.SMTP_USER))
            msg["To"] = email_to
            msg["Subject"] = subject
            html = body

            # Record the MIME types of text/html.
            msg.attach(MIMEText(html, "html"))
            server.login(kwik.settings.SMTP_USER, kwik.settings.SMTP_PASSWORD)
            server.sendmail(kwik.settings.SMTP_USER, email_to, msg.as_string())
    except Exception as e:
        kwik.logger.debug("failed to send an email")
        kwik.logger.debug(e)


def send_reset_password_email(email_to: str, email: str, token: str) -> None:
    project_name = kwik.settings.PROJECT_NAME
    subject = f"{project_name} - Password recovery"
    server_host = kwik.settings.SERVER_HOST
    template_file = Path(kwik.settings.EMAIL_TEMPLATES_DIR) / "reset_password.html"
    template_str = "Use the following link to reset your password <a href='{{link}}'>{{link}}</a>"
    if Path(template_file).is_file():
        with open(template_file) as f:
            template_str = f.read()
    server_host = kwik.settings.SERVER_HOST
    link = f"{server_host}/reset-password?token={token}"
    body_template = Template(template_str)
    body = body_template.render(
        {
            "project_name": kwik.settings.PROJECT_NAME,
            "username": email,
            "email": email_to,
            "valid_hours": kwik.settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS,
            "link": link,
        }
    )
    send_email(email_to=email_to, subject=subject, body=body)


def send_new_account_email(email_to: str, username: str, password: str) -> None:
    project_name = kwik.settings.PROJECT_NAME
    subject = f"{project_name} - New account for user {username}"
    template_file = Path(kwik.settings.EMAIL_TEMPLATES_DIR) / "new_account.html"
    template_str = "A new account has been created<br/>You can login at <a href='{{link}}'>{{link}}</a>,<br /> password <b>{{password}}</b>"
    if Path(template_file).is_file():
        with open(template_file) as f:
            template_str = f.read()
    link = kwik.settings.SERVER_HOST
    body_template = Template(template_str)
    body = body_template.render(
        {
            "project_name": kwik.settings.PROJECT_NAME,
            "username": username,
            "password": password,
            "email": email_to,
            "link": link,
        }
    )
    send_email(email_to=email_to, subject=subject, body=body)


def send_test_email(email_to: str) -> None:
    project_name = kwik.settings.PROJECT_NAME
    subject = f"{project_name} - Test email"
    send_email(email_to=email_to, subject=subject, body="Only a test!!! CAN BE DELETED")
