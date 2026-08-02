# 不积硅步 / Guibu

> **可审计的微步** — Auditable micro-steps  
> 学一步，留一迹——出处可溯、学时可稽

Guibu 是面向考证 / 职培平台的 **按需技能微课交付壳（shell）**：编排现有能力，不重写各仓内核。

| | |
|--|--|
| 品牌 | 不积硅步 · 硅步 · **Guibu** |
| 定位 | Grounded micro-lesson delivery for skills platforms |
| 命名定稿 | [docs/NAMING.md](./docs/NAMING.md) |
| 架构 | [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) |
| 微课契约 | [contracts/microlesson.v1.json](./contracts/microlesson.v1.json) |

---

## 一句话价值

业界 AIGC 热点多在审计「这条内容是不是 AI 造的」；  
**Guibu 审计的是「这一步技能是不是真学过、从哪段课来」。**

---

## 边界（谁做什么）

```
考证 / 职培平台
        ↓
     Guibu 壳          ← 本仓：契约 · 适配 · 编排 · 审计导出
        ├── DemoPeter  ← 内容溯源 / RAG sources（只读适配）
        ├── looma      ← 学习时间线（后续）
        └── YeDall     ← 学完可证 attestation（可选后期）
```

| 系统 | 角色 | Guibu 是否深入改写 |
|------|------|-------------------|
| **Guibu（本仓）** | 薄壳：统一 API 形状、适配器、审计包 | — |
| **DemoPeter** | 内容出处：`file_path` / sources / 将来视频段 | ❌ 只读调用 |
| **looma-zervi** | 行为时间戳：`timeline_events` / trust | ❌ 后续适配 |
| **YeDall** | 信任协议 / 权威凭证核验 | ❌ 不把壳做进协议仓 |

**刻意不做：** 自建考证发证平台、第二套招聘 SaaS、C2PA/水印主业、推倒重写各仓 RAG。

---

## 当前进度

| 项 | 状态 |
|----|------|
| 命名定稿 | ✅ |
| 微课契约 `microlesson.v1` | ✅ 初版 |
| DemoPeter 只读适配（问 → sources → 微课形状） | ✅ 初版 |
| looma 学迹适配 | ⏳ |
| 视频 `start_sec/end_sec` | ⏳（DemoPeter Phase 0） |
| 审计导出包 | ⏳ |

---

## 快速试用（DemoPeter 通路）

前提：本机 DemoPeter Web 已启动（默认 `http://127.0.0.1:5200`），且知识库有语料。

```bash
cd /Users/jason/SurfaceZervi/guibu
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export GUIBU_DEMOPETER_BASE_URL=http://127.0.0.1:5200
python -m adapters.demopeter "列表推导式怎么用"
```

成功时打印符合 `microlesson.v1` 的 JSON（含 `sources[]`；视频时间戳字段在 DemoPeter 未提供前为 `null`）。

---

## 仓库结构

```
guibu/
├── README.md
├── requirements.txt
├── contracts/
│   └── microlesson.v1.json
├── adapters/
│   └── demopeter/          # 只读：POST /api/rag/query → 微课形状
├── docs/
│   ├── NAMING.md
│   └── ARCHITECTURE.md
└── .env.example
```

---

## 相关仓

| 仓 | 用途 |
|----|------|
| [szpeter2026/DemoPeter](https://github.com/szpeter2026/DemoPeter) | 内容溯源底座 |
| [szpeter2026/guibu](https://github.com/szpeter2026/guibu) | 本壳 |
| Desktop/YeDall | 协议与验证（不并入本仓） |
| looma-zervi | 学迹 / trust（后续适配） |
