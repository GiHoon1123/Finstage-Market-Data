# app/repositories/symbol_repository.py

from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.models.symbol import Symbol

def get_symbols_with_pagination(session: Session, page: int, size: int):
    total = session.scalar(select(func.count()).select_from(Symbol))

    items = session.scalars(
        select(Symbol)
        .order_by(Symbol.symbol)
        .offset((page - 1) * size)
        .limit(size)
    ).all()

    return total, items
