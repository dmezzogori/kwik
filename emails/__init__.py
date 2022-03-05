import re
from typing import Any, Dict, Optional
import smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from pathlib import Path

from kwik.core.config import settings
import kwik

import emails
from emails.template import JinjaTemplate
from jinja2 import Template


def send_email(
    email_to: str, subject_template: str = "", html_template: str = "", environment: Dict[str, Any] = {},
) -> None:
  try:
    context = ssl.create_default_context()
    email_from = settings.EMAILS_FROM_EMAIL
    with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context) as server:
      msg = MIMEMultipart("alternative")
      msg["From"] = formataddr((str(Header(email_from, "utf-8")), settings.SMTP_USER))
      msg["To"] = email_to
      msg["Subject"] = subject_template
      html = html_template

      # Record the MIME types of text/html.
      msg.attach(MIMEText(html, "html"))
      server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
      server.sendmail(settings.SMTP_USER, email_to, msg.as_string())
  except Exception as e:
    kwik.logger.debug("failed to send this email")
    kwik.logger.debug(e)

# NON FUNZIONA; stessi parametri di smtplib...
# peccato per il template
# risolto usando direttamente ninja2...
# finito il porting delle principali email si puliscono i pacchetti
def send_email_deprecated(
    email_to: str, subject_template: str = "", html_template: str = "", environment: Dict[str, Any] = {},
) -> None:
    assert settings.EMAILS_ENABLED, "no provided configuration for email variables"
    message = emails.Message(
        subject=JinjaTemplate(subject_template),
        html=JinjaTemplate(html_template),
        mail_from=(settings.EMAILS_FROM_NAME, settings.EMAILS_FROM_EMAIL),
    )
    smtp_options = {"host": settings.SMTP_HOST, "port": settings.SMTP_PORT}
    if settings.SMTP_TLS:
        smtp_options["tls"] = True
    if settings.SMTP_USER:
        smtp_options["user"] = settings.SMTP_USER
        print(smtp_options["user"])
    if settings.SMTP_PASSWORD:
        smtp_options["password"] = settings.SMTP_PASSWORD
        print(smtp_options["password"])
    print("ready to send")
    response = message.send(to=email_to, render=environment, smtp=smtp_options)
    print(response)
    kwik.logger.debug(f"send email result: {response}")

def send_reset_password_email(email_to: str, email: str, token: str) -> None:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Password recovery"
    server_host = settings.SERVER_HOST
    with open(Path(settings.EMAIL_TEMPLATES_DIR) / "reset_password.html") as f:
        template_str = f.read()
    server_host = settings.SERVER_HOST
    link = f"{server_host}/reset-password?token={token}"
    body_template = Template(template_str)
    body = body_template.render({
            "project_name": settings.PROJECT_NAME,
            "username": email,
            "email": email_to,
            "valid_hours": settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS,
            "link": link,
        })
    
    send_email(email_to=email_to,subject_template=subject, html_template=body)

def send_reset_password_email_deprecated(email_to: str, email: str, token: str) -> None:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Password recovery for user {email}"
    with open(Path(settings.EMAIL_TEMPLATES_DIR) / "reset_password.html") as f:
        template_str = f.read()
    server_host = settings.SERVER_HOST
    link = f"{server_host}/reset-password?token={token}"
    send_email(
        email_to=email_to,
        subject_template=subject,
        html_template=template_str,
        environment={
            "project_name": settings.PROJECT_NAME,
            "username": email,
            "email": email_to,
            "valid_hours": settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS,
            "link": link,
        },
    )

def send_new_account_email(email_to: str, username: str, password: str) -> None:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - New account for user {username}"
    with open(Path(settings.EMAIL_TEMPLATES_DIR) / "new_account.html") as f:
        template_str = f.read()
    link = settings.SERVER_HOST
    send_email(
        email_to=email_to,
        subject_template=subject,
        html_template=template_str,
        environment={
            "project_name": settings.PROJECT_NAME,
            "username": username,
            "password": password,
            "email": email_to,
            "link": link,
        },
    )

def send_test_email(email_to: str) -> None:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Test email"
    send_email(
        email_to=email_to,
        subject_template=subject,
        html_template="Only a test!!! CAN BE DELETED",
        environment={"project_name": settings.PROJECT_NAME, "email": email_to},
    )