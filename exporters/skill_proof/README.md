# skill-proof 导出方

把 `microlesson.v1` 聚合为 `skill-proof.v1`，供 JobFirst 简历增强消费。

## 契约

- 真源：`contracts/skill-proof.v1.json`（Tatha 摄入端与 claw 工具端引用同一 schema）
- `user_id` = `sha256(email.lower().trim())`（64 位 hex，2026-08-12 已决策）

## 用法

```bash
cd /Users/jason/SurfaceZervi/guibu
source .venv/bin/activate

# 方式 1：实时问 DemoPeter（需 :5210 已启动）
python -m exporters.skill_proof \
  --email learner@example.com \
  --query "列表推导式怎么用" \
  --query "Python 数据结构有哪些" \
  --validate

# 方式 2：读本地 microlesson JSON
python -m exporters.skill_proof \
  --email learner@example.com \
  --lesson-file out/lesson1.json \
  --lesson-file out/lesson2.json \
  --out out/skill-proof.json

# 方式 3：聚合后 POST 到 mock ingest（需 Tractor mock :3999）
python -m exporters.skill_proof \
  --email learner@example.com \
  --lesson-file out/lesson1.json \
  --validate \
  --ingest
# 或指定完整 URL：
#   --ingest http://127.0.0.1:3999/v1/skills/ingest
```

冒烟（含可选 egress）：

```bash
# DemoPeter :5210 + mock :3999
python scripts/smoke_skill_proof.py --email learner@example.com
# 仅本地聚合 + schema：
python scripts/smoke_skill_proof.py --no-ingest
```

## 设计约束（对齐 Tractor 适配方案 §7.1 / §十）

- Phase 1 只传 `evidence[]` 原文 + 轻量 `skill_tags`，技能语义由下游 LLM 判断。
- `skill_tags` 用关键词白名单兜底，无命中时退回 query 前 30 字，保证非空。
- `learned_at` Phase 1 用 microlesson 的 `generated_at` 代替；Phase 2 从 looma timeline 拉取。
- egress：`post_skill_proof(url, proof)` 用 urllib 直连；HMAC 占位，接 Tatha 真端点再启用。
