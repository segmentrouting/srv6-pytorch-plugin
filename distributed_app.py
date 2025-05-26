import os
import torch
import torch.distributed as dist
from network_optimized_distributed import NetworkOptimizedDistributed

def main():
    # Initialize our wrapper with API endpoint
    net_dist = NetworkOptimizedDistributed(api_endpoint="http://api-service:8000")
    
    # Initialize distributed training with network optimization
    net_dist.init_process_group(backend="nccl")
    
    # Get local rank and world size
    rank = dist.get_rank()
    world_size = dist.get_world_size()
    
    print(f"Process {rank}/{world_size} initialized")
    
    # Create a dummy tensor to simulate NCCL communication
    tensor = torch.ones(10)
    
    # Perform an all-reduce operation (this would use NCCL in a GPU setup)
    dist.all_reduce(tensor, op=dist.ReduceOp.SUM)
    
    print(f"Process {rank}: Result after all_reduce: {tensor}")
    
    # Clean up
    dist.destroy_process_group()

if __name__ == "__main__":
    main() 