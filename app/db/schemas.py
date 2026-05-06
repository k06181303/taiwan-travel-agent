"""
app/db/schemas.py

景點與美食資料的 Pydantic 驗證 models。
用於 seed 資料入庫前的格式與內容驗證。
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────
# Enum 定義
# ─────────────────────────────────────────

class AttractionType(str, Enum):
    老街 = "老街"
    廟宇 = "廟宇"
    夜景 = "夜景"
    博物館 = "博物館"
    公園 = "公園"
    自然景觀 = "自然景觀"
    步道 = "步道"
    觀光工廠 = "觀光工廠"
    主題樂園 = "主題樂園"
    文創園區 = "文創園區"
    海邊 = "海邊"
    溫泉 = "溫泉"


class FoodCategory(str, Enum):
    麵食 = "麵食"
    小吃 = "小吃"
    海鮮 = "海鮮"
    甜點 = "甜點"
    咖啡 = "咖啡"
    中式 = "中式"
    日式 = "日式"
    韓式 = "韓式"
    義式 = "義式"
    美式 = "美式"
    火鍋 = "火鍋"
    燒烤 = "燒烤"
    夜市 = "夜市"
    早午餐 = "早午餐"


class TransitType(str, Enum):
    MRT = "MRT"
    TRA = "TRA"
    THSR = "THSR"
    BUS = "BUS"


class VegetarianType(str, Enum):
    none = "none"
    partial = "partial"
    lacto_ovo = "lacto_ovo"
    vegan = "vegan"


class QueueLevel(str, Enum):
    none = "none"
    short = "short"
    medium = "medium"
    long = "long"


class PopularityLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


# ─────────────────────────────────────────
# 巢狀 Model
# ─────────────────────────────────────────

class TransitInfo(BaseModel):
    """捷運 / 台鐵 / 高鐵 / 公車 交通資訊"""
    type: TransitType
    station: str
    line: str | None = None  # 只有 MRT 才有路線名稱
    walk_minutes: int = Field(ge=0, le=120)


class SeatingInfo(BaseModel):
    """用餐方式"""
    dine_in: bool
    takeout: bool
    delivery: bool


class OpenHours(BaseModel):
    """每週各天營業時間，格式 HH:MM-HH:MM 或 '全天開放' 或 '公休'"""
    monday: str
    tuesday: str
    wednesday: str
    thursday: str
    friday: str
    saturday: str
    sunday: str


# ─────────────────────────────────────────
# 主 Model：景點
# ─────────────────────────────────────────

class Attraction(BaseModel):
    """台灣景點資料 schema"""

    # 基本識別
    id: str
    name: str
    aliases: list[str]
    description: str = Field(min_length=80, max_length=200)
    keywords: list[str]

    # 地理位置
    city: str
    district: str
    address: str
    latitude: float = Field(ge=21.0, le=26.0)    # 台灣緯度範圍
    longitude: float = Field(ge=119.0, le=122.5)  # 台灣經度範圍
    nearest_transit: list[TransitInfo]
    has_parking: bool

    # 分類
    type: AttractionType
    tags: list[str]

    # 設施 / 無障礙
    indoor: bool
    wheelchair_friendly: bool
    kid_friendly: bool
    pet_friendly: bool
    wifi: bool
    power_outlet: bool
    has_restroom: bool

    # 時間
    open_hours: OpenHours
    closed_days: list[str]
    best_time: list[str]
    season: list[str]
    visit_duration_min: int = Field(ge=15, le=600)
    visit_duration_max: int = Field(ge=15, le=600)

    # 費用
    price_level: Literal[1, 2, 3]
    entrance_fee: int = Field(ge=0)
    reservation_required: bool

    # 交通說明
    transport: str

    # 評價
    rating: float = Field(ge=3.5, le=5.0)
    review_count: int = Field(ge=0)
    popularity: Literal["low", "medium", "high"]
    crowdedness: Literal["low", "medium", "high"]

    @field_validator("visit_duration_max")
    @classmethod
    def max_must_ge_min(cls, v: int, info) -> int:
        """遊玩時間上限必須 >= 下限"""
        if "visit_duration_min" in info.data and v < info.data["visit_duration_min"]:
            raise ValueError("visit_duration_max 必須 >= visit_duration_min")
        return v


# ─────────────────────────────────────────
# 主 Model：美食
# ─────────────────────────────────────────

class Food(BaseModel):
    """台灣美食資料 schema"""

    # 基本識別
    id: str
    name: str
    aliases: list[str]
    description: str = Field(min_length=80, max_length=200)
    keywords: list[str]
    must_try: list[str]
    awards: list[str]

    # 地理位置
    city: str
    district: str
    address: str
    latitude: float = Field(ge=21.0, le=26.0)
    longitude: float = Field(ge=119.0, le=122.5)
    nearest_transit: list[TransitInfo]
    has_parking: bool

    # 分類
    category: FoodCategory
    tags: list[str]

    # 飲食需求 / 設施
    vegetarian_type: VegetarianType
    halal: bool
    pet_friendly: bool
    wifi: bool
    power_outlet: bool
    private_room: bool

    # 用餐方式
    seating: SeatingInfo
    open_hours: OpenHours
    closed_days: list[str]
    season: list[str]
    avg_meal_time: int = Field(ge=5, le=300)   # 分鐘
    queue_level: QueueLevel

    # 費用
    payment_methods: list[str]
    price_range_min: int = Field(ge=0)
    price_range_max: int = Field(ge=0)
    price_level: Literal[1, 2, 3]
    min_charge: int = Field(ge=0)
    reservation_required: bool

    # 評價
    rating: float = Field(ge=3.5, le=5.0)
    review_count: int = Field(ge=0)
    popularity: Literal["low", "medium", "high"]
    crowdedness: Literal["low", "medium", "high"]

    @field_validator("price_range_max")
    @classmethod
    def max_price_ge_min(cls, v: int, info) -> int:
        """最高價必須 >= 最低價"""
        if "price_range_min" in info.data and v < info.data["price_range_min"]:
            raise ValueError("price_range_max 必須 >= price_range_min")
        return v

    @field_validator("private_room")
    @classmethod
    def private_room_requires_dine_in(cls, v: bool, info) -> bool:
        """沒有內用座位就不可能有包廂"""
        seating = info.data.get("seating")
        if v and seating and not seating.dine_in:
            raise ValueError("seating.dine_in=false 時 private_room 不可為 true")
        return v
