from openai import OpenAI
from fastapi import FastAPI, Form, Request, Depends
from decouple import config
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

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

@app.post("/message")
async def reply(request: Request, Body: str = Form(), db: Session = Depends(get_db)):
    print("Webhook /message called")
    form_data = await request.form()
    print(f"Form data received: {form_data}")
    whatsapp_number = form_data['From'].split('whatsapp:')[-1]
    print(f"Sending the ChatGPT response to this number: {whatsapp_number}")

    messages = [{"role": "user", "content": Body}]
    messages.append({"role": "system", "content": "You're a helpful investor, a serial founder and you've sold many startups. You understand nothing but business. You are here to give advice on business."})
    response = client.chat.completions.create(
      model=config('OPENAI_MODEL'),
      messages=messages,
      max_tokens=100,
      temperature=0.5,
      n=1,
      stop=None,
    )

    chatgpt_response = response.choices[0].message.content
    print(f"ChatGPT response: {chatgpt_response}")
    
    try:
        conversation = Conversation(
            sender=whatsapp_number,
            message=Body,
            response=chatgpt_response
        )
        db.add(conversation)
        db.commit()
    except SQLAlchemyError as e:
      db.rollback()
      logger.error(f"Failed to save conversation to database: {str(e)}")
    
    send_whatsapp_message(whatsapp_number, chatgpt_response)
    return {"message": chatgpt_response}
    
    
    
    


