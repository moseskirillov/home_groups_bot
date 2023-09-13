import os
from datetime import datetime, time
from typing import List

from sqlalchemy import String, Boolean, DateTime, Integer, Time, ForeignKey, MetaData, BigInteger
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, relationship

TG_DEFAULT = os.getenv('TG_DEFAULT')


class Base(AsyncAttrs, DeclarativeBase):
    metadata = MetaData(schema=os.getenv('SCHEMA'))


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(length=255), nullable=True)
    last_name: Mapped[str] = mapped_column(String(length=255), nullable=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    telegram_login: Mapped[str] = mapped_column(String(length=255), nullable=True)
    last_login: Mapped[datetime] = mapped_column(DateTime, default=datetime.now())
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)


class GroupLeader(Base):
    __tablename__ = 'group_leaders'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(length=255), nullable=False)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    telegram_login: Mapped[str] = mapped_column(String(length=255), default=TG_DEFAULT)
    groups: Mapped[List['Group']] = relationship()
    region_leader_id: Mapped[int] = mapped_column(ForeignKey('regional_leaders.id'), nullable=True)
    region_leader: Mapped['RegionLeader'] = relationship(back_populates='leaders', lazy='joined')


class Group(Base):
    __tablename__ = 'groups'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    metro: Mapped[str] = mapped_column(String(length=255), nullable=False)
    day: Mapped[str] = mapped_column(String(length=255), nullable=False)
    time: Mapped[time] = mapped_column(Time, nullable=False)
    age: Mapped[str] = mapped_column(String(length=255), nullable=False)
    type: Mapped[str] = mapped_column(String(length=255), nullable=False)
    is_open: Mapped[bool] = mapped_column(Boolean, default=False)
    leader_id: Mapped[int] = mapped_column(ForeignKey('group_leaders.id'), nullable=True)
    group_leader: Mapped['GroupLeader'] = relationship(back_populates='groups', lazy='joined')


class RegionLeader(Base):
    __tablename__ = 'regional_leaders'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(length=255), nullable=False)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    telegram_login: Mapped[str] = mapped_column(String(length=255), nullable=True)
    leaders: Mapped[List['GroupLeader']] = relationship()


class JoinRequest(Base):
    __tablename__ = 'join_requests'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.now())
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=True)
    leader_id: Mapped[int] = mapped_column(ForeignKey('group_leaders.id'), nullable=True)
