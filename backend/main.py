from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
from pydantic import BaseModel
from typing import List, Optional
from telemetry_extractor import extract_telemetry_from_tlog

app = FastAPI()

# Allow frontend access (CORS settings)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global telemetry context (used by chatbot)
telemetry_context = {}

# Telemetry data structure
class TelemetrySummary(BaseModel):
    takeoffTime: Optional[str]
    maxAltitude: Optional[float]
    flightModes: Optional[List[str]]
    gpsLossTimes: Optional[List[str]]
    batteryLow: Optional[bool]
    flightDurationSec: Optional[int]

# Accept manual telemetry input (optional API)
#@app.post("/api/telemetry_summary")
#async def receive_telemetry(summary: TelemetrySummary):
#    global telemetry_context
 #   telemetry_context = summary.dict()
  #  return {"status": "Telemetry summary received", "data": telemetry_context}

# Upload and extract telemetry from .tlog
@app.post("/api/extract_from_tlog")
async def extract_and_store(file: UploadFile = File(...)):
    global telemetry_context
    try:
        file_bytes = await file.read()
        telemetry_summary = extract_telemetry_from_tlog(file_bytes)
        telemetry_context = telemetry_summary
        print("Extracted Telemetry:", telemetry_summary)  # ✅ Debug print
        return {"status": "Extracted", "data": telemetry_summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Chat endpoint
@app.post("/api/chat")
async def chat(request: Request):
    global telemetry_context
    data = await request.json()
    question = data.get("question", "What is your name?")

    # ✅ Debug print to confirm LLM context
    print("🧠 Telemetry context in chat:", telemetry_context)
    print("💬 User question:", question)

    # Construct prompt
    prompt = f"""
    You are a technical assistant. Answer user questions directly and clearly based only on the telemetry summary provided below.

    Telemetry Summary:
    - Takeoff Time: {telemetry_context.get('takeoffTime', 'Unknown')}
    - Max Altitude: {telemetry_context.get('maxAltitude', 'Unknown')} meters
    - Flight Modes: {', '.join(telemetry_context.get('flightModes', []) or [])}
    - GPS Loss Times: {', '.join(telemetry_context.get('gpsLossTimes', []) or [])}
    - Battery Low: {'Yes' if telemetry_context.get('batteryLow') else 'No'}
    - Duration: {telemetry_context.get('flightDurationSec', 'Unknown')} seconds

    User Question: "{question}"

    Answer as clearly and directly as possible. Do not introduce yourself or make up any information.
    """


    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama2",
                "prompt": prompt,
                "stream": False
            }
        )
        result = response.json()
        return {"response": result.get("response", "")}
    except Exception as e:
        return {"response": f"Error: {str(e)}"}
