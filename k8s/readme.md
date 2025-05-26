# Kubernetes Deployment

This directory contains Kubernetes manifests for deploying distributed PyTorch training with SRv6 network optimization.

## Prerequisites

- Kubernetes cluster with SRv6 support
- Access to Jalapeno API
- Docker registry access for the container image

## Deployment Steps

1. First, create the ConfigMap with environment variables:
```bash
kubectl apply -f pytorch-distributed-statefulset.yaml
```

2. Then, choose one of the following deployment methods:

### Option 1: StatefulSet (Recommended for Multi-Node Training)
```bash
kubectl apply -f pytorch-distributed-statefulset.yaml
```
This will create:
- A headless Service for pod DNS
- A StatefulSet with 4 replicas
- Each pod will automatically get a rank based on its ordinal

### Option 2: Job (For Single-Node Testing)
```bash
kubectl apply -f pytorch-distributed-job.yaml
```
This will create:
- A single pod with rank 0
- Useful for testing the setup

## Configuration

The `pytorch-distributed-config` ConfigMap contains the following environment variables:
- `JALAPENO_API_ENDPOINT`: URL of the Jalapeno API
- `TOPOLOGY_COLLECTION`: Name of the topology collection
- `BACKEND_INTERFACE`: Network interface for SRv6 routes
- `ROUTE_PLATFORM`: Route programming platform (linux/vpp)
- `ROUTE_TABLE_ID`: Routing table ID
- `WORLD_SIZE`: Number of training processes
- `MASTER_PORT`: Port for distributed training

## Monitoring

To check the status of your deployment:
```bash
# For StatefulSet
kubectl get pods -l app=pytorch-distributed

# For Job
kubectl get jobs
kubectl get pods -l job-name=pytorch-distributed-training
```

To view logs:
```bash
# For StatefulSet pods
kubectl logs pytorch-distributed-training-0
kubectl logs pytorch-distributed-training-1
# etc.

# For Job pod
kubectl logs -l job-name=pytorch-distributed-training
```