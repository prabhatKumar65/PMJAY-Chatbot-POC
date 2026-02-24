from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import ollama
from pymongo import MongoClient
import uuid

app = FastAPI(title="PMJAY AI-Mitra Chatbot")
templates = Jinja2Templates(directory="templates")

# MongoDB Connection
client = MongoClient("mongodb://localhost:27017/")
db = client["pmjay_chatbot"]

# Session storage
sessions = {}

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


# ═══════════════════════════════════════════════════════════════
# DATABASE QUERIES
# ═══════════════════════════════════════════════════════════════
def check_aadhaar_eligibility(aadhaar: str):
    """Check PMJAY eligibility by Aadhaar"""
    return db.beneficiaries.find_one({"aadhaar": aadhaar})

def check_ration_card(ration_number: str):
    """Check PMJAY eligibility by Ration Card"""
    return db.ration_cards.find_one({"ration_card": ration_number})

def search_hospitals(state: str = None, pincode: str = None):
    """Search empanelled hospitals"""
    query = {"empanelled": True}
    if state:
        query["state"] = {"$regex": state, "$options": "i"}
    if pincode:
        query["pincode"] = pincode
    return list(db.hospitals.find(query, {"_id": 0}).limit(5))

def save_conversation(session_id: str, user_msg: str, bot_reply: str, intent: str):
    """Save conversation to MongoDB"""
    db.conversations.insert_one({
        "session_id": session_id,
        "user_message": user_msg,
        "bot_reply": bot_reply,
        "intent": intent,
        "timestamp": datetime.utcnow()
    })


# ═══════════════════════════════════════════════════════════════
# INTENT DETECTION (Keyword-based - FAST & RELIABLE)
# ═══════════════════════════════════════════════════════════════
def detect_intent(message: str) -> str:
    """Detect user intent from message"""
    msg = message.lower()
    
    # Eligibility
    if any(word in msg for word in ["eligible", "eligibility", "qualify", "check"]):
        return "eligibility"
    
    # Aadhaar
    if any(word in msg for word in ["aadhaar", "aadhar", "adhar"]):
        return "aadhaar"
    
    # Ration card
    if any(word in msg for word in ["ration", "card"]):
        return "ration"
    
    # Hospital search
    if any(word in msg for word in ["hospital", "doctor", "find", "search", "near"]):
        return "hospital"
    
    # Scheme info
    if any(word in msg for word in ["pmjay", "scheme", "coverage", "benefit", "what is", "tell me", "explain"]):
        return "scheme_info"
    
    # Card/Application
    if any(word in msg for word in ["apply", "application", "get card", "download"]):
        return "card_info"
    
    return "general"


# ═══════════════════════════════════════════════════════════════
# AI CHAT (English-only, Clean responses)
# ═══════════════════════════════════════════════════════════════
def get_ai_response(user_message: str, context: str = "") -> str:
    """Get English response from Ollama"""
    try:
        print(f"[AI] Processing: {user_message[:50]}...")
        
        system_prompt = """You are PMJAY AI-Mitra, a helpful assistant for Pradhan Mantri Jan Arogya Yojana (Ayushman Bharat - PM-JAY).

Key Information about PM-JAY:
- Provides health coverage of ₹5 lakh per family per year
- Covers 1,949 medical procedures including hospitalization costs
- Cashless and paperless at empanelled hospitals
- Covers pre and post-hospitalization expenses
- No cap on family size or age
- Covers secondary and tertiary care hospitalization
- Free for eligible beneficiaries

Your role:
- Answer questions about PM-JAY scheme clearly and accurately
- Help users understand eligibility, benefits, and processes
- Guide users to check eligibility or find hospitals
- Keep responses concise (2-3 sentences), friendly, and professional
- Use simple English that's easy to understand
- If you don't know something specific, guide them to helpline: 14555

CRITICAL: Respond ONLY in English. Keep answers short and direct."""

        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        if context:
            messages.append({"role": "system", "content": f"Context: {context}"})
        
        messages.append({"role": "user", "content": user_message})
        
        response = ollama.chat(
            model="mistral",  # Using mistral - better English than phi3
            messages=messages,
            options={
                "num_predict": 150,
                "temperature": 0.7,
                "top_p": 0.9
            }
        )
        
        reply = response["message"]["content"].strip()
        print(f"[AI] Generated response: {len(reply)} chars")
        return reply
        
    except Exception as e:
        print(f"[ERROR] Ollama failed: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# HOME ROUTE
# ═══════════════════════════════════════════════════════════════
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ═══════════════════════════════════════════════════════════════
# MAIN CHAT ENDPOINT
# ═══════════════════════════════════════════════════════════════
@app.post("/chat")
async def chat(req: ChatRequest):
    # Generate session ID
    session_id = req.session_id or str(uuid.uuid4())
    user_msg = req.message.strip()
    
    # Initialize session
    if session_id not in sessions:
        sessions[session_id] = {
            "step": None,
            "data": {}
        }
    
    session = sessions[session_id]
    current_step = session.get("step")
    
    print(f"\n[USER] {user_msg}")
    print(f"[SESSION] Step: {current_step}")
    
    # ═══════════════════════════════════════════════════════════
    # FLOW HANDLERS
    # ═══════════════════════════════════════════════════════════
    
    # AADHAAR INPUT
    if current_step == "aadhaar_input":
        aadhaar = user_msg.strip()
        
        if len(aadhaar) != 12 or not aadhaar.isdigit():
            return {
                "response": "Please enter a valid 12-digit Aadhaar number.",
                "session_id": session_id
            }
        
        record = check_aadhaar_eligibility(aadhaar)
        session["step"] = None
        
        if record:
            if record["eligible"]:
                reply = f"✅ Great news! {record['name']} is eligible for PM-JAY.\n\n📋 Details:\n• Card Number: {record.get('pmjay_card', 'N/A')}\n• State: {record['state']}\n• District: {record['district']}\n• Family Members: {len(record.get('family_members', []))}\n\nYou can get your Ayushman Card from the nearest Common Service Centre (CSC) or visit beneficiary.nha.gov.in"
            else:
                reply = f"❌ {record['name']} is currently not eligible for PM-JAY based on our database.\n\nFor more information or to appeal, please contact the PM-JAY helpline: 14555"
        else:
            reply = f"⚠️ Aadhaar number {aadhaar} not found in our database.\n\nPlease verify:\n• The number is correct\n• You're in the eligible categories (SECC 2011 database)\n\nYou can also check at: beneficiary.nha.gov.in"
        
        save_conversation(session_id, user_msg, reply, "aadhaar_check")
        return {"response": reply, "session_id": session_id}
    
    # RATION CARD INPUT
    if current_step == "ration_input":
        record = check_ration_card(user_msg)
        session["step"] = None
        
        if record:
            if record["eligible"]:
                members = ", ".join(record['members'])
                reply = f"✅ This ration card is eligible for PM-JAY!\n\n👨‍👩‍👧‍👦 Eligible Family Members:\n{members}\n\n📍 Location: {record['district']}, {record['state']}\n\nYou can apply for Ayushman Cards at your nearest Common Service Centre."
            else:
                reply = f"❌ This ration card (Card Type: {record.get('card_type', 'N/A')}) is currently not eligible for PM-JAY.\n\nEligibility is primarily based on SECC 2011 data and BPL status. For queries, contact helpline: 14555"
        else:
            reply = "⚠️ Ration card not found in our database.\n\nPlease check:\n• The card number is correct\n• Your card is registered with the state government\n\nAlternatively, you can check eligibility using your Aadhaar number."
        
        save_conversation(session_id, user_msg, reply, "ration_check")
        return {"response": reply, "session_id": session_id}
    
    # HOSPITAL STATE INPUT
    if current_step == "hospital_state":
        session["data"]["state"] = user_msg
        session["step"] = "hospital_pincode"
        reply = f"Got it! Searching for empanelled hospitals in {user_msg}.\n\nPlease provide your 6-digit pincode."
        return {"response": reply, "session_id": session_id}
    
    # HOSPITAL PINCODE INPUT
    if current_step == "hospital_pincode":
        pincode = user_msg.strip()
        
        if len(pincode) != 6 or not pincode.isdigit():
            return {
                "response": "Please enter a valid 6-digit pincode.",
                "session_id": session_id
            }
        
        state = session["data"].get("state")
        hospitals = search_hospitals(state=state, pincode=pincode)
        session["step"] = None
        session["data"] = {}
        
        if hospitals:
            reply = f"🏥 Found {len(hospitals)} empanelled hospital(s) in {state}:\n\n"
            for h in hospitals:
                specialties = ", ".join(h.get('specialties', [])[:3])
                reply += f"• {h['name']}\n  📍 {h['district']}, {h['state']}\n  🏥 Type: {h['type']}\n  💊 Specialties: {specialties}\n  📞 Contact: {h.get('contact', 'N/A')}\n\n"
            reply += "All listed hospitals accept PM-JAY Ayushman Cards for cashless treatment!"
        else:
            reply = f"❌ No empanelled hospitals found for pincode {pincode} in {state}.\n\nTry:\n• Different pincode\n• Nearby districts\n• Visit pmjay.gov.in to search for hospitals"
        
        save_conversation(session_id, user_msg, reply, "hospital_search")
        return {"response": reply, "session_id": session_id}
    
    # ═══════════════════════════════════════════════════════════
    # INTENT ROUTING
    # ═══════════════════════════════════════════════════════════
    intent = detect_intent(user_msg)
    print(f"[INTENT] {intent}")
    
    # ELIGIBILITY START
    if intent == "eligibility":
        session["step"] = "ask_method"
        reply = "I can help you check PM-JAY eligibility! 😊\n\nPlease choose one:\n• Type 'Aadhaar' to check with Aadhaar number\n• Type 'Ration' to check with Ration Card number\n\nWhich one do you have?"
        return {"response": reply, "session_id": session_id}
    
    # AADHAAR FLOW
    if intent == "aadhaar" or (session.get("step") == "ask_method" and "aad" in user_msg.lower()):
        session["step"] = "aadhaar_input"
        reply = "Please enter your 12-digit Aadhaar number.\n\n📝 For demo, try: 123456789012"
        return {"response": reply, "session_id": session_id}
    
    # RATION FLOW
    if intent == "ration" or (session.get("step") == "ask_method" and "rat" in user_msg.lower()):
        session["step"] = "ration_input"
        reply = "Please enter your Ration Card number.\n\n📝 For demo, try: RC1001"
        return {"response": reply, "session_id": session_id}
    
    # HOSPITAL SEARCH
    if intent == "hospital":
        session["step"] = "hospital_state"
        reply = "I'll help you find empanelled hospitals! 🏥\n\nFirst, please tell me your state name.\n\n📝 Examples: Bihar, Delhi, Uttar Pradesh, Tamil Nadu"
        return {"response": reply, "session_id": session_id}
    
    # SCHEME INFO
    if intent == "scheme_info":
        reply = "📋 About Pradhan Mantri Jan Arogya Yojana (PM-JAY):\n\n• World's largest health insurance scheme\n• ₹5 lakh coverage per family per year\n• Covers 1,949 medical procedures\n• Cashless treatment at 27,000+ empanelled hospitals\n• No premium payments required\n• Covers pre and post-hospitalization expenses\n\nWould you like to check if you're eligible?"
        save_conversation(session_id, user_msg, reply, "scheme_info")
        return {"response": reply, "session_id": session_id}
    
    # CARD INFO
    if intent == "card_info":
        reply = "💳 About Ayushman Card:\n\nTo get your PM-JAY Ayushman Card:\n1. Check eligibility first (using Aadhaar/Ration Card)\n2. Visit nearest Common Service Centre (CSC)\n3. Provide your Aadhaar and photo\n4. Get your e-card instantly (free of cost)\n\nYou can also apply online at: beneficiary.nha.gov.in\n\nWant me to check if you're eligible?"
        save_conversation(session_id, user_msg, reply, "card_info")
        return {"response": reply, "session_id": session_id}
    
    # ═══════════════════════════════════════════════════════════
    # AI CHAT (for general queries)
    # ═══════════════════════════════════════════════════════════
    print(f"[MODE] AI Chat")
    
    ai_response = get_ai_response(user_msg)
    
    if ai_response:
        reply = ai_response
    else:
        # Fallback if AI fails
        reply = "Hello! I'm PMJAY AI-Mitra. 😊\n\nI can help you with:\n• Check PM-JAY eligibility\n• Find empanelled hospitals\n• Learn about scheme benefits\n• Apply for Ayushman Card\n\nWhat would you like to know?"
    
    save_conversation(session_id, user_msg, reply, "general")
    return {"response": reply, "session_id": session_id}


# ═══════════════════════════════════════════════════════════════
# UTILITY ENDPOINTS
# ═══════════════════════════════════════════════════════════════
@app.get("/stats")
def get_stats():
    """Database statistics"""
    return {
        "beneficiaries": db.beneficiaries.count_documents({}),
        "ration_cards": db.ration_cards.count_documents({}),
        "hospitals": db.hospitals.count_documents({}),
        "conversations": db.conversations.count_documents({}),
        "active_sessions": len(sessions)
    }

@app.get("/test-ai")
def test_ai():
    """Test if Ollama is working"""
    test_response = get_ai_response("Hello, how are you?")
    
    return {
        "status": "✅ Working" if test_response else "❌ Failed",
        "test_query": "Hello, how are you?",
        "ai_response": test_response,
        "model": "mistral"
    }

@app.get("/health")
def health():
    return {
        "status": "running",
        "database": "connected",
        "language": "English only",
        "model": "mistral"
    }