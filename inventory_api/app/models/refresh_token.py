from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from app.core.database import Base


class RefreshToken(Base):
  __tablename__ = "refresh_tokens"

  id = Column(Integer, primary_key=True, index=True)
  user_id = Column(
      Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
  )
  token_hash = Column(String(255), unique=True, index=True, nullable=False)
  expires_at = Column(DateTime, nullable=False)
  is_revoked = Column(Boolean, default=False, nullable=False)
  created_at = Column(DateTime, default=datetime.utcnow, nullable=False)