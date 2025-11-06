import os
import json
from typing import Any, Dict, List

STORE_DIR = "ltm_store"
os.makedirs(STORE_DIR, exist_ok=True)

def _path_for(user_key: str) -> str:
    safe = user_key.replace("+", "p").replace(":", "_").replace("/", "_")
    return os.path.join(STORE_DIR, f"{safe}.json")

def mem0_get(user_key: str, limit: int = 50) -> List[Dict[str, Any]]:
    p = _path_for(user_key)
    if not os.path.exists(p):
        return []
    try:
        with open(p, "r", encoding="utf-8") as f:
            arr = json.load(f)
        return arr[-limit:]
    except Exception as e:
        print(f"mem0_get error for {user_key}: {e}")
        return []

def mem0_set(user_key: str, memory: Dict[str, Any]) -> bool:
    p = _path_for(user_key)
    arr = []
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                arr = json.load(f)
        except Exception:
            arr = []
    arr.append(memory)
    arr = arr[-1000:]
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(arr, f, ensure_ascii=False, indent=2, default=str)
        return True
    except Exception as e:
        print(f"mem0_set error for {user_key}: {e}")
        return False
