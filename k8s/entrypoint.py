#!/usr/bin/env python3
import os
import sys
import torch
from network_optimized_distributed import NetworkOptimizedDistributed

def main():
    # Get environment variables set by Kubernetes
    rank = int(os.environ.get('RANK', '0'))
    world_size = int(os.environ.get('WORLD_SIZE', '1'))
    master_addr = os.environ.get('MASTER_ADDR', 'localhost')
    master_port = os.environ.get('MASTER_PORT', '29500')
    api_endpoint = os.environ.get('API_ENDPOINT', 'http://network-api:8000')
    
    print(f"Initializing distributed process: rank={rank}, world_size={world_size}")
    print(f"Master: {master_addr}:{master_port}")
    
    # Initialize our network-optimized distributed wrapper
    net_dist = NetworkOptimizedDistributed(api_endpoint=api_endpoint)
    
    # Initialize distributed training with network optimization
    net_dist.init_process_group(backend="nccl")
    
    # Now run your actual training script with the remaining arguments
    if len(sys.argv) > 1:
        training_script = sys.argv[1]
        training_args = sys.argv[2:]
        
        # Execute the training script
        print(f"Launching training script: {training_script}")
        sys.argv = [training_script] + training_args
        with open(training_script) as f:
            exec(f.read())
    else:
        print("No training script specified. Exiting after initialization.")

if __name__ == "__main__":
    main() 