from pydantic import BaseModel


class FeedCard(BaseModel):
    id: str
    node_id: str
    node_slug: str
    topic: str
    hook: str
    body: str
    format: str


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
