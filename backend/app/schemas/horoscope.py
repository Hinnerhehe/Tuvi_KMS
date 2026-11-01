"""Schema Pydantic cho API Horoscope."""
from __future__ import annotations

from pydantic import BaseModel, Field


class HoroscopeRequest(BaseModel):
    ho_ten: str = Field("", description="Họ và tên người xem")
    ngay: int = Field(..., ge=1, le=31, description="Ngày sinh (dương hoặc âm)")
    thang: int = Field(..., ge=1, le=12, description="Tháng sinh (dương hoặc âm)")
    nam: int = Field(..., ge=1900, le=2100, description="Năm sinh")
    chi_gio: int = Field(..., ge=1, le=12, description="Chi giờ (1: Tý, 2: Sửu, ..., 12: Hợi)")
    gioi_tinh: int = Field(1, description="Giới tính: 1 cho Nam, 2 hoặc -1 cho Nữ")
    duong_lich: bool = Field(True, description="True nếu ngày sinh là Dương lịch, False nếu Âm lịch")
    target_year: int | None = Field(None, description="Năm xem chiêm nghiệm")
    provider: str = Field("auto", description="Chế độ luận giải: 'auto' (AI) hoặc 'mock' (Dữ kiện thuần)")
    top_k_per_topic: int = Field(2, ge=1, le=10, description="Số đoạn trích dẫn mỗi chủ đề")

