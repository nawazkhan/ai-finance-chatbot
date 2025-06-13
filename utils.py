import logging
import textwrap

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
        # Split message into chunks of 1500 characters
        chunks = textwrap.wrap(message, width=1500, break_long_words=False)
        
        for i, chunk in enumerate(chunks, 1):
            # Add part number if message is split into multiple parts
            if len(chunks) > 1:
                chunk = f"[Part {i}/{len(chunks)}]\n{chunk}"
            
            message = client.messages.create(
                body=chunk,
                from_=f"whatsapp:{twilio_number}",
                to=f"whatsapp:{to_number}"
            )
            logger.info(f"WhatsApp message part {i}/{len(chunks)} sent successfully to {to_number}")
            
    except Exception as e:
        logger.error(f"Failed to send WhatsApp message: {str(e)}")

logger = logging.getLogger(__name__)
