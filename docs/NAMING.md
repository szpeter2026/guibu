# 不积硅步 / Guibu · 中英命名定稿

> **版本：** 1.0 · **日期：** 2026-08-02  
> **状态：** 已采纳  
> **来源：** training-line / Guibu 产品命名对话定稿

---

## 1. 定稿表

| 用途 | 中文 | English |
|------|------|---------|
| **主品牌** | **不积硅步** | **Guibu** |
| **产品短名** | **硅步** | **Guibu** |
| **价值副标** | 可审计的微步 | Auditable micro-steps |
| **一句话** | 学一步，留一迹——出处可溯、学时可稽 | Learn in steps you can audit |
| **品类定位** | 按需技能微课交付引擎（赋能考证/职培平台） | Grounded micro-lesson delivery for skills platforms |
| **域名（首选）** | — | **guibu.ai** 或 **guibu.io** |
| **域名（备选）** | — | guibu.tech / getguibu.com |
| **工程仓名** | — | **guibu**（或 `guibu-shell`） |
| **工作区目录** | — | `SurfaceZervi/guibu`（由 `training-line` 更名） |
| **模块/适配前缀** | — | `guibu-adapter-demopeter` / `guibu-adapter-looma` |

---

## 2. 分层用法

```
不积硅步（品牌气质 · 典故「跬步」× 硅）
    └── 硅步 / Guibu（日常称呼、Logo、App、仓与域）
            ├── 副标：可审计的微步 / Auditable micro-steps
            └── 工程：guibu · guibu.ai
```

| 受众 | 怎么讲 |
|------|--------|
| 职培 / 考证机构采购 | 先副标「可审计的微步」，再讲补贴学时、出处可稽 |
| 学员 / 传播 | 「不积硅步 / 硅步」——卡点微课、积步成才 |
| 英文材料 | 主名 **Guibu**；首次出现写 *Guibu (auditable micro-steps)* |
| AIGC 合规（可选层） | **不进主名**；技术说明可写 optional Content Credentials on AI-assembled clips |

---

## 3. 命名原则（对话共识）

1. **中文保梗，英文不硬译**  
   「硅步」= 跬步谐音 + 技术感；英文用音译 **Guibu**，不译 *Silicon Step*。

2. **价值靠副标钉死**  
   主品牌传气质；「可审计的微步」传采购刚需（溯源 + 时间戳）。

3. **与 AIGC 内容溯源热点区分**  
   业界热点多审计「这条内容是不是 AI 造的」；我们审计「这一步技能是不是真学过、从哪段课来」。  
   蹭标准与审计包形态，不抢 C2PA/水印赛道。

4. **壳仓定位**  
   `guibu` = 薄编排壳；不深入改写 DemoPeter / looma / YeDall。  
   YeDall 仍为信任协议仓，可后期承接「学完可证」attestation。

---

## 4. 刻意不用

| 弃用 | 原因 |
|------|------|
| StepTrace / ProofBridge 做主品牌 | 可留作功能名或英文备选域 |
| training-line 对外 | 仅历史过渡目录名 |
| Silicon Stride | 像芯片公司，丢「学迹」 |
| 把 YeDall 当 shell 品牌 | BOUNDARY：协议仓 ≠ 内容交付壳 |

---

## 5. 仓库建议结构

```
guibu/                      # shell 真源
  adapters/
    demopeter/              # 内容溯源 / 将来视频段
    looma/                  # 学习记录 / timeline（过渡）
  contracts/                # 微课包 · 学迹 · 审计导出
  docs/
    NAMING.md               # 本文
```

---

## 6. 首次对外句式（可直接复制）

**中文**

> **不积硅步（硅步）**——可审计的微步。  
> 为考证与职培平台提供按需技能微课交付：出处可溯、学时可稽。

**English**

> **Guibu** — auditable micro-steps.  
> Grounded micro-lesson delivery for skills and certification platforms: learn in steps you can audit.

---

## 7. 修订记录

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2026-08-02 | 首版定稿；目录 `training-line` → `guibu` |
