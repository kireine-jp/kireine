"""Instagram の自分の投稿一覧を取る共通関数。
フィールド指定で 400 が返ることがあるので、少ないフィールドへ順に落として再試行し、エラー本文をログに出す。"""
import json, sys, urllib.error, urllib.parse, urllib.request

API = "https://graph.instagram.com/v26.0"
FIELD_SETS = [
    "id,caption,permalink,timestamp,media_type,media_product_type",
    "id,caption,permalink,timestamp,media_type",
    "id,caption,permalink,timestamp",
]

def list_media(user_id, token, limit=25):
    last = ""
    for path in (f"{user_id}/media", "me/media"):
        for fields in FIELD_SETS:
            q = urllib.parse.urlencode({"fields": fields, "limit": limit, "access_token": token})
            try:
                with urllib.request.urlopen(f"{API}/{path}?{q}", timeout=60) as r:
                    return json.load(r).get("data", [])
            except urllib.error.HTTPError as e:
                last = f"{e.code} {e.read().decode(errors='replace')[:400]}"
                print(f"::warning::media list failed ({path}, fields={fields}): {last}", file=sys.stderr)
    raise RuntimeError(f"media list failed: {last}")

def is_reel(m):
    if m.get("media_product_type"):
        return m["media_product_type"] == "REELS"
    return m.get("media_type") == "VIDEO"
