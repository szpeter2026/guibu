# adapters/demopeter

只读适配：DemoPeter `POST /api/rag/query` → Guibu `microlesson.v1`。

## 用法

```bash
# 仓库根目录
export GUIBU_DEMOPETER_BASE_URL=http://127.0.0.1:5200
python -m adapters.demopeter "列表推导式怎么用"
python -m adapters.demopeter "列表推导式怎么用" --validate
```

## 映射说明

| microlesson 字段 | DemoPeter 字段 |
|------------------|----------------|
| `summary` | `answer` |
| `sources[].source` | `sources[].source` |
| `sources[].excerpt` | `sources[].content` |
| `start_sec` / `end_sec` | 暂无 → `null` |
| `retrieval_mode` | `retrieval_mode` |
| `gaps` | 无命中 / retrieval_only / 低相似度时生成 |

不写入 DemoPeter；导入语料仍用 DemoPeter 自己的 Web / CLI。
