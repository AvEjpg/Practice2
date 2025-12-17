from sqlalchemy import Column, Integer, String, Text, Date, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "climate_service"}

    user_id = Column(Integer, primary_key=True, index=True)
    fio = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    login = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    user_type = Column(String(50), nullable=False)

    requests = relationship("Request", back_populates="client", foreign_keys="Request.client_id")
    comments = relationship("Comment", back_populates="master")

class Request(Base):
    __tablename__ = "requests"
    __table_args__ = {"schema": "climate_service"}

    request_id = Column(Integer, primary_key=True, index=True)
    start_date = Column(Date, nullable=False)
    climate_tech_type = Column(String(100), nullable=False)
    climate_tech_model = Column(String(255), nullable=False)
    problem_description = Column(Text, nullable=False)
    request_status = Column(String(50), nullable=False)
    completion_date = Column(Date, nullable=True)
    repair_parts = Column(Text, nullable=True)

    master_id = Column(Integer, ForeignKey("climate_service.users.user_id", ondelete="SET NULL"))
    client_id = Column(Integer, ForeignKey("climate_service.users.user_id", ondelete="CASCADE"))

    client = relationship("User", foreign_keys=[client_id], back_populates="requests")
    master = relationship("User", foreign_keys=[master_id])
    comments = relationship("Comment", back_populates="request")

class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = {"schema": "climate_service"}

    comment_id = Column(Integer, primary_key=True, index=True)
    message = Column(Text, nullable=False)

    master_id = Column(Integer, ForeignKey("climate_service.users.user_id", ondelete="CASCADE"))
    request_id = Column(Integer, ForeignKey("climate_service.requests.request_id", ondelete="CASCADE"))

    master = relationship("User", back_populates="comments")
    request = relationship("Request", back_populates="comments")
