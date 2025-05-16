import logging

from twilio.rest import Client
from decouple import config

account_sid = config('TWILIO_ACCOUNT_SID')
auth_token = config('TWILIO_AUTH_TOKEN')
client = Client(account_sid, auth_token)
twilio_number = config('TWILIO_NUMBER')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_whatsapp_message(to_number, message):
    try:
        message = client.messages.create(
            body=message,
            from_=f"whatsapp:{twilio_number}",
            to=f"whatsapp:{to_number}"
        )
        logger.info(f"WhatsApp message sent successfully: {message.body} to {to_number}")
    except Exception as e:
        logger.error(f"Failed to send WhatsApp message: {str(e)}")

logger = logging.getLogger(__name__)
