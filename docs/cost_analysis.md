# Cloud Run Cost Analysis: 24/7 Streaming & AI

Running this application 24/7 on Cloud Run with your current configuration (**1 vCPU, 2GiB RAM**) will significantly reduce compute costs, though network egress remains a major driver.

## 💰 Summary Estimate (Updated for 1 vCPU / 2GiB)
| Category | Estimated Daily Cost | Estimated Monthly Cost |
| :--- | :--- | :--- |
| **Compute (1 vCPU / 2GiB)** | ~$2.50 | ~$75.00 |
| **Network Egress (Video)** | ~$9.00 - $12.00 | ~$270.00 - $360.00 |
| **Total Baseline** | **~$11.50 - $14.50** | **~$345.00 - $435.00** |

---

## 📊 Model Tier Comparison (Cloud Run)

If you upgrade to larger models, your compute costs will increase due to higher RAM and GPU requirements. Note that 7B+ models generally require an **Nvidia L4 GPU** for acceptable latency.

| Model Tier | Configuration | Est. Compute Cost (24/7) | AI Latency |
| :--- | :--- | :--- | :--- |
| **Qwen 2B** | 1-2 vCPU, 2-4GB RAM | **$75 - $150 / mo** | Slow (CPU) |
| **Qwen 3B** | 4 vCPU, 8GB RAM | **~$300 / mo** | Moderate (CPU) |
| **Qwen 7B** | 4 vCPU, 16GB RAM + **L4 GPU** | **~$750 / mo** | Fast (GPU) |
| **Qwen 9B** | 8 vCPU, 32GB RAM + **L4 GPU** | **~$1,100 / mo** | Fast (GPU) |

*Prices exclude Network Egress (~$300/mo) and assume the instance is active 24/7.*

---

## 🖥️ Can CPUs handle Qwen models?

Yes, but with caveats. Qwen VL models can technically run on CPUs using standard libraries like `torch` and `transformers`, which is why your **Qwen 2B** setup works today.

### 🧠 CPU Viability by Model Size
- **2B / 3B Models**: These are "CPU-viable" for logging tasks that run every 15-60 seconds. On 4 vCPUs, a summary might take 2-5 seconds. 
- **⚠️ RAM Hazard**: Your current **2GiB** setting is very risky. Qwen 2B typically needs **~3.5GB to 5GB** of RAM to load comfortably along with the OS and backend. You may see **Out of Memory (OOM)** crashes during model loading.
- **7B / 9B Models**: These are **NOT practical on CPUs** for your 24/7 use case because:
    - **Latency**: A single frame summary can take **30 to 60+ seconds** on a CPU, which is slower than your 15s logging interval.
    - **RAM Cost**: They require **15GB to 20GB+** of RAM. On Cloud Run, paying for 32GB of CPU-only RAM is often **more expensive** than just attaching an L4 GPU.

**Recommendation**: Stick to **Qwen 2B** if you want to avoid GPU costs, but increase your RAM to at least **4GiB** to ensure stability.

## 🔍 Key Cost Drivers

### 1. "Always-On" Background Threads
Cloud Run typically scales to zero when no requests are active. However, your backend starts two background tasks on startup:
- `generate_frames`: Continuously captures and processes RTSP frames.
- `auto_observation_loop`: Runs AI scene analysis every 15 seconds.

**Impact**: These loops keep the CPU active 100% of the time, meaning Cloud Run will bill you for every second the container is alive.

### 2. Reduced Resources (1 vCPU / 2GiB)
- You have switched to **1 vCPU and 2GiB RAM**. This is much more cost-effective for standby.
- **Note**: Qwen2-VL-2B may run slower on 1 vCPU and 2GB might be tight for the model weights. If you see crashes (OOM) or extremely slow AI summaries, you may need to go back to 2 vCPU / 4GiB.

### 3. Network Egress (The "Silent Killer")
Streaming 640x360 video at 30 FPS via WebSockets is bandwidth-heavy.
- **Estimated Data**: ~30KB per frame * 30 FPS = ~0.9 MB/s.
- **24-Hour Total**: ~77 GB of data sent over the internet.
- **Cost**: Google Cloud charges ~$0.12 per GB for internet egress.
- **Impact**: Egress alone now costs **3-4x more** than the compute resources.

---

## 💡 Optimization Recommendations

1. **Reduce Frame Rate**: Lowering the WebSocket stream to 10-15 FPS can cut egress costs by 50-70%.
2. **Increase Logging Interval**: Changing the AI summary interval from 15s to 5 minutes will reduce CPU pressure.
3. **Lazy Streaming**: Modify the backend to only run `generate_frames` when at least one WebSocket client is connected. 
4. **On-Demand AI**: Trigger AI summaries based on motion detection events rather than a fixed timer.
