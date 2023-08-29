import smtplib
import ssl
from email.message import EmailMessage


def create_alert(
    sender: str, receiver: str, website: str, table: str
) -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = receiver
    message["Subject"] = "[Alerte codes promo] Nouveaux codes"

    body = f"""\
    <html>
        <body>
            <p>De nouveaux codes promo ont été ajoutés pour le site {website}.
            </p>
            {table}
        </body>
    </html>
    """

    message.set_content(body, subtype="html")

    return message


def send_mail(
    sender: str, password: str, receiver: str, message: EmailMessage
) -> None:
    context = ssl.create_default_context()

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
        smtp.login(sender, password)
        smtp.sendmail(sender, receiver, message.as_string())
