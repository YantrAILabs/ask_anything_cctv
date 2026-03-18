# Cloud Run Cost Analysis: 24/7 Streaming & AI

Running this application 24/7 on Cloud Run with your current configuration (**1 vCPU, 2GiB RAM**) will significantly reduce compute costs, though network egress remains a major driver.

## 💰 Summary Estimate (Updated for 1 vCPU / 2GiB)
| Category | Estimated Daily Cost | Estimated Monthly Cost |
| :--- | :--- | :--- |
| **Compute (1 vCPU / 2GiB)** | ~$2.50 | ~$75.00 |
| **Network Egress (Video)** | ~$9.00 - $12.00 | ~$270.00 - $360.00 |
| **Total Baseline** | **~$11.50 - $14.50** | **~$345.00 - $435.00** |

---

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
