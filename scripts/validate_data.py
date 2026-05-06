"""
scripts/validate_data.py

讀取 data/attractions.json 與 data/foods.json,
用 Pydantic schema 逐筆驗證,並印出統計報告。
執行方式:python scripts/validate_data.py
"""

import io
import json
import sys
from collections import Counter
from pathlib import Path

# Windows 終端機強制 UTF-8 輸出,避免 cp950 無法顯示特殊符號
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ─── 路徑設定 ───────────────────────────────────────────
# 從 scripts/ 往上一層找到專案根目錄
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
sys.path.insert(0, str(ROOT))  # 讓 Python 能找到 app 套件

from pydantic import ValidationError

from app.db.schemas import Attraction, Food

# ─── 顏色輸出 ───────────────────────────────────────────
GREEN = "\033[92m"
RED   = "\033[91m"
YELLOW = "\033[93m"
CYAN  = "\033[96m"
RESET = "\033[0m"

def ok(msg: str) -> str:
    return f"{GREEN}✅ {msg}{RESET}"

def err(msg: str) -> str:
    return f"{RED}❌ {msg}{RESET}"

def warn(msg: str) -> str:
    return f"{YELLOW}⚠️  {msg}{RESET}"

def header(msg: str) -> str:
    return f"{CYAN}{msg}{RESET}"


# ─── 通用驗證函式 ───────────────────────────────────────

def validate_file(
    filepath: Path,
    model,
    id_field: str = "id",
    rating_range: tuple = (3.8, 4.7),
) -> dict:
    """
    讀取 JSON 陣列並逐筆用 Pydantic model 驗證。
    回傳統計結果 dict。
    """
    if not filepath.exists():
        print(err(f"{filepath.name} 不存在,跳過"))
        return {}

    raw: list[dict] = json.loads(filepath.read_text(encoding="utf-8"))
    total = len(raw)
    passed = 0
    failed = 0
    errors: list[str] = []

    ids_seen: set[str] = set()
    cities: list[str] = []
    types_or_cats: list[str] = []

    for item in raw:
        item_id = item.get(id_field, "?")

        # id 重複檢查
        if item_id in ids_seen:
            errors.append(f"[{item_id}] id 重複")
            failed += 1
            continue
        ids_seen.add(item_id)

        # Pydantic schema 驗證
        try:
            obj = model(**item)
        except ValidationError as e:
            failed += 1
            for err_info in e.errors():
                loc = " → ".join(str(x) for x in err_info["loc"])
                errors.append(f"[{item_id}] {loc}: {err_info['msg']}")
            continue

        # 額外數值範圍檢查(不在 Pydantic 裡的業務規則)
        lo, hi = rating_range
        if not (lo <= obj.rating <= hi):
            errors.append(
                f"[{item_id}] rating={obj.rating} 超出建議範圍 {lo}~{hi}"
            )
            failed += 1
            continue

        # 蒐集分布資料
        cities.append(obj.city)
        if hasattr(obj, "type"):
            types_or_cats.append(obj.type.value)
        elif hasattr(obj, "category"):
            types_or_cats.append(obj.category.value)

        passed += 1

    return {
        "filename": filepath.name,
        "total": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "cities": cities,
        "types_or_cats": types_or_cats,
    }


def print_report(result: dict, type_label: str = "類型") -> None:
    """印出單一檔案的驗證報告"""
    if not result:
        return

    print(f"\n[{result['filename']}]")
    print(f"  總筆數:{result['total']}")
    print(ok(f"通過:{result['passed']}"))
    if result["failed"]:
        print(err(f"失敗:{result['failed']}"))
        for e in result["errors"]:
            print(f"    {RED}→ {e}{RESET}")
    else:
        print(ok("失敗:0"))

    print(f"\n  縣市分布:")
    for city, count in sorted(Counter(result["cities"]).items(), key=lambda x: -x[1]):
        print(f"    {city}:{count}")

    print(f"\n  {type_label}分布:")
    for t, count in sorted(Counter(result["types_or_cats"]).items(), key=lambda x: -x[1]):
        print(f"    {t}:{count}")


# ─── 主程式 ────────────────────────────────────────────

def main() -> None:
    print(header("=" * 40))
    print(header("  資料驗證報告"))
    print(header("=" * 40))

    # 驗證景點
    attr_result = validate_file(
        DATA_DIR / "attractions.json",
        model=Attraction,
        rating_range=(3.8, 4.7),
    )
    print_report(attr_result, type_label="景點類型")

    # 驗證美食
    food_result = validate_file(
        DATA_DIR / "foods.json",
        model=Food,
        rating_range=(3.8, 4.7),
    )
    print_report(food_result, type_label="美食類別")

    print(header("\n" + "=" * 40))

    # 整體是否通過
    total_failed = attr_result.get("failed", 0) + food_result.get("failed", 0)
    if total_failed == 0:
        print(ok("所有資料驗證通過！可以進行下一步。"))
    else:
        print(err(f"共 {total_failed} 筆驗證失敗,請修正後重跑。"))
        sys.exit(1)


if __name__ == "__main__":
    main()
