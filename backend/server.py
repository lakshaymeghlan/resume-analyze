# server.py
from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import json
from PyPDF2 import PdfReader
import io
import collections.abc

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL')
if not mongo_url:
    raise RuntimeError("MONGO_URL is not set in your environment (.env)")
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'test_database')]

# Create the main app without a prefix
app = FastAPI()
api_router = APIRouter(prefix="/api")

# DeepSeek client (async)
try:
    from tools.deepseek_client import DeepSeekClient as LlmChat
    # minimal UserMessage class (compatible shape)
    class UserMessage:
        def __init__(self, text: str, system_message: str = ""):
            self.text = text
            self.system_message = system_message
except Exception as e:
    raise RuntimeError("deepseek_client not found — create backend/tools/deepseek_client.py and set DEEPSEEK_API_KEY in .env") from e

# Models
class AnalyzeRequest(BaseModel):
    resume_text: str
    job_description: str

class SkillMatch(BaseModel):
    matched_skills: List[str]
    missing_skills: List[str]
    additional_skills: List[str]

class AnalysisResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    match_score: int
    skill_match: SkillMatch
    suggestions: List[str]
    rewritten_resume: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AnalysisResponse(BaseModel):
    id: str
    match_score: int
    matched_skills: List[str]
    missing_skills: List[str]
    additional_skills: List[str]
    suggestions: List[str]
    rewritten_resume: str
    timestamp: str

# Helper to normalize responses
async def normalize_llm_output(raw) -> str:
    if isinstance(raw, str):
        return raw
    if isinstance(raw, (bytes, bytearray)):
        return raw.decode('utf-8', errors='ignore')
    if isinstance(raw, collections.abc.Mapping):
        for key in ("content", "text", "message", "output", "response"):
            if key in raw and isinstance(raw[key], str):
                return raw[key]
        try:
            return json.dumps(raw)
        except Exception:
            return str(raw)
    for attr in ("content", "text", "message", "data"):
        if hasattr(raw, attr):
            val = getattr(raw, attr)
            if isinstance(val, (str, bytes, bytearray)):
                return val.decode('utf-8') if isinstance(val, (bytes, bytearray)) else val
    return str(raw)


@api_router.get("/")
async def root():
    return {"message": "Smart AI Resume & Job Matcher API (DeepSeek)"}


@api_router.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    try:
        content = await file.read()
        pdf_reader = PdfReader(io.BytesIO(content))
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")
        return {"text": text.strip()}
    except Exception as e:
        logging.error(f"PDF extraction error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")


@api_router.post("/analyze", response_model=AnalysisResponse)
async def analyze_resume(request: AnalyzeRequest):
    # Use DEEPSEEK API key from env; DeepSeekClient raises if not set
    try:
        chat = LlmChat()  # uses DEEPSEEK_API_KEY env
    except Exception as e:
        logging.exception("Failed to initialize DeepSeek client")
        raise HTTPException(status_code=500, detail="LLM client not configured")

    try:
        # 1) Skill analysis
        skill_prompt = f"""Analyze this resume against the job description:

RESUME:
{request.resume_text}

JOB DESCRIPTION:
{request.job_description}

Provide a JSON response with:
{{
  "matched_skills": [list of skills present in both],
  "missing_skills": [skills in job description but not in resume],
  "additional_skills": [skills in resume but not required in job],
  "match_score": integer from 0-100 based on skill overlap and relevance
}}

Only return valid JSON, nothing else."""
        skill_message = UserMessage(text=skill_prompt)
        skill_raw = await chat.send_message(skill_message)
        skill_text = await normalize_llm_output(skill_raw)
        try:
            skill_data = json.loads(skill_text)
        except Exception as e:
            logging.error("Failed to parse skill_data. Raw: %s", skill_text)
            raise HTTPException(status_code=500, detail=f"LLM returned invalid JSON for skills: {str(e)}")

        # 2) Suggestions
        suggestion_prompt = f"""Based on this analysis:
- Match Score: {skill_data.get('match_score', 0)}%
- Matched Skills: {', '.join(skill_data.get('matched_skills', [])[:10])}
- Missing Skills: {', '.join(skill_data.get('missing_skills', [])[:10])}

Provide 5-7 specific, actionable suggestions to improve the resume for this job. Return as JSON array:
{{"suggestions": ["suggestion 1", "suggestion 2", ...]}}

Only return valid JSON."""
        suggestion_message = UserMessage(text=suggestion_prompt)
        suggestion_raw = await chat.send_message(suggestion_message)
        suggestion_text = await normalize_llm_output(suggestion_raw)
        try:
            suggestion_data = json.loads(suggestion_text)
        except Exception as e:
            logging.error("Failed to parse suggestion_data. Raw: %s", suggestion_text)
            raise HTTPException(status_code=500, detail=f"LLM returned invalid JSON for suggestions: {str(e)}")

        # 3) Rewrite resume (plain text)
        rewrite_prompt = f"""Original Resume:
{request.resume_text}

Job Description:
{request.job_description}

Missing Key Skills: {', '.join(skill_data.get('missing_skills', [])[:10])}

Rewrite the resume to better match this job description. Focus on:
1. Incorporating missing keywords naturally
2. Highlighting relevant experience
3. Using strong action verbs
4. Maintaining truthfulness (don't fabricate experience)
5. ATS-friendly formatting

Provide only the rewritten resume text, no explanations."""
        rewrite_message = UserMessage(text=rewrite_prompt)
        rewrite_raw = await chat.send_message(rewrite_message)
        rewritten_resume = await normalize_llm_output(rewrite_raw)

        # Build result
        analysis = AnalysisResult(
            match_score=int(skill_data.get('match_score', 0)),
            skill_match=SkillMatch(
                matched_skills=skill_data.get('matched_skills', []),
                missing_skills=skill_data.get('missing_skills', []),
                additional_skills=skill_data.get('additional_skills', [])
            ),
            suggestions=suggestion_data.get('suggestions', []),
            rewritten_resume=rewritten_resume
        )

        # DB store
        doc = {
            "id": analysis.id,
            "match_score": analysis.match_score,
            "matched_skills": skill_data.get('matched_skills', []),
            "missing_skills": skill_data.get('missing_skills', []),
            "additional_skills": skill_data.get('additional_skills', []),
            "suggestions": analysis.suggestions,
            "rewritten_resume": analysis.rewritten_resume,
            "timestamp": analysis.timestamp.isoformat(),
            "resume_text": request.resume_text[:500],
            "job_description": request.job_description[:500],
        }
        await db.analyses.insert_one(doc)

        return AnalysisResponse(
            id=analysis.id,
            match_score=analysis.match_score,
            matched_skills=skill_data.get('matched_skills', []),
            missing_skills=skill_data.get('missing_skills', []),
            additional_skills=skill_data.get('additional_skills', []),
            suggestions=analysis.suggestions,
            rewritten_resume=analysis.rewritten_resume,
            timestamp=analysis.timestamp.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Analysis error")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@api_router.get("/history", response_model=List[dict])
async def get_history():
    try:
        history = await db.analyses.find(
            {},
            {"_id": 0, "id": 1, "match_score": 1, "timestamp": 1, "resume_text": 1, "job_description": 1}
        ).sort("timestamp", -1).limit(20).to_list(20)
        return history
    except Exception as e:
        logging.error(f"History error: {e}")
        return []


app.include_router(api_router)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
