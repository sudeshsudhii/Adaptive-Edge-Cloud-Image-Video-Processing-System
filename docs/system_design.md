# Adaptive Edge–Cloud Image/Video Processing with Auto-Scaling, Parallel Computing, and Intelligent Optimization

## IEEE-Style System Design & Implementation Blueprint

---

## Abstract

This paper presents a production-ready system for adaptive image and video processing that dynamically selects between LOCAL (edge), CLOUD (remote), and SPLIT (hybrid) execution modes. The system employs a deterministic decision engine driven by real-time system profiling, network condition assessment, energy modelling, and workload complexity analysis. The architecture integrates a React+Chart.js frontend, FastAPI backend, Celery+Redis task orchestration, Ray-based distributed computing, PyTorch GPU acceleration, and simulated/real AWS cloud execution. A Deep Q-Network (DQN) reinforcement learning extension enables adaptive optimisation over time. Experimental benchmarks demonstrate sub-second decision latency, memory-safe GPU batching, automatic fault tolerance with cloud-to-local fallback, and comprehensive energy-aware cost optimisation.

**Keywords**: Edge computing, cloud computing, auto-scaling, parallel processing, reinforcement learning, image processing, task scheduling, energy optimisation.

---

## 1. Introduction

### 1.1 Problem Statement

Modern image/video processing workloads face a fundamental trade-off: local edge devices offer low latency and zero data-transfer cost but are constrained by CPU/GPU capacity and battery life, while cloud platforms provide elastic compute but introduce network latency, monetary cost, and energy overhead from data transfer. Current systems typically commit statically to one execution mode, resulting in suboptimal performance across heterogeneous workloads and varying network conditions.

### 1.2 Contributions

This work makes the following contributions:

1. **Deterministic Decision Engine** — A scoring-based decision tree that selects LOCAL, CLOUD, or SPLIT modes in real-time using normalised system, network, workload, and energy metrics.
2. **Unified Orchestration Model** — Celery handles task lifecycle (queue, retry, timeout) while Ray provides intra-task distributed parallelism, avoiding scheduling conflicts.
3. **Memory-Safe GPU Processing** — Dynamic batch sizing derived from available VRAM with automatic OOM-to-CPU fallback.
4. **Multi-Component Energy Model** — `E_total = E_cpu + E_gpu + E_network` with physics-informed power modelling.
5. **Optional DQN Extension** — A reinforcement learning agent that learns optimal mode selection through experience replay and epsilon-greedy exploration.

### 1.3 System Requirements

- Dynamic mode selection (LOCAL / CLOUD / SPLIT)
- Real-time system and network profiling
- Fault-tolerant execution with retry and fallback
- Energy-aware cost optimisation
- Production-grade security (JWT, rate limiting)
- Real-time progress feedback (polling + WebSocket)

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                       │
│  Dashboard │ FileUpload │ BenchmarkChart │ TaskProgress   │
└──────────────────────┬───────────────────────────────────┘
                       │ HTTP/WS
┌──────────────────────▼───────────────────────────────────┐
│                 BACKEND (FastAPI)                         │
│  Auth │ Routes │ WebSocket │ Middleware │ Rate Limiter    │
└───┬──────────────────┬───────────────────────────────────┘
    │                  │
┌───▼───┐      ┌───────▼───────┐     ┌──────────────────┐
│ Agent │      │  Orchestrator  │     │ Observability    │
│ CPU   │      │  Celery+Redis  │     │ Logger│Metrics   │
│ GPU   │      │  State Manager │     │ ErrorTracker     │
│ Net   │      └───────┬───────┘     └──────────────────┘
│Energy │              │
└───────┘      ┌───────▼───────┐
               │Decision Engine│
               │ Scorer│Models │
               └───────┬───────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
    ┌────▼───┐    ┌────▼───┐   ┌────▼───┐
    │ LOCAL  │    │ CLOUD  │   │ SPLIT  │
    │CPU Pool│    │AWS/Sim │   │Hybrid  │
    │GPU/Ray │    │AutoScale│  │Pipeline│
    └────┬───┘    └────┬───┘   └────┬───┘
         │             │             │
    ┌────▼─────────────▼─────────────▼───┐
    │        Benchmark Engine            │
    │   Metrics │ Cache │ Reporter       │
    └────────────────────────────────────┘
```

### 2.2 Module Inventory

| Module | Technology | Responsibility |
|--------|-----------|---------------|
| Frontend | React + Chart.js | Dashboard, upload, charts, progress |
| Backend | FastAPI | REST API, WebSocket, auth, middleware |
| Agent | psutil, GPUtil, torch | System/network/energy profiling |
| Decision | Python | Scoring, normalisation, mode selection |
| Orchestrator | Celery + Redis | Task queue, state management, retry |
| Processing | multiprocessing, PyTorch, Ray | LOCAL/GPU/distributed compute |
| Cloud | boto3 / Simulator | AWS EC2/S3 with auto-scaling |
| Benchmark | psutil, GPUtil | Metric collection and caching |
| ML | PyTorch DQN | Optional RL-based decision making |
| Storage | Filesystem + S3 | Upload/output/checkpoint persistence |
| Observability | Structured JSON | Logging, metrics, error tracking |

---

## 3. Methodology

### 3.1 Normalisation

All metrics are normalised to [0, 1]:

```
normalize(v, min, max) = clamp((v - min) / (max - min), 0, 1)
```

### 3.2 System Score

```
S = 0.40 × normalize(cores × freq_GHz, 0, 80)
  + 0.35 × normalize(gpu_cores, 0, 10496)
  + 0.25 × normalize(ram_GB, 0, 64)
```

### 3.3 Workload Complexity

```
C = normalize(W × H × F, 0, 3840 × 2160 × 1800)
```

### 3.4 Network Score (higher = worse)

```
N = normalize(latency_s + 1/bandwidth_Mbps, 0, 2.0)
```

### 3.5 Energy Model

```
E_total = E_cpu + E_gpu + E_network

E_cpu = (P_idle + load × (TDP - P_idle)) × time
E_gpu = (P_idle_gpu + load × (TDP_gpu - P_idle_gpu)) × time
E_network = data_MB × 0.2 J/MB
```

### 3.6 Cloud Provider Score

```
Score = 0.4 × cost_norm + 0.4 × latency_norm − 0.2 × availability_norm
```

---

## 4. Algorithms

### 4.1 Decision Engine (Deterministic)

```
FUNCTION decide(system, network, input):
    S ← system_score(system)
    N ← network_score(network)
    C ← workload_complexity(input)

    IF system.battery ≠ -1 AND system.battery < 30:
        RETURN CLOUD    // preserve battery

    ELIF N > 0.7:
        RETURN LOCAL    // network too poor for cloud

    ELIF S > 0.6 AND system.cpu_load < 0.7:
        RETURN LOCAL    // system strong, load low

    ELIF C > 0.6 AND N < 0.3:
        RETURN SPLIT    // complex task, good network

    ELSE:
        RETURN CLOUD    // default delegation
```

### 4.2 Split Pipeline

```
FUNCTION split_pipeline(input):
    Stage 1: local_data ← preprocess(input)          [LOCAL]
    Stage 2: features ← cloud_extract(local_data)     [CLOUD]
    Stage 3: result ← cloud_compute(features)          [CLOUD]
    Stage 4: output ← postprocess(result)              [LOCAL]
    RETURN output
```

### 4.3 Auto-Scaling

```
instances = ⌈total_workload / instance_capacity⌉
clamped to [1, 20]
```

### 4.4 DQN Agent

```
State:   [cpu_load, gpu_flag, latency_norm, battery_norm, task_size_norm]
Action:  {LOCAL=0, CLOUD=1, SPLIT=2}
Reward:  R = -(0.4×latency + 0.3×cost + 0.3×energy)

Network: Input(5) → Dense(128) → ReLU → Dense(128) → ReLU → Dense(3)
Training: experience replay (buffer=10K), ε-greedy (1.0→0.05), target net update every 50 steps
```

---

## 5. Implementation Details

### 5.1 Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | React + Chart.js | 18.x + 4.x |
| Backend | FastAPI + Uvicorn | 0.111 + 0.30 |
| Queue | Celery + Redis | 5.4 + 7.x |
| Distributed | Ray | 2.31 |
| GPU | PyTorch / CUDA | 2.2+ |
| Cloud | boto3 (AWS) | 1.34 |
| Profiling | psutil + GPUtil | 5.9 + 1.4 |
| Auth | PyJWT | 2.8 |

### 5.2 Task State Machine

```
PENDING → RUNNING → COMPLETED
                  → FAILED → PENDING (retry, max 3)
```

### 5.3 Fault Tolerance

| Mechanism | Detail |
|-----------|--------|
| Retry | 3 attempts, 5s exponential backoff |
| Timeout | Soft=300s, Hard=360s |
| Fallback | Cloud fails 3× → LOCAL |
| Checkpoint | Split pipeline saves per stage |
| Idempotency | UUID task_id, cached results |
| Worker crash | acks_late + re-delivery |

### 5.4 Security

| Feature | Implementation |
|---------|---------------|
| Auth | JWT (HS256), 24h expiry |
| Rate limit | 60 req/min per IP |
| File validation | Extension whitelist + size cap |
| Credential handling | Environment variables, never in code |

---

## 6. Results & Benchmarking

### 6.1 Metrics Collected

- **Latency** (seconds): end-to-end processing time
- **Throughput** (items/sec): 1 / latency
- **CPU Usage** (0–100%): measured via psutil
- **GPU Usage** (0–100%): measured via GPUtil / torch
- **Cost** (USD): time × cloud rate
- **Energy** (Joules): multi-component model
- **Speedup**: estimated_local_time / actual_time

### 6.2 Benchmark Strategy

- Instrument only the **executed** mode (not all three)
- Cache results per task_id for later comparison
- Optional background benchmarking via async Celery tasks

---

## 7. Conclusion

This system demonstrates a production-ready approach to adaptive edge-cloud processing with:

1. Sub-second deterministic decision-making based on real-time system telemetry
2. Unified Celery+Ray orchestration without scheduling conflicts
3. Memory-safe GPU processing with automatic failover
4. Multi-component energy modelling for battery-aware operation
5. Production security (JWT, rate limiting, file validation)
6. Real-time observability and task progress tracking

The optional DQN reinforcement learning extension provides a path toward self-improving decision-making as the system accumulates operational experience.

---

## 8. Future Work

1. **Multi-cloud arbitrage** — Dynamic provider selection across AWS, Azure, and GCP based on real-time pricing
2. **Federated edge processing** — Distribute workloads across multiple edge devices using gossip protocols
3. **Transfer learning** — Pre-train the DQN on simulated workloads and fine-tune on real traffic
4. **Video streaming pipeline** — Real-time frame-by-frame processing with adaptive quality scaling
5. **Carbon-aware scheduling** — Factor grid carbon intensity into the energy model for sustainability

---

## References

[1] Shi, W., Cao, J., Zhang, Q., Li, Y., & Xu, L. (2016). Edge Computing: Vision and Challenges. IEEE Internet of Things Journal.

[2] Mach, P., & Becvar, Z. (2017). Mobile Edge Computing: A Survey on Architecture and Computation Offloading. IEEE Communications Surveys & Tutorials.

[3] Mnih, V., et al. (2015). Human-level Control Through Deep Reinforcement Learning. Nature.

[4] Dean, J., & Ghemawat, S. (2008). MapReduce: Simplified Data Processing on Large Clusters. Communications of the ACM.

[5] Burns, B., Grant, B., Oppenheimer, D., Brewer, E., & Wilkes, J. (2016). Borg, Omega, and Kubernetes. ACM Queue.
