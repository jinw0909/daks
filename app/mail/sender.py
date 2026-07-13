import smtplib
from email.message import EmailMessage

from app.core.config import settings

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape


TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"

template_environment = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


def render_mail_template(
        template_name: str,
        context: dict,
) -> str:
    template = template_environment.get_template(template_name)
    return template.render(**context)


def send_html_email(
        *,
        to_email: str,
        subject: str,
        html: str,
) -> None:
    message = EmailMessage()

    message["Subject"] = subject
    message["From"] = (
        f"{settings.mail_from_name} "
        f"<{settings.mail_from_email}>"
    )
    message["To"] = to_email

    message.set_content(
        "HTML 이메일을 확인할 수 있는 환경에서 열어주세요."
    )
    message.add_alternative(
        html,
        subtype="html",
    )

    with smtplib.SMTP(
            settings.mail_host,
            settings.mail_port,
    ) as smtp:
        smtp.starttls()
        smtp.login(
            settings.mail_username,
            settings.mail_password,
        )
        smtp.send_message(message)