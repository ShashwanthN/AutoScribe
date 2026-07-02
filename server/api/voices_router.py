from __future__ import annotations

from fastapi import APIRouter, HTTPException

from server.domain.schemas import VoiceProfile, VoiceProfileDetail
from server.storage.voice_profiles import get_voice_profile, list_voice_profiles

router = APIRouter(prefix="/voices", tags=["voices"])


@router.get("", response_model=list[VoiceProfile])
async def list_voices() -> list[VoiceProfile]:
    return list_voice_profiles()


@router.get("/{voice_id}", response_model=VoiceProfileDetail)
async def get_voice(voice_id: str) -> VoiceProfileDetail:
    try:
        return get_voice_profile(voice_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Voice profile not found: {voice_id}") from None
