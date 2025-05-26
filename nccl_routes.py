from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
from pydantic import BaseModel
import logging
from ..utils.path_processor import process_path_data
from ..utils.load_processor import process_load_data

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Define data models for the request and response
class GPUNode(BaseModel):
    hostname: str
    ip_address: str
    rank: int
    gpu_id: Optional[int] = None

class NCCLOptimizationRequest(BaseModel):
    job_id: str
    world_size: int
    master_addr: str
    collection_name: str
    gpu_nodes: List[GPUNode]
    direction: str = "outbound"

class SRv6Path(BaseModel):
    source: str
    destination: str
    srv6_sid_list: List[str]
    hopcount: int
    average_load: float

class NCCLOptimizationResponse(BaseModel):
    job_id: str
    status: str
    paths: List[SRv6Path]
    message: str

@router.post("/nccl/optimize", response_model=NCCLOptimizationResponse)
async def optimize_nccl_paths(request: NCCLOptimizationRequest):
    """
    Optimize network paths for NCCL traffic between GPUs
    """
    try:
        logger.info(f"Received NCCL optimization request for job {request.job_id}")
        
        # Get database connection
        db = get_db()
        if not db.has_collection(request.collection_name):
            raise HTTPException(
                status_code=404,
                detail=f"Collection {request.collection_name} not found"
            )
        
        # Generate all-to-all paths between GPU nodes
        paths = []
        gpu_nodes = request.gpu_nodes
        
        # For each pair of GPUs, find the optimal path
        for source_node in gpu_nodes:
            for dest_node in gpu_nodes:
                # Skip self-connections
                if source_node.ip_address == dest_node.ip_address:
                    continue
                
                # Find shortest path with load as weight
                aql = f"""
                WITH igp_node
                LET path = (
                    FOR v, e IN {request.direction.upper()}
                        SHORTEST_PATH @source TO @destination
                        @graph_name
                        OPTIONS {{
                            weightAttribute: 'load',
                            defaultWeight: 1
                        }}
                        RETURN {{
                            vertex: {{
                                _id: v._id,
                                _key: v._key,
                                router_id: v.router_id,
                                prefix: v.prefix,
                                name: v.name,
                                sids: v.sids
                            }},
                            edge: e ? {{
                                _id: e._id,
                                _key: e._key,
                                _from: e._from,
                                _to: e._to,
                                latency: e.latency,
                                percent_util_out: e.percent_util_out,
                                load: e.load
                            }} : null
                        }}
                )
                
                LET avg_load = (
                    FOR p IN path
                        FILTER p.edge != null
                        COLLECT AGGREGATE 
                            avg = AVERAGE(p.edge.load)
                        RETURN avg
                )
                
                RETURN {{
                    path: path,
                    hopcount: LENGTH(path) - 1,
                    vertex_count: LENGTH(path),
                    source_info: FIRST(path).vertex,
                    destination_info: LAST(path).vertex,
                    average_load: FIRST(avg_load)
                }}
                """
                
                cursor = db.aql.execute(
                    aql,
                    bind_vars={
                        'source': source_node.ip_address,
                        'destination': dest_node.ip_address,
                        'graph_name': request.collection_name
                    }
                )
                
                results = [doc for doc in cursor]
                
                if not results or not results[0]['path']:
                    logger.warning(f"No path found between {source_node.ip_address} and {dest_node.ip_address}")
                    continue
                
                # Process and append the SRv6 data
                srv6_data = process_path_data(results[0]['path'], source_node.ip_address, dest_node.ip_address)
                
                # Process load data
                load_data = process_load_data(results[0]['path'], request.collection_name, db)
                
                # Add path to the list
                paths.append(SRv6Path(
                    source=source_node.ip_address,
                    destination=dest_node.ip_address,
                    srv6_sid_list=srv6_data["sid_list"],
                    hopcount=results[0]['hopcount'],
                    average_load=results[0]['average_load']
                ))
                
                logger.info(f"Found path from {source_node.ip_address} to {dest_node.ip_address} with {results[0]['hopcount']} hops")
        
        if not paths:
            return NCCLOptimizationResponse(
                job_id=request.job_id,
                status="warning",
                paths=[],
                message="No valid paths found between GPU nodes"
            )
        
        return NCCLOptimizationResponse(
            job_id=request.job_id,
            status="success",
            paths=paths,
            message=f"Successfully optimized {len(paths)} paths for NCCL traffic"
        )
        
    except Exception as e:
        logger.error(f"Error optimizing NCCL paths: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) 