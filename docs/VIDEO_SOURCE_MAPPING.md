# DemoPeter 视频 segment → microlesson.v1

> 真源字段清单与 Windows 练手步骤见 DemoPeter：  
> `docs/VIDEO_SEGMENT_GUIBU_CONTRACT.md`  
> 示例 corpora：`config/corpora.video.windows.example.json`

## 对照（摘要）

| microlesson.v1 `sources[]` | DemoPeter segment metadata |
|----------------------------|----------------------------|
| `source` | `source_file` 或 `title` |
| `file_path` | `file_path` |
| `start_sec` | `start_sec` |
| `end_sec` | `end_sec` |
| `excerpt` | chunk / `transcript` |
| `similarity` | 检索 score |
| `corpus_id` | `corpus_id` |

当前 `adapters/demopeter` 在上游未提供时将时间戳置 `null`；Phase 0 透出后在此填实。

## 练手验收

```bash
export GUIBU_DEMOPETER_BASE_URL=http://127.0.0.1:5200   # Windows: set GUIBU_DEMOPETER_BASE_URL=...
python -m adapters.demopeter "变量怎么定义" --validate
```

期望：至少一条 `sources[]` 含非空 `file_path`、`start_sec`、`end_sec`、`excerpt`。
