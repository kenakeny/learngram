from fastapi import APIRouter
from learngram_shared.db.pool import get_pool
from ..models import GraphNode, GraphEdge, GraphResponse

router = APIRouter()


@router.get("/graph", response_model=GraphResponse)
async def get_graph() -> GraphResponse:
    pool = get_pool()
    with pool.connection() as conn:
        node_rows = conn.execute(
            "SELECT id, name, slug, topic, depth_level FROM nodes ORDER BY depth_level, name"
        ).fetchall()

        edge_rows = conn.execute(
            "SELECT from_node_id, to_node_id, relationship_type, weight FROM edges"
        ).fetchall()

    nodes = [
        GraphNode(id=str(r[0]), name=r[1], slug=r[2], topic=r[3], depth_level=r[4])
        for r in node_rows
    ]
    edges = [
        GraphEdge(
            from_id=str(r[0]),
            to_id=str(r[1]),
            relationship_type=r[2],
            weight=float(r[3]),
        )
        for r in edge_rows
    ]

    return GraphResponse(nodes=nodes, edges=edges)
