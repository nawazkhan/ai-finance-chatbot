from openai import OpenAI
from fastapi import FastAPI, Form, Request, Depends
from decouple import config
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import desc

from models import Conversation, SessionLocal
from utils import send_whatsapp_message, logger

client = OpenAI(api_key=config('OPENAI_API_KEY'))

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
async def index():
    return {"msg": "working"}

def is_stock_request(message):
    """Check if the message is asking for stock or financial information"""
    stock_keywords = ['stock', 'share', 'financial', 'earnings', 'revenue', 'profit', 'market cap', 
                      'dividend', 'pe ratio', 'eps', 'ticker', 'nasdaq', 'nyse', 'dow', 'sp500']
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in stock_keywords)

@app.post("/message")
async def reply(request: Request, Body: str = Form(), db: Session = Depends(get_db)):
    logger.info("Webhook /message called")
    form_data = await request.form()
    logger.info(f"Form data received: {form_data}")
    whatsapp_number = form_data['From'].split('whatsapp:')[-1]
    logger.info(f"Sending the ChatGPT response to this number: {whatsapp_number}")

    # Get the last conversation for this number
    last_conversation = db.query(Conversation)\
        .filter(Conversation.sender == whatsapp_number)\
        .order_by(desc(Conversation.id))\
        .first()

    # Prepare the API call parameters
    api_params = {
        "model": config('OPENAI_MODEL'),
        "input": Body,
        "max_output_tokens": 1000,
        "temperature": 0.5,
    }

    # Add web search tool for stock/financial requests
    if is_stock_request(Body):
        api_params["tools"] = [
            {
                "type": "web_search_preview",
                "tool_choice": "web_search_preview",
                "search_context_size": "low",
                "web_search_preview": {
                    "max_results": 5,
                    "search_depth": "basic"
                }
            }
        ]

    # If there's a previous conversation, add the previous_response_id
    if last_conversation and last_conversation.response_id:
        api_params["previous_response_id"] = last_conversation.response_id
    
    response = client.responses.create(**api_params)
    
    logger.info(f"Response: {response}")
    chatgpt_response = response.output_text
    
    try:
        conversation = Conversation(
            sender=whatsapp_number,
            message=Body,
            response=chatgpt_response,
            response_id=response.id
        )
        db.add(conversation)
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to save conversation to database: {str(e)}")
    
    send_whatsapp_message(whatsapp_number, chatgpt_response)
    return {"message": chatgpt_response}
    
    
    
    


