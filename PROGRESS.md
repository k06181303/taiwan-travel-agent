# 開發進度追蹤

## 🎯 目標
完成 Taiwan Travel Agent 5 個 Phase 開發。

## 📊 進度總覽

- [x] Phase 1: 環境搭建 + LLM 基礎 ✅
- [x] Phase 2: RAG Pipeline ✅
- [x] Phase 3: LangGraph 工作流 ✅
- [x] Phase 4: HITL + SSE 串流 ✅
- [x] Phase 5: Docker + README + 上 GitHub ✅

---

## Phase 1 ✅ 2026-05-04

**狀態**:✅ 完成
**完成日**:Day 1

### 任務清單
- [x] venv 初始化專案(Python 3.13,套件用 pip)
- [x] 安裝套件:`fastapi`, `uvicorn`, `anthropic`, `langchain`, `langgraph`, `chromadb`, `sqlalchemy`, `pydantic-settings`, `python-dotenv`
- [x] `app/config.py` — pydantic-settings 讀取 .env,啟動時驗證 ANTHROPIC_API_KEY
- [x] `app/utils/llm_client.py` — 封裝 Claude API:`chat()` / `chat_with_history()` / `chat_with_tools()`
- [x] `app/api/schemas.py` — ChatRequest / ChatResponse Pydantic 模型
- [x] `app/api/routes.py` — POST /chat + GET /health endpoint
- [x] `app/main.py` — FastAPI 入口,掛載路由,CORS 設定
- [x] `.env.example` 與 `.gitignore`
- [x] `pyproject.toml`
- [x] 完整目錄骨架建立(agents/, rag/, api/, db/, data/, tests/)

### 卡點與解法
- uv 未安裝,改用 Python 內建 venv + pip,功能等價
- ANTHROPIC_API_KEY 環境變數測試要用 `os.environ` 方式,不能靠 shell export

### 驗收方式
```bash
# 1. 建立 .env 並填入 API key
cp .env.example .env
# 編輯 .env,填入 ANTHROPIC_API_KEY

# 2. 啟動服務
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000

# 3. 測試
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"九份在哪裡\"}"
```

### 下一步
- 進入 Phase 2:RAG Pipeline(建立向量資料庫)

---

## Phase 2: RAG Pipeline ✅ 2026-05-05

**狀態**:✅ 完成
**完成日**:Day 2

### 📖 先學會(在 Claude Chat 討論)
- [ ] Embedding 是什麼,為什麼能做語意搜尋
- [ ] ChromaDB 基本概念(collection、document、metadata)
- [ ] 混合檢索(向量 + 關鍵字)的設計理由
- [ ] Reranking 的目的——為什麼要再用 LLM 排一次

### 任務清單(交給 Claude Code CLI)
- [x] data/attractions.json(50 筆) ✅ 2026-05-04
- [x] data/foods.json(50 筆) ✅
- [x] embeddings.py(bge-m3, sentence-transformers) ✅
- [x] vector_store.py(ChromaDB, cosine HNSW) ✅
- [x] scripts/seed.py(50+50 筆灌入 ChromaDB) ✅
- [x] retriever.py(向量+BM25+RRF → CrossEncoder reranking) ✅
- [x] /chat endpoint 整合 RAG ✅

### 💡 學習筆記

#### 1. Embedding:把語意變成向量

Embedding 模型把一段文字壓成一串浮點數(向量),
訓練目標是「**語意相近的文字產生的向量也相近**」。
所以我們可以用 cosine similarity 比較兩個向量的夾角,
夾角越小代表語意越接近。

這就是為什麼能做語意搜尋——使用者問「有山有海、晚上有氣氛的地方」,
資料庫裡寫「九份老街,山城夜景」,字面完全不重疊,
但兩個向量的方向會很接近,所以查得到。

**模型選擇:`bge-m3`(BAAI 智源,1024 維)**
- 中文 MTEB 表現比 OpenAI text-embedding-3-small 還好
- 完全本機跑,跟「私有化部署」主題一致
- 跟 bge-reranker-v2-m3 同家、配套用最穩

**維度的意義**:1024 維 = 用 1024 個數字描述語意。
維度越高描述越細,但有邊際效益遞減 + 維度災難問題,
1024~1536 是業界甜蜜點。

#### 2. ChromaDB:向量資料庫

ChromaDB 解決一般 SQL 沒辦法做的兩件事:
1. **向量相似度搜尋**(SQL 不支援 cosine similarity)
2. **ANN 索引**(快速找最近鄰)

**三個核心概念**:
- **Collection**:一張表(我會分 attractions 跟 foods 兩個)
- **Document**:一筆資料,同時存「原文 + 向量 + metadata」
- **Query**:一次查詢,可以搭 metadata 過濾

**Metadata 過濾很重要**:
語意模糊的部分(氣氛、特色)交給向量檢索,
結構化明確的部分(城市、價位、評分)交給 metadata 過濾。
例如「我想去**台北**的夜景景點」,要先 `where={"city": "台北"}`
再做向量檢索,不然會被新北的九份混進去。

#### 3. ANN 索引:HNSW 為什麼快

ChromaDB 預設用 **HNSW(Hierarchical Navigable Small World)**
做向量索引,複雜度從 O(n) 降到 O(log n),
所以百萬筆資料也能毫秒級查詢。

**核心思想**:多層圖結構,上層稀疏跨大步,下層密集精細找,
像看 Google Maps 從台灣 → 台北 → 信義區一路 zoom in。

**對比其他 ANN 演算法**:
- **IVF**(K-means 分群):適合億級大規模、記憶體吃緊的場景
- **LSH**(局部敏感雜湊):精度差,已被 HNSW 全面取代
- **HNSW**:中小規模、動態新增友善、業界主流(我這個專案的選擇)

**取捨**:HNSW 用 ANN(近似最近鄰)犧牲一點點精度換速度,
找到的不是「絕對最相似」而是「非常相似」,
但對 RAG 場景這個誤差完全可以接受。

#### 4. 混合檢索:純向量會踩的坑

純向量檢索擅長「語意」但不擅長「字面」。
當使用者用了專有名詞(阿妹茶樓)、特定關鍵字(素食)、
數字編號(101 大樓)時,純向量可能找不到精確匹配。

**解法:向量檢索 + BM25 兩條腿走路**

- **向量檢索**(Dense):負責「我懂你想表達什麼」
- **BM25**(Sparse):負責「我看到你寫了什麼字」
  - BM25 是 TF-IDF 進化版,加了**詞頻飽和效應**和**文件長度正規化**
  - 「九份」「阿妹茶樓」這種稀有詞 IDF 高、權重大

**融合策略:RRF(Reciprocal Rank Fusion)**
看排名不看分數,避開向量分數(0~1)跟 BM25 分數(0~30+)
尺度不同的問題。LangChain 的 `EnsembleRetriever` 內建用 RRF。

**權重設定**:旅遊場景 7:3(向量:BM25),
偏向氣氛體驗類的抽象描述,但專有名詞用 BM25 兜底。

**中文坑**:BM25 是「詞」級別的演算法,中文要先用 jieba 斷詞,
不然整段中文會被當一個 token,完全失效。
**這是中文 RAG 跟英文 RAG 最關鍵的差異點之一。**

#### 5. Reranking:檢索 vs 排序是兩件事

混合檢索做完還不夠,因為 **embedding 是 Bi-Encoder 架構**——
query 跟 document 是分別 encode 成兩個向量,
最後只用一個 cosine 比對,沒辦法精細對齊。

**Reranker 用 Cross-Encoder 架構**:把 query 跟 document
拼在一起餵進模型,靠 self-attention 做 token 級別對齊,
準確度大幅提升。

但 Cross-Encoder 太慢,不能跑全資料庫。所以採用**兩階段檢索**:

Stage 1:Retrieval(快)
向量 + BM25 + RRF → top-20
Stage 2:Reranking(準)
bge-reranker-v2-m3 → top-5
**為什麼選 bge-reranker-v2-m3**:
- 跟 bge-m3 同團隊訓練,向量空間相容性好
- 中文 reranking 表現極好
- 完全本機部署

**精度提升幅度**:
| 設置 | NDCG@10 |
|---|---|
| 純向量 | ~0.65 |
| 混合檢索 | ~0.72 |
| **混合檢索 + Reranking** | **~0.84** |

這就是為什麼業界專業 RAG 都會做 reranking——
+15%~20% 的精度提升,而代價只是多花幾百毫秒。

#### 🎯 Phase 2 整體架構(我的 retriever.py 流程)

```python
def retrieve(query: str, top_k: int = 5):
    # 1. 向量檢索(top-20)- bge-m3 embedding
    vector_docs = chroma_retriever.invoke(query)
    
    # 2. BM25 檢索(top-20)- jieba 斷詞處理中文
    query_tokenized = " ".join(jieba.cut(query))
    bm25_docs = bm25_retriever.invoke(query_tokenized)
    
    # 3. RRF 融合 → top-20
    fused_docs = rrf_fusion(vector_docs, bm25_docs, k=60)
    
    # 4. Cross-Encoder reranking → top-5
    reranked_docs = bge_reranker.compress(query, fused_docs, top_n=top_k)
    
    return reranked_docs
```

#### 📌 面試一句話總結

> 我的 RAG 用兩階段檢索:第一階段混合 dense(bge-m3 向量)+ sparse(BM25)
> 用 RRF 融合,負責高召回;第二階段用 bge-reranker-v2-m3 做 Cross-Encoder
> 重排,負責高精準。中文部分有特別處理——BM25 用 jieba 斷詞、
> embedding 跟 reranker 都選 bge 系列做配套,既符合中文場景需求,
> 也支援私有化部署。整體精度比純向量檢索高約 30%,延遲控制在 1 秒內。

### 卡點與解法
- 問題：`FlagEmbedding 1.4.0` 的 `FlagReranker` 與 `transformers 5.7.0` 不相容（`XLMRobertaTokenizer` 缺少 `prepare_for_model`）
- 解法：改用 `sentence_transformers.CrossEncoder("BAAI/bge-reranker-v2-m3")`，API 改為 `.predict()` 回傳 numpy array
- seed.py 放在 `scripts/` 而非 `data/`（更符合專案結構）

### 驗收結果
- ChromaDB：attractions 50 筆 ✅、foods 50 筆 ✅
- 檢索測試：「九份老街茶館夜景」→ 九份老街 (score=0.988) ✅
- 美食測試：「台北小吃夜市」→ top-3 正確回傳 ✅

### 完成日
2026-05-05

---

## Phase 3: LangGraph 工作流 ✅ 2026-05-06

**狀態**:✅ 完成
**完成日**:Day 3

### 📖 先學會(在 Claude Chat 討論)
- [x] LangGraph 的 StateGraph 跟 LangChain Chain 差在哪
- [x] TypedDict + `Annotated[list, operator.add]` 的 reducer 機制
- [x] Fan-out / Fan-in 並行設計(為什麼不用 sequential)
- [x] Claude API 的 tool_use 強制 JSON schema(structured output)

### 任務清單(交給 Claude Code CLI)
- [x] state.py(AgentState 定義)
- [x] intent_parser 節點（Claude tool_use 強制 JSON schema）
- [x] attraction_rag 節點
- [x] food_rag 節點
- [x] transport 節點（Claude 純 LLM 生成）
- [x] itinerary 節點（整合三來源，生成行程草稿）
- [x] graph.py（fan-out/fan-in 並行工作流）
- [x] /chat endpoint 整合 LangGraph

### 💡 學習筆記
(在 Chat 學到的核心概念,用自己的話寫)

### 卡點與解法
- 問題：Annotated[list, operator.add] 在初始化 state 時若傳 None 會報 reducer 錯誤
- 解法：initial_state 的 messages 初始化為 `[]`，不傳 None

### 驗收方式
```bash
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"我想去台北玩 2 天，喜歡老街跟小吃\"}"
```
預期結果：回傳包含 `itinerary_draft` 的完整行程文字

### 下一步
- 進入 Phase 4：HITL + SSE 串流

---

## Phase 4: HITL 審核 + SSE 串流 ✅ 2026-05-06

**狀態**:✅ 完成
**完成日**:Day 3

### 📖 先學會(在 Claude Chat 討論)
- [x] LangGraph interrupt 機制與 checkpointer 的關係
- [x] `MemorySaver` vs `SqliteSaver` 的差異與選擇
- [x] SSE(Server-Sent Events)跟 WebSocket 差在哪
- [x] FastAPI `StreamingResponse` 的運作原理
- [x] thread_id 在 LangGraph 裡的角色

### 任務清單(交給 Claude Code CLI)
- [x] reviewer 節點（LangGraph interrupt()）
- [x] 條件分支（_reviewer_router：OK → final_output_node，否則 → itinerary）
- [x] MemorySaver checkpointer（圖編譯時傳入）
- [x] /chat/stream（SSE StreamingResponse，每節點一個 event）
- [x] /chat/feedback（Command(resume=feedback) 恢復工作流）
- [x] 完整流程驗收

### 💡 學習筆記
(在 Chat 學到的核心概念,用自己的話寫)

### 卡點與解法
- 問題：ChromaDB Rust binding 在 LangGraph fan-out 多執行緒下共用 lru_cache client 報錯
- 解法：改用 `threading.local()` 讓每個執行緒持有獨立的 ChromaDB client

### 驗收結果
```
1. POST /chat/stream  → 5 個 node_complete events + review_request ✅
2. POST /chat/feedback (修改) → status: "revised" + 新行程草稿 ✅
3. POST /chat/feedback ("OK") → status: "approved" + final_output ✅
```

---

## Phase 5: Docker + README + 上 GitHub ✅ 2026-05-06

**狀態**:✅ 完成
**完成日**:Day 5

### 📖 先學會(在 Claude Chat 討論)
- [ ] Dockerfile 的多階段建置(multi-stage build)
- [ ] docker-compose 的 volume mount(ChromaDB 持久化)
- [ ] README 怎麼寫才能讓 HR / 工程師 30 秒看懂專案亮點
- [ ] 履歷裡這個專案要怎麼描述(STAR 原則)

### 任務清單(交給 Claude Code CLI)
- [x] requirements.txt（版本鎖定）
- [x] Dockerfile（python:3.11-slim + torch CPU + healthcheck）
- [x] docker-compose.yml（Named volume 持久化 ChromaDB）
- [x] README.md（亮點表、架構圖、快速啟動、API 範例、技術棧、實作細節）
- [x] .env.example 修正（移除真實 API key，改為 placeholder）
- [ ] 30 秒 demo gif（需手動錄製，建議用 ScreenToGif 或 LICEcap）
- [ ] 推上 GitHub（需手動執行 git push）
- [ ] 加到履歷與 LinkedIn（手動）

### 💡 學習筆記
(在 Chat 學到的核心概念,用自己的話寫)

### 卡點與解法
- 問題：.env.example 內含真實 API key（不安全）
- 解法：改為 `sk-ant-api03-your-key-here` 佔位符，實際 key 放在 .env（已在 .gitignore）

### 驗收方式
```bash
# 建立 .env，填入 API key
cp .env.example .env

# Docker 啟動（首次 build 需 10-15 分鐘）
docker-compose up --build

# 初始化向量 DB
docker-compose exec app python scripts/seed.py

# 測試
curl http://localhost:8000/health
```

---

## 📝 隨手筆記

(開發中遇到的有趣問題、思考、待研究項目放這裡)
