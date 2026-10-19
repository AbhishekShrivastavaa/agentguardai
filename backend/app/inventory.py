from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models import InventoryItem

router = APIRouter(prefix="/inventory", tags=["AI Inventory"])
VALID_CATEGORIES = {"agents", "mcp-servers", "tools", "investigations"}


class InventoryInput(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    data: dict = Field(default_factory=dict)


def _category(category: str) -> str:
    if category not in VALID_CATEGORIES:
        raise HTTPException(status_code=404, detail="Unknown inventory category")
    return category


def _serialize(item: InventoryItem) -> dict:
    return {**(item.data or {}), "registry_id": item.id, "category": item.category, "name": item.name}


@router.get("/{category}")
def list_inventory(category: str, current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    category = _category(category)
    items = db.query(InventoryItem).filter(InventoryItem.category == category).order_by(InventoryItem.id).all()
    return {"items": [_serialize(item) for item in items]}


@router.post("/{category}")
def create_inventory(category: str, payload: InventoryInput, current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    category = _category(category)
    existing = db.query(InventoryItem).filter_by(category=category, name=payload.name).first()
    if existing:
        return _serialize(existing)
    item = InventoryItem(category=category, name=payload.name, data=payload.data)
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(InventoryItem).filter_by(category=category, name=payload.name).first()
        if existing:
            return _serialize(existing)
        raise
    db.refresh(item)
    return _serialize(item)


@router.put("/{category}/{item_id}")
def update_inventory(category: str, item_id: int, payload: InventoryInput, current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    category = _category(category)
    item = db.query(InventoryItem).filter_by(category=category, id=item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    duplicate = db.query(InventoryItem).filter(InventoryItem.category == category, InventoryItem.name == payload.name, InventoryItem.id != item_id).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="An item with this name already exists")
    item.name = payload.name
    item.data = payload.data
    db.commit()
    db.refresh(item)
    return _serialize(item)


@router.delete("/{category}/{item_id}")
def delete_inventory(category: str, item_id: int, current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    category = _category(category)
    item = db.query(InventoryItem).filter_by(category=category, id=item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    db.delete(item)
    db.commit()
    return {"deleted": True}
