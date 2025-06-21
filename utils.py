import logging
import re
import html
import time
from twilio.rest import Client
from decouple import config

# Twilio credentials from .env
account_sid = config('TWILIO_ACCOUNT_SID')
auth_token = config('TWILIO_AUTH_TOKEN')
twilio_number = config('TWILIO_NUMBER')

client = Client(account_sid, auth_token)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def format_message(text):
    """
    Cleans and formats text to look good on WhatsApp.
    """
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text)

    # Use literal emoji instead of \U unicode escape
    text = re.sub(r'(?m)^## (.+)$', r'*📌 \1*', text)
    text = re.sub(r'(?m)\*\*(.+?)\*\*', r'*\1*', text)
    text = re.sub(r'(?m)^[-*] ', '• ', text)
    text = re.sub(r'(?m)^(\d+\.)', r'\n\1', text)
    text = re.sub(r'\. ', '.\n\n', text)
    text = re.sub(r'\? ', '?\n\n', text)
    text = re.sub(r'! ', '!\n\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def split_into_chunks(message, max_length=1500):
    paragraphs = message.split('\n\n')
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para += '\n\n'
        if len(current_chunk) + len(para) <= max_length:
            current_chunk += para
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            if len(para) > max_length:
                sentences = re.split(r'(?<=[.!?]) +', para)
                temp = ""
                for sentence in sentences:
                    if len(temp) + len(sentence) + 1 <= max_length:
                        temp += sentence + " "
                    else:
                        chunks.append(temp.strip())
                        temp = sentence + " "
                if temp:
                    chunks.append(temp.strip())
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

def send_whatsapp_message(to_number, message):
    try:
        formatted = format_message(message)
        chunks = split_into_chunks(formatted)

        for i, chunk in enumerate(chunks, 1):
            if len(chunks) > 1:
                # Use a literal emoji instead of \U0001F4F1 to avoid escape issues
                chunk = f"📱 *Part {i}/{len(chunks)}*\n\n{chunk}"

            response = client.messages.create(
                body=chunk,
                from_=f"whatsapp:{twilio_number}",
                to=f"whatsapp:{to_number}"
            )
            logger.info(f"WhatsApp message part {i}/{len(chunks)} sent to {to_number}")
            time.sleep(1.5)

    except Exception as e:
        logger.error(f"Failed to send WhatsApp message: {str(e)}")

def send_media_message(to_number, media_url, caption=""):
    try:
        client.messages.create(
            from_=f"whatsapp:{twilio_number}",
            to=f"whatsapp:{to_number}",
            body=caption,
            media_url=[media_url]
        )
        logger.info(f"Media message sent to {to_number}")
    except Exception as e:
        logger.error(f"Failed to send media message: {str(e)}")

def extract_and_send_media(response_text, to_number):
    media_links = re.findall(r'(https?://\S+\.(?:jpg|png|jpeg|gif|mp4|webp))', response_text)
    for media_url in media_links:
        caption = "Media attached:"
        send_media_message(to_number, media_url, caption)
        time.sleep(1)