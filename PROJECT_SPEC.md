# Taiwan Travel Agent - 專案開發規格文件

> 📘 **協作說明**:本專案採用 Claude Chat (Opus, 學習/規劃) + Claude Code CLI (Sonnet, 實作) 雙軌模式。詳細分工原則見 `CLAUDE.md` 的「與 Claude Chat 的分工」section,學習筆記記錄在 `PROGRESS.md` 的「先學會」與「學習筆記」欄位。

> 這份文件是給 Claude Code CLI 閱讀的專案規格。
> 請逐階段實作,每完成一個 Phase 後更新 PROGRESS.md。

---

## 📌 專案目標

打造一個基於 **LangGraph + LangChain + FastAPI + Claude API** 的台灣旅遊 AI Agent 系統,作為求職作品集。

**核心價值主張**:展示 AI Agent 工作流設計能力,包含:
- 多步驟 Agent Pipeline(意圖解析 → 並行檢索 → 整合 → HITL 審核 → 輸出)
- LangGraph 併行工作流與條件分支
- Human-in-the-Loop 審核流程
- RAG Pipeline(向量檢索 + 重排序)
- FastAPI 即時串流回應(SSE)

---

## 🎯 使用者故事

```
作為一個想去台灣旅遊的使用者,
我輸入「我想去台北玩 2 天,喜歡老街跟小吃,預算 5000 元」,
Agent 會:
1. 解析我的意圖(地點、天數、偏好、預算)
2. 並行檢索景點、美食、交通資訊
3. 整合成行程草案
4. 讓我審核(可以說「換掉第 2 天的景點」)
5. 重新生成最終行程
```

---

## 🏗️ 系統架構

### 技術棧

| 層級 | 技術 | 用途 |
|---|---|---|
| LLM | Claude API (Anthropic) | 主要推理引擎 |
| Agent 框架 | LangChain + LangGraph | 工作流編排 |
| Vector DB | ChromaDB(本地) | RAG 向量檢索 |
| Backend | FastAPI | API 服務 + SSE 串流 |
| ORM | SQLAlchemy | 資料模型 |
| DB | SQLite(MVP)/ PostgreSQL(進階) | 對話歷史儲存 |
| 容器化 | Docker + Docker Compose | 部署 |
| 語言 | Python 3.11+ | 主要語言 |

### 架構圖

```
┌─────────────────────────────────────────────────────────┐
│                   FastAPI (SSE Stream)                  │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    LangGraph Workflow                   │
│                                                         │
│  ┌──────────────┐                                      │
│  │ Intent Parser│ ──┐                                  │
│  └──────────────┘   │                                  │
│                     ▼                                  │
│           ┌─────────────────┐                          │
│           │  Parallel Nodes │                          │
│           │  ┌───────────┐  │                          │
│           │  │ Attraction│  │                          │
│           │  │  RAG      │  │                          │
│           │  └───────────┘  │                          │
│           │  ┌───────────┐  │                          │
│           │  │ Food RAG  │  │                          │
│           │  └───────────┘  │                          │
│           │  ┌───────────┐  │                          │
│           │  │ Transport │  │                          │
│           │  └───────────┘  │                          │
│           └─────────┬───────┘                          │
│                     ▼                                  │
│           ┌─────────────────┐                          │
│           │ Itinerary       │                          │
│           │ Generator       │                          │
│           └─────────┬───────┘                          │
│                     ▼                                  │
│           ┌─────────────────┐                          │
│           │ HITL Review     │ ◄─── User Feedback       │
│           │ (interrupt)     │                          │
│           └─────────┬───────┘                          │
│                     ▼                                  │
│           ┌─────────────────┐                          │
│           │ Final Output    │                          │
│           └─────────────────┘                          │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 專案目錄結構

```
taiwan-travel-agent/
├── README.md                      # 專案介紹(對外)
├── PROJECT_SPEC.md                # 本文件(給 Claude Code 看)
├── PROGRESS.md                    # 進度追蹤(每個 phase 後更新)
├── CLAUDE.md                      # Claude Code 工作指引
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml                 # 用 uv 管理(或 requirements.txt)
├── .env.example
├── .gitignore
│
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI 入口
│   ├── config.py                  # 環境變數設定
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── graph.py               # LangGraph 主工作流
│   │   ├── nodes/
│   │   │   ├── __init__.py
│   │   │   ├── intent_parser.py   # 意圖解析節點
│   │   │   ├── attraction_rag.py  # 景點檢索節點
│   │   │   ├── food_rag.py        # 美食檢索節點
│   │   │   ├── transport.py       # 交通資訊節點
│   │   │   ├── itinerary.py       # 行程生成節點
│   │   │   └── reviewer.py        # HITL 審核節點
│   │   └── state.py               # AgentState 定義
│   │
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── vector_store.py        # ChromaDB 操作
│   │   ├── embeddings.py          # Embedding 函式
│   │   └── retriever.py           # 混合檢索 + Reranking
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py              # API endpoints
│   │   └── schemas.py             # Pydantic schemas
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py              # SQLAlchemy models
│   │   └── session.py             # DB session
│   │
│   └── utils/
│       ├── __init__.py
│       └── llm_client.py          # Claude API wrapper
│
├── data/
│   ├── attractions.json           # 景點資料(50 筆)
│   ├── foods.json                 # 美食資料(50 筆)
│   └── seed.py                    # 初始化向量資料庫
│
├── tests/
│   ├── test_agents.py
│   └── test_rag.py
│
└── docs/
    ├── architecture.md            # 架構說明
    └── demo.gif                   # Demo 動畫(最後錄)
```

---

## 🗓️ 實作階段(5 天)

### Phase 1:環境搭建 + LLM 基礎(Day 1)

**目標**:能透過 FastAPI 呼叫 Claude API 並回應觀光問題。

**任務清單**:
- [x] 用 uv 或 venv 初始化專案
- [x] 安裝套件:`fastapi`, `uvicorn`, `anthropic`, `langchain`, `langgraph`, `chromadb`, `sqlalchemy`, `pydantic-settings`, `python-dotenv`
- [x] 建立 `app/config.py` 讀取 `.env`(ANTHROPIC_API_KEY)
- [x] 建立 `app/utils/llm_client.py` 包裝 Claude API 呼叫
- [x] 建立 `app/main.py` 與最簡單的 `/chat` endpoint(POST,接收 query 字串,回傳 Claude 回答)
- [x] 寫 `.env.example` 與 `.gitignore`
- [x] 用 curl 測試:`curl -X POST localhost:8000/chat -d '{"query":"九份在哪裡"}'`

**驗收標準**:能跑起 FastAPI,丟問題能拿到 Claude 回答。

---

### Phase 2:RAG Pipeline(Day 2)

**目標**:建立向量資料庫,讓 Agent 能基於台灣景點資料回答問題。

**任務清單**:
- [x] 建立 `data/attractions.json`(50 筆台灣景點)
- [x] 建立 `data/foods.json`(50 筆台灣美食)
- [x] 建立 `app/rag/embeddings.py` — sentence-transformers bge-m3(1024 維,本機)
- [x] 建立 `app/rag/vector_store.py` — ChromaDB 初始化(cosine HNSW)、新增、查詢
- [x] 建立 `scripts/seed.py` — 批次 embed + 寫入 ChromaDB(attractions 50 + foods 50)
- [x] 建立 `app/rag/retriever.py` — 兩階段混合檢索:
  - Stage 1: 向量(bge-m3) + BM25(jieba 中文斷詞) → RRF 融合 → top-20
  - Stage 2: bge-reranker-v2-m3 CrossEncoder → top-5
- [x] 修改 `/chat` endpoint:RAG 檢索景點+美食各 top-3,注入 prompt 再呼叫 Claude
- [x] 測試:「九份老街茶館夜景」→ score=0.988 ✅

**驗收標準**:RAG 能正確檢索並回答觀光問題,不再靠 Claude 自己生成(避免幻覺)。

---

### Phase 3:LangGraph 工作流(Day 3)

**目標**:用 LangGraph 重構 Agent,實作多步驟 + 並行工作流。

**任務清單**:
- [ ] 建立 `app/agents/state.py` 定義 `AgentState`(TypedDict),包含:
  ```python
  class AgentState(TypedDict):
      user_query: str
      intent: dict          # {location, days, preferences, budget}
      attractions: list     # RAG 結果
      foods: list           # RAG 結果
      transport: list       # 交通資訊
      itinerary_draft: str  # 行程草稿
      user_feedback: str    # HITL 回饋
      final_output: str     # 最終輸出
      messages: list        # 對話歷史
  ```
- [ ] 建立 `app/agents/nodes/intent_parser.py`:
  - 用 Claude + structured output(JSON schema)解析使用者輸入
  - 輸出格式:`{location, days, preferences: [], budget}`
- [ ] 建立 `app/agents/nodes/attraction_rag.py`:呼叫 RAG 取景點
- [ ] 建立 `app/agents/nodes/food_rag.py`:呼叫 RAG 取美食
- [ ] 建立 `app/agents/nodes/transport.py`:用 Claude 生成簡易交通建議(MVP 階段不接外部 API)
- [ ] 建立 `app/agents/nodes/itinerary.py`:整合三個來源,生成行程草稿
- [ ] 建立 `app/agents/graph.py`:
  ```
  intent_parser → [attraction_rag, food_rag, transport] (並行)
                → itinerary → END
  ```
  使用 LangGraph 的 `StateGraph`,在三個 RAG 節點用 `add_edge` 設計併行
- [ ] 修改 `/chat` endpoint 使用 LangGraph 工作流
- [ ] 測試:輸入「我想去台北玩 2 天,喜歡老街跟小吃」,確認回傳完整行程

**驗收標準**:LangGraph 工作流能跑通,並行節點同時執行(用 print 驗證執行順序)。

---

### Phase 4:HITL 審核 + SSE 串流(Day 4)

**目標**:加入人工審核節點,讓使用者能修改行程;API 改成 SSE 即時回應。

**任務清單**:
- [ ] 建立 `app/agents/nodes/reviewer.py`:
  - 使用 LangGraph 的 `interrupt_before` 暫停工作流
  - 等待使用者回饋(透過 API 傳入)
  - 若使用者說「OK」→ 繼續到 final_output
  - 若使用者提出修改 → 回到 itinerary 節點重新生成
- [ ] 修改 `app/agents/graph.py` 加入條件分支:
  ```
  itinerary → reviewer (interrupt)
            → user_decision
            → if approved: final_output
            → if revision: back to itinerary
  ```
- [ ] 加入 LangGraph 的 `MemorySaver` 或 `SqliteSaver` 做 checkpoint
- [ ] 建立 SSE endpoint `/chat/stream`:
  - 使用 `StreamingResponse`
  - 邊跑工作流邊回傳每個節點的中間狀態
- [ ] 建立 `/chat/feedback` endpoint:
  - 接收 thread_id + feedback
  - 用 `graph.update_state` 更新狀態並 resume
- [ ] 測試完整流程:
  1. POST /chat/stream → 收到行程草稿
  2. POST /chat/feedback (feedback="把第 2 天的九份換成淡水") → 收到新行程
  3. POST /chat/feedback (feedback="OK") → 收到 final_output

**驗收標準**:HITL 流程能跑通,前端可以收到即時 SSE 串流。

---

### Phase 5:Docker 化 + README + 上 GitHub(Day 5)

**目標**:讓 HR 一鍵啟動,作品集 GitHub 一目了然。

**任務清單**:
- [ ] 寫 `Dockerfile`(Python 3.11-slim base,uv 安裝套件)
- [ ] 寫 `docker-compose.yml`:
  - `app` service(FastAPI)
  - `chromadb` service(可選,也可內建)
- [ ] 寫 `README.md`,結構:
  ```
  # Taiwan Travel Agent
  > 一句話定位
  
  ## 🎯 專案亮點
  - LangGraph 多步驟 Agent 工作流
  - 並行 RAG 檢索(景點/美食/交通)
  - Human-in-the-Loop 審核機制
  - SSE 即時串流回應
  
  ## 🏗️ 架構圖
  (放架構圖)
  
  ## 🚀 快速啟動
  ```bash
  cp .env.example .env
  # 填入 ANTHROPIC_API_KEY
  docker-compose up
  ```
  
  ## 📺 Demo
  (放 demo.gif)
  
  ## 🛠️ 技術棧
  | 用途 | 技術 |
  | LLM | Claude (Anthropic) |
  | Agent | LangGraph + LangChain |
  | RAG | ChromaDB |
  | Backend | FastAPI |
  
  ## 💡 實作細節
  - 為什麼用 LangGraph 而不是純 LangChain
  - HITL 怎麼透過 interrupt 實現
  - 並行節點的設計考量
  
  ## 🧪 範例
  (curl 範例)
  ```
- [ ] 錄一個 30 秒 demo 動畫(用 ScreenToGif 或 LICEcap),放進 README
- [ ] 推上 GitHub,把連結加到履歷與 LinkedIn
- [ ] 在 README 加一個 badge:`Built with Claude Code`(這對應徵 ecosTek 跟那家觀光公司是強加分)

**驗收標準**:陌生人 clone repo + 填 API key + `docker-compose up` 能直接跑起來。

---

## 🚨 常見踩坑警示

1. **LangGraph 並行節點要用 `add_edge` 從同一個源頭分出去**,不是 sequential。語法:
   ```python
   graph.add_edge("intent_parser", "attraction_rag")
   graph.add_edge("intent_parser", "food_rag")
   graph.add_edge("intent_parser", "transport")
   # 三個節點都要連到 itinerary
   graph.add_edge("attraction_rag", "itinerary")
   graph.add_edge("food_rag", "itinerary")
   graph.add_edge("transport", "itinerary")
   ```
   並行匯流時要注意 state 合併邏輯,可能需要 reducer。

2. **State 並行更新會衝突**:多個節點同時寫 state 時,要在 TypedDict 裡用 `Annotated[list, operator.add]` 處理 list 合併。

3. **HITL 的 interrupt 要搭配 checkpointer**:沒有 checkpointer 工作流不能 resume。MVP 用 `MemorySaver`,production 用 `SqliteSaver`。

4. **ChromaDB 在 Docker 裡的 persistence**:要 mount volume,否則容器重啟資料會消失。

5. **Claude API 的 structured output**:用 `tool_use` 強制 JSON schema 比 prompt engineering 穩定 10 倍。

6. **SSE 在 FastAPI**:用 `StreamingResponse(generator(), media_type="text/event-stream")`,記得每個 chunk 結尾加 `\n\n`。

7. **不要忘記 .gitignore**:`.env`、`__pycache__`、`chromadb_data/`、`*.db` 都要排除。

---

## 📊 給 HR 看的「亮點清單」(寫進 README)

- ✅ **多步驟 Agent Pipeline**:意圖解析 → 並行檢索 → 整合 → HITL → 輸出
- ✅ **LangGraph 並行工作流**:三個 RAG 節點同時執行,降低延遲
- ✅ **Human-in-the-Loop**:使用者可以審核並修改 Agent 輸出,展示 production-ready 的設計思維
- ✅ **混合檢索 + Reranking**:展示 RAG 工程化能力
- ✅ **SSE 即時串流**:前端體驗對標 ChatGPT
- ✅ **Docker 一鍵啟動**:展示部署素養
- ✅ **完全用 Claude Code CLI 開發**:對 AI-First 公司有強烈匹配訊號

---

## 🎤 面試話術腳本(預先準備)

當面試官問「你怎麼設計這個 Agent?」,標準回答:

> 我把它設計成五階段 pipeline:意圖解析、並行檢索、整合、HITL 審核、最終輸出。
>
> 並行檢索是用 LangGraph 的 fan-out/fan-in 設計,讓景點、美食、交通三個 RAG 同時跑,降低總延遲。
>
> HITL 是我特別放進去的——因為觀光行程是高個人化需求,單次生成很難滿足使用者,讓他能在中間 review 並修改,符合 production 場景的需求。
>
> RAG 我做了混合檢索:向量檢索找語意相似、關鍵字過濾(地區/標籤)做 hard filter,最後用 LLM 對 top-10 做 reranking。

當面試官問「為什麼用 LangGraph 不用純 LangChain?」:

> LangChain 的 chain 是線性的,但我的場景需要並行(三個 RAG)跟條件分支(HITL 後可能要回到 itinerary 節點重做)。LangGraph 的 StateGraph 對這種非線性工作流支援更好,而且 checkpoint 機制讓 HITL 的 resume 變得很乾淨。

---

## ⚠️ 開發紀律(請 Claude Code 嚴格遵守)

1. **每完成一個 Phase,更新 `PROGRESS.md`**,格式:
   ```
   ## Phase 1 ✅ 2026-XX-XX
   - [x] 環境搭建
   - [x] FastAPI 基礎
   - 卡點:無
   ```

2. **遇到不確定的技術選擇,先問使用者**,不要自己決定關鍵架構。

3. **每個檔案開頭加 docstring**,說明這個模組做什麼。

4. **不要過度工程化 MVP**:能跑就好,先做完整 5 個 Phase 再回頭優化。

5. **Commit 訊息格式**:`feat(phase-X): xxx` / `fix: xxx` / `docs: xxx`

6. **變數命名用英文,註解用繁體中文**(方便面試時 walk-through)。

7. **概念性問題不要自己回答**:遇到使用者問「為什麼」、「這是什麼」、「兩個方案差在哪」,提示他去 Claude Chat 討論,你專心實作。詳見 `CLAUDE.md`。

---

## 🎯 最終交付物

完成所有 Phase 後,你會得到:

1. ✅ 一個能跑的 GitHub repo
2. ✅ 一個 30 秒 demo 動畫
3. ✅ 一份對外 README
4. ✅ Docker 一鍵啟動
5. ✅ **可以寫進履歷與推薦信的具體成果**

履歷可以這樣寫:
> **Taiwan Travel Agent** | LangGraph + FastAPI + Claude API
> 多步驟 AI Agent 系統,實作意圖解析、並行 RAG 檢索、HITL 審核流程。
> 採用 LangGraph 設計併行工作流,FastAPI 實作 SSE 串流,Docker 一鍵部署。
> [GitHub Link]

---

**現在請從 Phase 1 開始,並建立 `PROGRESS.md` 追蹤進度。**
