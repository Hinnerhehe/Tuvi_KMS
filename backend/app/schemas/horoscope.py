"""Pydantic schemas cho endpoint /api/v1/horoscope/read.

Tách biệt với các schema KMS RAG hiện có (search.py, chat.py).
"""
from __future__ import annotations

from typing import Optional, Literal
from pydantic import BaseModel, Field


class HoroscopeRequest(BaseModel):
    """Yêu cầu xem tử vi — người dùng nhập thông tin ngày sinh."""

    ho_ten: Optional[str] = Field(default="", description="Họ tên người xem (tuỳ chọn)")
    ngay: int = Field(..., ge=1, le=31, description="Ngày sinh (1-31)")
    thang: int = Field(..., ge=1, le=12, description="Tháng sinh (1-12)")
    nam: int = Field(..., ge=1900, le=2100, description="Năm sinh (1900-2100)")
    chi_gio: int = Field(
        ...,
        ge=1,
        le=12,
        description=(
            "Chi giờ sinh: 1=Tý(23-1h), 2=Sửu(1-3h), 3=Dần(3-5h), 4=Mão(5-7h), "
            "5=Thìn(7-9h), 6=Tỵ(9-11h), 7=Ngọ(11-13h), 8=Mùi(13-15h), "
            "9=Thân(15-17h), 10=Dậu(17-19h), 11=Tuất(19-21h), 12=Hợi(21-23h)"
        ),
    )
    gioi_tinh: Literal[1, 2] = Field(
        default=1, description="1 = Nam (♂), 2 = Nữ (♀)"
    )
    duong_lich: bool = Field(default=True, description="True = dương lịch, False = âm lịch")
    top_k_per_topic: int = Field(default=2, ge=1, le=10, description="Số chunk RAG mỗi chủ đề")
    provider: Literal["auto", "mock", "gemini"] = Field(
        default="auto",
        description="'auto'=tự động chọn, 'mock'=offline, 'gemini'=bắt buộc dùng Gemini API",
    )
    target_year: Optional[int] = Field(
        default=None, ge=1900, le=2200, description="Năm cần xem vận (mặc định: năm hiện tại)"
    )


class HoroscopeResponse(BaseModel):
    """Kết quả xem tử vi trả về từ API."""

    status: str
    ho_ten: str
    thong_tin_co_ban: dict
    reading: dict
    meta: dict
    la_so: dict = Field(default_factory=dict)
    citations: list[dict] = Field(default_factory=list)
    star_analysis: list[dict] = Field(default_factory=list)
    annual: dict = Field(default_factory=dict)
    palaces: list[dict] = Field(default_factory=list)

