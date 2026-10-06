"""Request/response models for SafeSaathi API."""
from pydantic import BaseModel, Field


class AnalyzeTextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8000, examples=[
        "Your bank KYC has expired. Verify now at http://sbi-kyc-verify.xyz or your account will be blocked."
    ])
    lang: str = Field(default="en", pattern="^(en|hi|mr)$")


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=600)
    lang: str = Field(default="en", pattern="^(en|hi|mr)$")


class GuardianRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1500)
    to: str = Field(default="", max_length=20)
    risk_label: str = Field(default="scam", pattern="^(safe|suspicious|scam)$")
