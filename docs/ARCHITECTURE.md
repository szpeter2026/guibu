# Guibu 架构（一页）

> **版本：** 0.1 · **日期：** 2026-08-02  
> **原则：** 壳只编排，不重写 DemoPeter / looma / YeDall 内核。

---

## 1. 系统位置

```
┌─────────────────────────────────────────────┐
│  考证平台 / 职培 LMS / 内部工具               │
└─────────────────────┬───────────────────────┘
                      │  microlesson.v1 / 学迹（后续）
┌─────────────────────▼───────────────────────┐
│  Guibu shell（本仓）                         │
│  contracts · adapters · （未来）audit export │
└───────┬─────────────────┬───────────────────┘
        │                 │
        ▼                 ▼
┌───────────────┐  ┌──────────────┐  ┌────────────┐
│ DemoPeter     │  │ looma-zervi  │  │ YeDall     │
│ 内容溯源 RAG  │  │ 学迹/timeline│  │ 可验证声明 │
│ （只读适配）  │  │ （后续）     │  │ （可选后期）│
└───────────────┘  └──────────────┘  └────────────┘
```

---

## 2. 第一条通路（已实现初版）

```
query
  → adapters.demopeter.client  POST {DEMOPETER}/api/rag/query
  → map_to_microlesson()
  → microlesson.v1 JSON
```

| 字段 | 来源 |
|------|------|
| `summary` | DemoPeter `answer` |
| `sources[].source` / `excerpt` | DemoPeter `sources[]` |
| `start_sec` / `end_sec` | 暂无 → `null`（等视频 ingest） |
| `gaps` | 无命中 / retrieval_only / 低置信时生成 |
| `provider` | 固定 `demopeter` + 端点元数据 |

---

## 3. 不变量

1. **对外只暴露 Guibu 契约**，不直接把 DemoPeter 原始 JSON 当产品 API。  
2. **适配器默认只读**；写入语料仍在 DemoPeter 运营面完成。  
3. **缺口只建一套叙事**：微课 `gaps[]` 后续可桥到 DemoPeter `gap_tasks` / looma 事件，不平行发明第二套。  
4. **YeDall 保持协议仓**；壳不实现第二套 trust SaaS。

---

## 4. 下一步挂载点

| 优先级 | 挂载 | 说明 |
|--------|------|------|
| P1 | `adapters/looma` | `microlesson_viewed` → `timeline_events` |
| P1 | 审计导出 | 谁 / 何时 / 哪条 source → 一包 JSON |
| P2 | DemoPeter 视频段 | metadata 带 `start_sec/end_sec` 后映射填实 |
| P3 | YeDall verify | 学完可证 attestation |

---

## 5. 相关文档

- [NAMING.md](./NAMING.md)  
- [../contracts/microlesson.v1.json](../contracts/microlesson.v1.json)  
- DemoPeter：`docs/按需微课MVP规划.md`（SurfaceZervi 镜像仓）
