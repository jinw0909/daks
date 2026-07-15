from sqlalchemy import Column, ForeignKey, Integer, VARCHAR, Text, Float, DOUBLE, BLOB, DATETIME
from app.db.base import Base



# DB Class

    
# DB Class
class WebhookLog(Base):
    __tablename__ = 'webhook_log'

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(VARCHAR(100), nullable=True)
    payment_key = Column(VARCHAR(100), nullable=True)
    status = Column(VARCHAR(100), nullable=True)
    amount = Column(VARCHAR(100), nullable=True)
    method = Column(VARCHAR(100), nullable=True)
    payload=Column(Text, nullable=True)
    enrollmentid = Column(VARCHAR(100), nullable=True)
    receipt = Column(Text, nullable=True)
    name = Column(VARCHAR(100), nullable=True)
    ticketuser_id = Column(VARCHAR(100), nullable=True)
    approved_at=Column(VARCHAR(100), nullable=True)
    created_at=Column(VARCHAR(100), nullable=True)
    datetime=Column(DATETIME, nullable=False)
    
    
class WebhookLogHistory(Base):
    __tablename__ = "webhook_log_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    eventType = Column(VARCHAR(100))
    order_id = Column(VARCHAR(100))
    payment_key = Column(VARCHAR(200))
    status = Column(VARCHAR(50))
    amount = Column(VARCHAR(100), nullable=True)
    method = Column(VARCHAR(100), nullable=True)
    payload = Column(Text)
    enrollmentid = Column(VARCHAR(100), nullable=True)
    name = Column(VARCHAR(100), nullable=True)
    ticketuser_id = Column(VARCHAR(100), nullable=True)
    approved_at=Column(VARCHAR(100), nullable=True)
    created_at=Column(VARCHAR(100), nullable=True)
    datetime = Column(DATETIME(timezone=True))
    
    
