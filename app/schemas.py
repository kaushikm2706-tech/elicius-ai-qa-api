from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str
    provider: str          # "gemini" | "groq" | "cache"
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
