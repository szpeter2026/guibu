# Phase 1 多仓联调指南

多仓联调说明（结构图、闭环清单、复跑命令）的**真源**在 Tractor：

→ [`/Users/jason/SurfaceZervi/Tractor/docs/Phase1_多仓联调指南.md`](../../Tractor/docs/Phase1_多仓联调指南.md)

Guibu 侧最短命令：

```bash
# 真闭环 → Tatha :8010（需 DemoPeter :5210 + Tatha 已起）
source .venv/bin/activate
python scripts/smoke_skill_proof.py --email learner@example.com

# 本地自测 → Tractor mock :3999
python scripts/smoke_skill_proof.py --email learner@example.com \
  --ingest-url http://127.0.0.1:3999
```
