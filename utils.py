import logging
import textwrap
import re

from twilio.rest import Client
from decouple import config

account_sid = config('TWILIO_ACCOUNT_SID')
auth_token = config('TWILIO_AUTH_TOKEN')
client = Client(account_sid, auth_token)
twilio_number = config('TWILIO_NUMBER')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def format_message(text):
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Add line breaks after periods followed by space
    text = re.sub(r'\. ', '.\n\n', text)
    
    # Add line breaks after question marks
    text = re.sub(r'\? ', '?\n\n', text)
    
    # Add line breaks after exclamation marks
    text = re.sub(r'! ', '!\n\n', text)
    
    # Add line breaks after colons
    text = re.sub(r': ', ':\n', text)
    
    # Add line breaks after bullet points
    text = re.sub(r'\* ', '\n• ', text)
    
    # Add line breaks after numbered points
    text = re.sub(r'(\d+\.)', r'\n\1', text)
    
    # Remove any triple or more newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove any leading/trailing whitespace
    text = text.strip()
    
    return text

def send_whatsapp_message(to_number, message):
    try:
        # Format the message first
        formatted_message = format_message(message)
        
        # Split message into chunks of 1500 characters, preserving line breaks
        chunks = []
        current_chunk = ""
        
        for line in formatted_message.split('\n'):
            if len(current_chunk) + len(line) + 1 <= 1500:
                current_chunk += line + '\n'
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = line + '\n'
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # Send each chunk
        for i, chunk in enumerate(chunks, 1):
            # Add part number if message is split into multiple parts
            if len(chunks) > 1:
                chunk = f"📱 Part {i}/{len(chunks)}\n\n{chunk}"
            
            message = client.messages.create(
                body=chunk,
                from_=f"whatsapp:{twilio_number}",
                to=f"whatsapp:{to_number}"
            )
            logger.info(f"WhatsApp message part {i}/{len(chunks)} sent successfully to {to_number}")
            
    except Exception as e:
        logger.error(f"Failed to send WhatsApp message: {str(e)}")

logger = logging.getLogger(__name__)
