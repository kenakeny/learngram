from typing import Literal, Optional

from pydantic import BaseModel


class FeedbackRequest(BaseModel):
    card_id: str
    rating: Literal["up", "down"]
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: str
    card_id: str
    node_id: Optional[str] = None
    rating: str


class FeedCard(BaseModel):
    id: str
    node_id: str
    node_slug: str
    topic: str
    hook: str
    body: str
    format: str
    # Persona ("account") that authored the post, when present.
    concept_name: Optional[str] = None
    post_style: Optional[str] = None
    persona_slug: Optional[str] = None
    persona_name: Optional[str] = None
    persona_color: Optional[str] = None
    persona_emoji: Optional[str] = None


class Persona(BaseModel):
    slug: str
    display_name: str
    bio: str
    post_style: str
    accent_color: str
    avatar_emoji: str
    posts: int


class FeedResponse(BaseModel):
    cards: list[FeedCard]
    seed: int


class GraphNode(BaseModel):
    id: str
    name: str
    slug: str
    topic: str
    depth_level: int


class GraphEdge(BaseModel):
    from_id: str
    to_id: str
    relationship_type: str
    weight: float


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class IngestJob(BaseModel):
    id: str
    filename: str
    status: str          # pending | running | done | error
    step: str
    message: str
    nodes_added: int
    cards_added: int
