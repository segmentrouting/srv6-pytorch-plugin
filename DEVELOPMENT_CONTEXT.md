# Development Context for SRv6 PyTorch Plugin

This document captures the architectural decisions, lessons learned, and implementation details from the development of this plugin. It's intended to provide context for future development sessions.

## Project Purpose

The SRv6 PyTorch Plugin enables distributed PyTorch training jobs to leverage SRv6 (Segment Routing over IPv6) for intelligent traffic engineering. Instead of relying on standard IP routing, the plugin queries the Jalapeño API for optimal paths and programs SRv6 encapsulation routes on each training node.

### Two Deployment Models

1. **Workload-Controlled SRv6**: The plugin runs inside the training pod and programs SRv6 routes within the pod's network namespace. The workload controls its own traffic engineering.

2. **Infrastructure-Controlled SRv6**: SRv6 encapsulation is done at the host level (on the VM's NIC), and pods are unaware of SRv6. This was validated as feasible (see "Host-Based SRv6" section below).

---

## Architecture Decisions

### CNI Stack

The plugin is designed for Kubernetes with:

| Component | Purpose |
|-----------|---------|
| **Cilium** | Primary CNI for pod networking |
| **Multus** | Adds secondary network interfaces to pods |
| **macvlan** | Backend network for SRv6 traffic (preferred over ipvlan) |
| **Whereabouts** | IPAM for secondary interfaces (optional) |

**Key Lesson**: Cilium's `cni.exclusive=true` setting (default) renames/removes other CNI configs. Set `cni.exclusive=false` in Cilium's Helm values when using Multus:

```yaml
# helm-values.yaml
cni:
  exclusive: false
```

### Why macvlan over ipvlan

We initially tried `ipvlan L3` mode but switched to `macvlan bridge` because:
- ipvlan L3 doesn't respond to Neighbor Discovery (NDP)
- macvlan works better for IPv6 with proper ARP/NDP handling
- macvlan in bridge mode allows pod-to-pod communication on the same host

### Network Interface Naming

Multus assigns secondary interfaces as `net1`, `net2`, etc. The plugin defaults to `net1` for the backend SRv6 interface, configurable via `BACKEND_INTERFACE`.

---

## Environment Variables

All configuration is via environment variables. **No hardcoded values in code.**

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RANK` | Yes | `0` | Node's rank in distributed training |
| `WORLD_SIZE` | Yes | `2` | Total number of training nodes |
| `MASTER_ADDR` | Yes | - | IPv6 address of master node's backend interface |
| `MASTER_PORT` | No | `29500` | Port for PyTorch distributed |
| `BACKEND_INTERFACE` | No | `net1` | Interface for SRv6 traffic |
| `BACKEND_GATEWAY` | No | - | Gateway for backend network routes |
| `BACKEND_ROUTE_PREFIX` | No | - | Prefix for backend network (e.g., `fcbb:0:800::/48`) |
| `SRV6_USID_BLOCK` | No | - | SRv6 uSID block (e.g., `fcbb::/32`) |
| `JALAPENO_API_ENDPOINT` | Yes | - | Jalapeño API URL |
| `TOPOLOGY_COLLECTION` | No | `fabric_graph` | ArangoDB collection name |
| `HOSTS` | No | - | Comma-separated list of hostnames |
| `ROUTE_PLATFORM` | No | `linux` | `linux` or `vpp` |
| `ROUTE_TABLE_ID` | No | `254` | Linux routing table ID |
| `SRV6_ENCAP_MODE` | No | `encap` | `encap` or `encap.red` |

### Important: .env File Behavior

The plugin uses `python-dotenv` with `load_dotenv(override=False)`. This means:
- Kubernetes environment variables take precedence
- `.env` file values are only used if the variable isn't already set
- **Don't include `.env` in the Docker image** for production

---

## Kubernetes Deployment

### Pod Requirements

1. **Privileged mode** for sysctl and route manipulation:
   ```yaml
   securityContext:
     privileged: true
   ```

2. **Multus annotation** for backend network:
   ```yaml
   annotations:
     k8s.v1.cni.cncf.io/networks: |
       [{
         "name": "backend-network",
         "ips": ["fcbb:0:0800:0::2/64"]
       }]
   ```

3. **Startup script** must enable IPv6 forwarding and SRv6:
   ```bash
   sysctl -w net.ipv6.conf.all.forwarding=1
   sysctl -w net.ipv6.conf.all.seg6_enabled=1
   sysctl -w net.ipv6.conf.default.seg6_enabled=1
   sysctl -w net.ipv6.conf.net1.seg6_enabled=1
   ```

4. **Static routes** for backend network:
   ```bash
   ip -6 route add $BACKEND_ROUTE_PREFIX via $BACKEND_GATEWAY dev $BACKEND_INTERFACE
   ip -6 route add $SRV6_USID_BLOCK via $BACKEND_GATEWAY dev $BACKEND_INTERFACE
   ```

### NetworkAttachmentDefinition (NAD)

```yaml
apiVersion: k8s.cni.cncf.io/v1
kind: NetworkAttachmentDefinition
metadata:
  name: backend-network
spec:
  config: |
    {
      "cniVersion": "0.3.1",
      "name": "backend-network",
      "type": "macvlan",
      "master": "ens5",
      "mode": "bridge",
      "ipam": {
        "type": "static"
      }
    }
```

### Keeping Pods Running for Debugging

Add sleep after the test script to keep pods alive:
```yaml
args:
  - |
    python3 /app/examples/test_connectivity.py
    echo "Test complete. Container will stay running for 1 hour."
    sleep 3600
```

---

## SRv6 Integration Details

### Route Programming

The plugin programs SRv6 encapsulation routes using `pyroute2`:

```python
# Example: program route to remote node
ip.route('add',
    dst=destination_prefix,
    oif=interface_index,
    encap={'type': 'seg6',
           'mode': encap_mode,  # 'encap' or 'encap.red'
           'segs': [srv6_sid]})
```

### encap vs encap.red

| Mode | When SRH is Included | Linux seg6local Decap |
|------|---------------------|----------------------|
| `encap` | Always | ✅ Works |
| `encap.red` (2+ SIDs) | Yes | ✅ Works |
| `encap.red` (1 SID) | **No** (plain IPv6-in-IPv6) | ❌ Doesn't work |

**Key Lesson**: If using Linux `seg6local` for decapsulation, use `encap` mode, not `encap.red` with a single SID.

### uSID Support in Linux

Linux supports Compressed SID (uSID) via the `next-csid` flavor:

```bash
# uSID-aware decapsulation
ip -6 route add fcbb:0:800:1::/48 encap seg6local action End.DT6 table main flavors next-csid dev ens5
```

Requires kernel 5.15+ for full support.

### Plain IPv6-in-IPv6 Decapsulation

If you need to decap `encap.red` single-SID packets (no SRH), use `ip6tnl`:

```bash
# Create tunnel for IPv6-in-IPv6 decapsulation
ip -6 tunnel add srv6decap mode ip6ip6 local fcbb:0:800:1:: dev ens5
ip link set srv6decap up
ip -6 route add fcbb:0:800:1::11/128 dev srv6decap
```

---

## Host-Based SRv6 Encapsulation (Feasibility Test)

We validated that infrastructure-controlled SRv6 is feasible, where the host (not the pod) performs SRv6 encapsulation.

### Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Host (VM)                              │
│  ┌─────────┐                                              │
│  │   Pod   │  (no SRv6 awareness)                        │
│  │  net1   │                                              │
│  └────┬────┘                                              │
│       │ ipvlan L3 (traffic routes through host)          │
│  ┌────▼────┐                                              │
│  │  ens5   │  ← SRv6 encap routes here                   │
│  │ + seg6  │                                              │
│  └────┬────┘                                              │
└───────┼──────────────────────────────────────────────────┘
        │ SRv6-encapsulated traffic
        ▼
```

### Requirements

1. **Use ipvlan L3 mode** (not macvlan) so traffic routes through host
2. **Add seg6local route on receiving host** for decapsulation
3. **Add /128 host routes** for pod IPs to avoid routing conflicts with seg6local

### Key Files Created

- `infrastructure/vms/london-vm-00/k8s/test-host-srv6-nad.yaml`
- `infrastructure/vms/london-vm-00/k8s/test-host-srv6-pod.yaml`

---

## Known Issues and Solutions

### 1. Pods Not Getting Secondary Interface

**Symptom**: Pod only has `eth0`, no `net1`

**Causes & Solutions**:
- Cilium `cni.exclusive=true` removing Multus config → Set `cni.exclusive=false`
- Multus kubeconfig missing → Create `/etc/cni/net.d/multus.d/multus.kubeconfig`
- NAD not applied → `kubectl apply -f backend-network-nad.yaml`

### 2. Nodes NotReady After CNI Changes

**Symptom**: `container runtime network not ready: NetworkPluginNotReady`

**Solution**: Restart kubelet on affected nodes:
```bash
sudo systemctl restart kubelet
```

### 3. Pods Evicted Due to DiskPressure

**Symptom**: Pods immediately evicted, even with free disk space

**Solution**: Kubelet has stale disk status. Restart kubelet:
```bash
sudo systemctl restart kubelet
```

### 4. SRv6 Ping Fails with "Parameter Problem"

**Symptom**: ICMP error "Unrecognized Next Header type encountered"

**Causes**:
- Using `encap.red` with single SID (no SRH) → Use `encap` mode
- Missing seg6_enabled sysctl → Enable seg6 sysctls
- seg6local route conflicts with pod IP route → Add more specific /128 route for pod

### 5. PyTorch "Cannot load module more than once"

**Symptom**: numpy import error

**Solution**: Pin numpy version in requirements.txt:
```
numpy>=1.24.0,<2.0.0
```

### 6. Environment Variables Overridden by .env

**Symptom**: Pod uses wrong values despite correct ConfigMap

**Solution**: Use `load_dotenv(override=False)` and don't include `.env` in Docker image

---

## Docker Image Optimization

For CPU-only PyTorch (much smaller image):

```
# requirements.txt
--extra-index-url https://download.pytorch.org/whl/cpu
torch==2.5.1+cpu
```

This reduces image size from ~8GB to ~2GB.

---

## Testing Checklist

1. [ ] Verify nodes are Ready: `kubectl get nodes`
2. [ ] Verify Multus is running: `kubectl get pods -n kube-system -l app=multus`
3. [ ] Verify NAD exists: `kubectl get net-attach-def`
4. [ ] Deploy test pods and check for `net1` interface
5. [ ] Verify SRv6 sysctls are enabled in pods
6. [ ] Verify routes are programmed: `ip -6 route show`
7. [ ] Test ping between pods
8. [ ] Check Jalapeño API connectivity
9. [ ] Verify SRv6 encapsulation with tcpdump

---

## Future Enhancements

1. **Helm Chart**: Package deployment as a Helm chart
2. **Operator**: Kubernetes operator for automatic route management
3. **Metrics**: Prometheus metrics for route programming and latency
4. **VPP Integration**: Complete VPP route programmer implementation
5. **Multi-path**: Support for multiple SRv6 paths with load balancing
6. **Dynamic Re-routing**: React to network changes via Jalapeño subscriptions

---

## Related Resources

- [Jalapeño Documentation](https://github.com/cisco-open/jalapeno)
- [PyTorch Distributed](https://pytorch.org/docs/stable/distributed.html)
- [Cilium CNI](https://docs.cilium.io/)
- [Multus CNI](https://github.com/k8snetworkplumbingwg/multus-cni)
- [Linux SRv6](https://segment-routing.org/index.php/Implementation/Linux)

---

## Contact

For questions about this plugin, refer to the original development conversation transcript or contact the development team.

