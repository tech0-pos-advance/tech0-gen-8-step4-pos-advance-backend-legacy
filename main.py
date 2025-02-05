from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, DateTime, Integer, create_engine, SMALLINT
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from dotenv import load_dotenv
import os
import logging
from typing import Optional
from pydantic import BaseModel, Field
from typing import List

# ログの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
logger.info("Connecting to database...")  # パスワードを表示しない
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
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,https://pos-advance-frontend-legacy-bdaxawereeeng2bm.canadacentral-01.azurewebsites.net/")
ALLOWED_ORIGINS_LIST = ALLOWED_ORIGINS.split(",")

# FastAPIアプリの作成
app = FastAPI()

# CORSミドルウェアの追加
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS_LIST,  # 環境変数から取得
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
@app.get("/facilities", response_model=List[FacilityResponse])
def read_facilities(db: Session = Depends(get_db)):
    facilities = db.query(Facility).all()
    return [
        {
            "facility_id": f.facility_id,
            "facility_name": f.facility_name,
            "facility_type": f.facility_type,
            "capacity": str(f.capacity),  # ✅ `int` → `str` に変換
        }
        for f in facilities
    ]