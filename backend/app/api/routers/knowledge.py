"""Knowledge base endpoints (Section 12) - entities, relationships, graph."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.knowledge import KnowledgeEntity, KnowledgeRelationship
from app.models.organization import User

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

ENTITY_TYPES = ("topic", "person", "organization", "event", "claim", "source",
               "video", "trend", "competitor", "concept")


class EntityIn(BaseModel):
    entity_type: str
    name: str
    data: dict = {}


class RelationshipIn(BaseModel):
    source_entity_id: int
    target_entity_id: int
    relation_type: str
    data: dict = {}


@router.post("/entities", status_code=201)
def create_entity(data: EntityIn, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    if data.entity_type not in ENTITY_TYPES:
        raise HTTPException(400, f"entity_type must be one of {ENTITY_TYPES}")
    slug = data.name.strip().lower().replace(" ", "-")[:200]
    existing = db.query(KnowledgeEntity).filter_by(org_id=user.org_id, slug=slug,
                                                   entity_type=data.entity_type).first()
    if existing:
        return {"id": existing.id, "name": existing.name, "slug": existing.slug,
                "entity_type": existing.entity_type, "data": existing.data,
                "note": "existing entity returned"}
    e = KnowledgeEntity(org_id=user.org_id, entity_type=data.entity_type,
                        name=data.name, slug=slug, data=data.data)
    db.add(e)
    db.commit()
    return {"id": e.id, "name": e.name, "slug": e.slug, "entity_type": e.entity_type, "data": e.data}


@router.get("/entities")
def list_entities(q: str = "", entity_type: str = "", limit: int = 100,
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(KnowledgeEntity).filter(KnowledgeEntity.org_id == user.org_id)
    if entity_type:
        query = query.filter(KnowledgeEntity.entity_type == entity_type)
    if q:
        query = query.filter(KnowledgeEntity.name.ilike(f"%{q}%"))
    rows = query.order_by(KnowledgeEntity.id.desc()).limit(min(limit, 500)).all()
    return [{"id": e.id, "entity_type": e.entity_type, "name": e.name,
             "slug": e.slug, "data": e.data} for e in rows]


@router.post("/relationships", status_code=201)
def create_relationship(data: RelationshipIn,
                        user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    for eid in (data.source_entity_id, data.target_entity_id):
        if not db.query(KnowledgeEntity).filter_by(id=eid, org_id=user.org_id).first():
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Entity {eid} not found")
    r = KnowledgeRelationship(org_id=user.org_id, source_entity_id=data.source_entity_id,
                              target_entity_id=data.target_entity_id,
                              relation_type=data.relation_type, data=data.data)
    db.add(r)
    db.commit()
    return {"id": r.id, "source": data.source_entity_id, "target": data.target_entity_id,
            "relation_type": data.relation_type}


@router.get("/graph")
def graph(entity_id: int | None = None, depth: int = 1,
          user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Nodes + edges around an entity (bounded depth) for visualization."""
    ent_rows = db.query(KnowledgeEntity).filter(KnowledgeEntity.org_id == user.org_id)
    rel_rows = db.query(KnowledgeRelationship).filter(KnowledgeRelationship.org_id == user.org_id)
    if entity_id:
        ent_rows = ent_rows.filter(KnowledgeEntity.id == entity_id)
    ents = ent_rows.all()
    ids = {e.id for e in ents}
    rels = [r for r in rel_rows.all() if r.source_entity_id in ids or r.target_entity_id in ids]
    # include direct neighbors
    neighbor_ids = set()
    for r in rels:
        neighbor_ids.update({r.source_entity_id, r.target_entity_id} - ids)
    if neighbor_ids:
        extra = db.query(KnowledgeEntity).filter(KnowledgeEntity.id.in_(neighbor_ids)).all()
        ents.extend(extra)
    return {
        "nodes": [{"id": e.id, "name": e.name, "entity_type": e.entity_type} for e in ents],
        "edges": [{"id": r.id, "source": r.source_entity_id, "target": r.target_entity_id,
                   "relation": r.relation_type} for r in rels],
    }
