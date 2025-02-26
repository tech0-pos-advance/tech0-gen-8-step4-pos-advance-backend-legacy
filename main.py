from fastapi import FastAPI, Depends, HTTPException, Query #追記
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, DateTime, Integer, create_engine, SMALLINT, SmallInteger
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text  # 追記
from datetime import datetime
from dotenv import load_dotenv
import os
import logging
from typing import Optional, Union # 追記2
from pydantic import BaseModel, Field, root_validator # 追記2
from typing import List
import json  # 追記2
from sqlalchemy import and_

# ログの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 環境変数をログに出力（セキュリティ上、パスワードなどを除外）
logger.info("=== 環境変数の確認 ===")
for key, value in os.environ.items():
    if "PASSWORD" not in key and "SECRET" not in key:  # セキュリティ対策
        logger.info(f"{key}: {value}")
logger.info("======================")

# 環境変数の読み込み
load_dotenv()  # .env をデフォルトとして読み込む
load_dotenv(dotenv_path=".env.local", override=True)  # .env.local があれば上書き

# 環境変数の読み込み
DB_HOST = os.getenv("DB_HOST") 
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_SSL_CA = os.getenv("DB_SSL_CA")

# MySQL接続URLを構築
# DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}?ssl_disabled=true"
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}?ssl_ca={DB_SSL_CA}"


if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_NAME, DB_SSL_CA]):
    raise ValueError("Missing database configuration environment variables")

# SQLAlchemyの設定（データベース接続）
try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)  # 接続前にチェックを実施
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except SQLAlchemyError as e:
    logger.error(f"Database connection error: {e}")
    raise RuntimeError(f"Database connection error: {e}")

# ORMの基盤となるクラスを作成
Base = declarative_base()

# CORSの許可設定
# ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,https://pos-advance-frontend-legacy-bdaxawereeeng2bm.canadacentral-01.azurewebsites.net")
# ALLOWED_ORIGINS_LIST = ALLOWED_ORIGINS.split(",")

# FastAPIアプリの作成
app = FastAPI()

# CORSミドルウェアの追加
app.add_middleware(
    CORSMiddleware,
    # allow_origins=ALLOWED_ORIGINS_LIST,  # 環境変数から取得
        allow_origins=[
        "http://localhost:3000",  # 開発時のローカルURL
        "http://127.0.0.1:3000", # 開発時のローカルURL
        "https://pos-advance-frontend-legacy-bdaxawereeeng2bm.canadacentral-01.azurewebsites.net" #Azureでデプロイされたユーザー用のフロントエンドのURL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ユーザーモデルの定義
class User(Base):
    __tablename__ = "m_company_users"
    user_id = Column(String(50), primary_key=True, nullable=False)
    user_name = Column(String(100), nullable=False)
    password = Column(String(255), nullable=False)  # プレーンテキストのパスワードはNG
    email = Column(String(100), nullable=False, unique=True)
    role = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

# 設備モデルの定義
class Facility(Base):
    __tablename__ = "m_company_facilities"
    facility_id = Column(String(50), primary_key=True, nullable=False)
    facility_name = Column(String(100), nullable=False)
    facility_type = Column(String(50), nullable=False)
    capacity = Column(SMALLINT, nullable=False)

from sqlalchemy import Column, String, Integer, DateTime, SmallInteger

class Reservation(Base):
    __tablename__ = "t_company_facility_reservations"

    reservation_id = Column(Integer, primary_key=True, autoincrement=True)  # 自動インクリメントを追加
    user_id = Column(String(50), nullable=False)
    facility_id = Column(String(50), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    attendee_count = Column(SmallInteger, nullable=False)
    created_date = Column(DateTime, nullable=False)



# Pydanticモデル（APIレスポンス用）
# ユーザー情報のレスポンスモデル
class UserResponse(BaseModel):
    user_id: str
    user_name: str
    email: str
    role: str
    created_at: datetime
    updated_at: datetime

# 設備情報のレスポンスモデル
class FacilityResponse(BaseModel):
    facility_id: str
    facility_name: str
    facility_type: str
    capacity: int

# Pydanticモデル（フロントエンドからのリクエストデータ）
class ReservationRequest(BaseModel):
    facility_id: str
    start_time: datetime
    end_time: datetime
    user_id: str
    attendee_count: int

# 予約レスポンス用のPydanticモデル
class ReservationResponse(BaseModel):
    reservation_id: int
    facility_name: str
    reservation_date: str
    time_slot: str
    status: str
    message: str

# データベースセッションを取得する関数
def get_db():
    """データベースセッションを取得し、処理後にクローズする"""
    db = None
    try:
        db = SessionLocal()
        yield db
    except SQLAlchemyError as e:
        logger.error(f"Database session error: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        if db:
            db.close()

# ルートエンドポイント
@app.get("/")
def read_root():
    """アプリのルートエンドポイント"""
    print("DB_SSL_CA",DB_SSL_CA)
    print("DATABASE_URL",DATABASE_URL)

    return {"message": "M不動産の社内システムです。"}

# ユーザー情報を取得するエンドポイント
@app.get("/users/{user_id}", response_model=UserResponse)
def read_user(user_id: str, db: Session = Depends(get_db)):
    """指定されたユーザーIDの情報を取得"""
    user: Optional[User] = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user  # Pydanticが自動的にJSONへ変換


# 設備情報を取得するエンドポイント
@app.get("/facilities/{facility_id}", response_model=FacilityResponse)
def read_facility(facility_id: str , db: Session = Depends(get_db)):
    """指定された設備IDの情報を取得"""
    facility: Optional[Facility] = db.query(Facility).filter(Facility.facility_id == facility_id).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")  # 修正
    return facility  # Pydanticが自動的にJSONへ変換

# すべての設備情報を取得するエンドポイント
@app.get("/facilities")
def read_facilities(
    facility_type: Optional[str] = Query(None, description="検索する施設のタイプ（完全一致）"),
    location: Optional[str] = Query(None, description="検索する施設の場所（部分一致）"),
    capacity: Optional[int] = Query(None, description="この人数以上のキャパシティ"),
    limit: Optional[int] = Query(10, description="取得する件数（デフォルト10件）"),
    offset: Optional[int] = Query(0, description="スキップする件数（デフォルト0件）"),
    db: Session = Depends(get_db)
):
    """施設名・施設タイプ・場所・キャパシティで検索する（ページネーションあり）"""
    sql_where = "WHERE 1=1"
    params = {}

    if facility_type:
        sql_where += " AND facility_type = :facility_type"
        params["facility_type"] = facility_type

    if location:
        sql_where += " AND MATCH(location) AGAINST(:location IN BOOLEAN MODE)"
        params["location"] = f"{location}*"  # Indexを利用

    if capacity:
        sql_where += " AND capacity >= :capacity"
        params["capacity"] = capacity

    # **1. 件数を取得**
    count_sql = f"SELECT COUNT(*) FROM m_company_facilities {sql_where}"
    total_count = db.execute(text(count_sql), params).scalar()

    # **2. データ取得**
    sql = f"SELECT * FROM m_company_facilities {sql_where} LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = offset

    logger.info(f"Executing SQL: {sql}")
    logger.info(f"With parameters: {params}")

    result = db.execute(text(sql), params).fetchall()

    # **3. 結果がない場合**
    if not result:
        return {
            "status": "success",
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "message": "No facilities found matching the search criteria.",
            "data": []
        }

    facilities = [
        {
            "facility_id": row[0],
            "facility_name": row[1],
            "facility_type": row[2],
            "capacity": row[3],
            "location": row[4],
            "equipment": json.loads(row[5]) if isinstance(row[5], str) else row[5],
            "management_type": row[6],
            "external_id": row[7],
            "created_at": row[8]
        }
        for row in result
    ]

    return {
        "status": "success",
        "total_count": total_count, 
        "limit": limit,
        "offset": offset,
        "data": facilities
    }


# 予約を処理するエンドポイント
@app.post("/reservations", response_model=ReservationResponse)
def create_reservation(request: ReservationRequest, db: Session = Depends(get_db)):
    # 1. 予約時間が過去ではないか確認
    if request.start_time < datetime.now():
        raise HTTPException(status_code=400, detail="予約時間は過去に設定できません。")
    
    # 2. 同じ施設で重複予約がないか確認
    existing_reservation = db.query(Reservation).filter(
        and_(
            Reservation.facility_id == request.facility_id,
            Reservation.start_time < request.end_time,
            Reservation.end_time > request.start_time
        )
    ).first()
    
    if existing_reservation:
        raise HTTPException(status_code=400, detail="この施設はすでに予約されています")
    
    # 3. 施設名を取得
    facility = db.query(Facility).filter(Facility.facility_id == request.facility_id).first()
    if not facility:
        raise HTTPException(status_code=404, detail="施設が見つかりません")

    # 4. 予約の作成
    new_reservation = Reservation(
        user_id=request.user_id,
        facility_id=request.facility_id,
        start_time=request.start_time,
        end_time=request.end_time,
        attendee_count=request.attendee_count,
        created_date=datetime.now()
    )
    
    db.add(new_reservation)
    db.commit()
    db.refresh(new_reservation)
    
    # 5. レスポンスデータを作成
    reservation_date = request.start_time.date().strftime('%Y-%m-%d')
    time_slot = f"{request.start_time.strftime('%H:%M')}-{request.end_time.strftime('%H:%M')}"
    
    return ReservationResponse(
        reservation_id=new_reservation.reservation_id,
        facility_name=facility.facility_name,
        reservation_date=reservation_date,
        time_slot=time_slot,
        status="success",
        message="予約が完了しました"
    )

# 予約を削除するエンドポイント
@app.delete("/reservations/{reservation_id}", response_model=ReservationResponse)
def delete_reservation(reservation_id: int, db: Session = Depends(get_db)):
    """
    指定されたreservation_idに関連する予約を削除する
    フロントエンドからreservation_idが渡される
    """
    # 予約IDに関連するレコードをデータベースから検索
    reservation = db.query(Reservation).filter(Reservation.reservation_id == reservation_id).first()
    
    # 予約が見つからない場合は404エラーを返す
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    # 施設名を取得するためにfacility_idを使ってFacilityテーブルを検索
    facility = db.query(Facility).filter(Facility.facility_id == reservation.facility_id).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")  # 施設が見つからない場合のエラーハンドリング
    
    # 予約を削除する
    db.delete(reservation)
    db.commit()  # 変更をデータベースに反映
    
    # レスポンス用のデータを準備
    return ReservationResponse(
        reservation_id=reservation.reservation_id,
        facility_name=facility.facility_name,  # Facilityテーブルから施設名を取得
        reservation_date=reservation.start_time.date().strftime('%Y-%m-%d'),
        time_slot=f"{reservation.start_time.strftime('%H:%M')}-{reservation.end_time.strftime('%H:%M')}",
        status="success",
        message="予約を削除しました"
    )