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
    stock_keywords = [
        'stock', 'share', 'financial', 'earnings', 'revenue', 'profit', 
        'market cap', 'dividend', 'pe ratio', 'eps', 'ticker', 
        'nasdaq', 'nyse', 'dow', 'sp500'
    ]
    is_stock_request_result = any(keyword in message.lower() for keyword in stock_keywords)
    logger.info(f"is_stock_request_result: {is_stock_request_result}")
    return is_stock_request_result

@app.post("/message")
async def reply(request: Request, Body: str = Form(), db: Session = Depends(get_db)):
    logger.info("Webhook /message called")
    form_data = await request.form()
    logger.info(f"Form data received: {form_data}")

    whatsapp_number = form_data['From'].split('whatsapp:')[-1]
    logger.info(f"Sending the ChatGPT response to this number: {whatsapp_number}")

    last_conversation = db.query(Conversation)\
        .filter(Conversation.sender == whatsapp_number)\
        .order_by(desc(Conversation.id))\
        .first()

    api_params = {
        "model": config('OPENAI_MODEL'),
        "input": Body,
        "max_output_tokens": 1000,
        "temperature": 0.5,
    }

    if is_stock_request(Body):
        api_params["tools"] = [{"type": "web_search_preview"}]
    else:
        error_message = "I'm sorry, I can only help with stock requests right now."
        send_whatsapp_message(whatsapp_number, error_message)
        return {"message": error_message}

    if last_conversation and last_conversation.response_id:
        api_params["previous_response_id"] = last_conversation.response_id
    
    whatsapp_response = "Sorry, We're having trouble processing your request right now."

    try:
        response = client.responses.create(**api_params)
        logger.info(f"Response: {response}")
        chatgpt_response = response.output_text

        conversation = Conversation(
            sender=whatsapp_number,
            message=Body,
            response=chatgpt_response,
            response_id=response.id
        )
        db.add(conversation)
        db.commit()
        whatsapp_response = chatgpt_response
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to save conversation to database: {str(e)}")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create response: {str(e)}")
    
    send_whatsapp_message(whatsapp_number, whatsapp_response)
    return {"message": whatsapp_response}
