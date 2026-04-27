import os
import csv
import uuid
import logging
import requests
from typing import Optional, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("endpoints")
API_KEY = os.getenv("keys")

if not API_URL or not API_KEY:
    raise ValueError("Azure credentials missing")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Chatbot")

app = FastAPI(title="Customer Support Chatbot", version="6.0")


class ChatRequest(BaseModel):
    user_id: str
    query: str


class ChatResponse(BaseModel):
    reply: str
    intent: str
    ticket_id: Optional[str] = None
    status: str



class KB:
    def __init__(self, file):
        self.data = self.load(file)

    def load(self, file) -> Dict[str, str]:
        try:
            with open(file, encoding="utf-8") as f:
                return {
                    row["Intent"].strip(): row["Response"].strip()
                    for row in csv.DictReader(f)
                }
        except:
            logger.warning("KB not found")
            return {}

    async def create_ticket(self):
        return f"SUP-{uuid.uuid4().hex[:6].upper()}"

class AIEngine:
    def __init__(self, kb: KB):
        self.kb = kb

    def call_azure(self, system, user):
        headers = {
            "Content-Type": "application/json",
            "api-key": API_KEY
        }

        payload = {
            "model": "gpt-4o-mini",
            "input": f"{system}\nUser: {user}",
            "temperature": 0.3
        }

        res = requests.post(API_URL, headers=headers, json=payload)

        print("STATUS:", res.status_code)
        print("RESPONSE:", res.text)

        if res.status_code != 200:
            return "AI service unavailable"

        data = res.json()

        try:
            return data["output"][0]["content"][0]["text"]
        except:
            return "Response parsing error"

    def detect_intent(self, text):
        prompt = "Classify into: Order_Status, Support_Ticket, General_Query. Return only one."
        return self.call_azure(prompt, text).strip()

    def generate_reply(self, text):
        prompt = "You are a helpful customer support assistant."
        return self.call_azure(prompt, text)

    async def process(self, user, text):
        intent = self.detect_intent(text)

        try:
            reply = self.generate_reply(text)
        except:
            reply = self.kb.data.get(intent, "No info available")

        ticket = None

        if intent == "Support_Ticket":
            ticket = await self.kb.create_ticket()
            reply += f"\nTicket ID: {ticket}"

        return reply, intent, ticket


kb = KB("knowledge_base.csv")
ai = AIEngine(kb)


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        reply, intent, ticket = await ai.process(req.user_id, req.query)

        return ChatResponse(
            reply=reply,
            intent=intent,
            ticket_id=ticket,
            status="success"
        )

    except Exception as e:
        logger.error(str(e))
        raise HTTPException(status_code=500, detail="Server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=8000)