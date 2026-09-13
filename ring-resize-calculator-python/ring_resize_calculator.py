import base64
import json
import math
import re
from datetime import datetime

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# 戒圍對照表（國際圍 → 內直徑 mm）含半號圍
# ---------------------------------------------------------------------------
INNER_DIAMETER_MM = {
    3: 12.8, 3.5: 13.0, 4: 13.2, 4.5: 13.5, 5: 13.8, 5.5: 14.0,
    6: 14.2, 6.5: 14.4, 7: 14.7, 7.5: 14.9, 8: 15.2, 8.5: 15.4,
    9: 15.7, 9.5: 15.9, 10: 16.2, 10.5: 16.5, 11: 16.6, 11.5: 16.9,
    12: 17.1, 12.5: 17.3, 13: 17.6, 13.5: 17.9, 14: 18.0, 14.5: 18.4,
    15: 18.7, 15.5: 18.9, 16: 19.1, 16.5: 19.3, 17: 19.7, 17.5: 20.0,
    18: 20.2, 18.5: 20.4, 19: 20.7, 19.5: 20.9, 20: 21.2, 20.5: 21.4,
    21: 21.7, 21.5: 22.0, 22: 22.3, 22.5: 22.5, 23: 22.7, 23.5: 23.0,
    24: 23.2, 24.5: 23.5,
}
SIZE_LIST = sorted(INNER_DIAMETER_MM.keys())

DENSITY = {"750": 15.6, "585": 13.2, "Pt950": 21.45}  # g/cm³, estimate
RATIO = {"750": 0.750, "585": 0.585, "Pt950": 0.950}
GRAMS_PER_QIAN = 3.75

# 與主系統 (jewOEM) 相同的 GitHub repo，紀錄另存成獨立檔案避免互相覆蓋
GITHUB_OWNER = "aurumartjewelry"
GITHUB_REPO = "jewOEM"
GITHUB_PATH = "ring_resize_records.json"
GITHUB_BRANCH = "main"


def format_size(s: float) -> str:
    return f"#{s:g}"


def circumference_mm(size: float) -> float:
    """由內直徑換算內圍周長（mm）。"""
    return INNER_DIAMETER_MM[size] * math.pi


# ---------------------------------------------------------------------------
# 金價自動抓取（詮美珠寶 allbeauty.com.tw「黃金條塊／白金條塊」售價，5 分鐘快取）
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def fetch_gold_price():
    """抓取黃金條塊、白金條塊的售價（單位：每台錢）。"""
    url = "https://allbeauty.com.tw/GoldPrice/index.php?mobile=no"
    resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    target_table = None
    for table in soup.find_all("table"):
        text = table.get_text()
        if "黃金條塊" in text and "白金條塊" in text:
            target_table = table
            break
    if target_table is None:
        return None

    table_text = target_table.get_text()
    time_match = re.search(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}", table_text)
    publish_time = time_match.group(0) if time_match else ""

    for row in target_table.find_all("tr"):
        cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
        if "台錢" in cells:
            numbers = []
            for c in cells:
                c_clean = c.replace(",", "")
                if re.fullmatch(r"-?\d+(\.\d+)?", c_clean):
                    numbers.append(float(c_clean))
            # 該列數值依序為：黃金售價,黃金回收,白金售價,白金回收,...
            if len(numbers) >= 3:
                return {
                    "time": publish_time,
                    "黃金條塊售價": numbers[0],
                    "白金條塊售價": numbers[2],
                }
    return None


# ---------------------------------------------------------------------------
# 紀錄儲存（GitHub API，與主系統 jewOEM 相同做法，含 SHA 追蹤）
# ---------------------------------------------------------------------------
def _github_headers():
    token = st.secrets.get("GITHUB_TOKEN", "")
    return {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}


def _github_contents_url():
    return f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{GITHUB_PATH}"


def load_records_from_github():
    """回傳 (records, sha)。檔案不存在時回傳 ([], None)。"""
    try:
        resp = requests.get(
            _github_contents_url(), headers=_github_headers(),
            params={"ref": GITHUB_BRANCH}, timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            content = base64.b64decode(data["content"]).decode("utf-8")
            records = json.loads(content) if content.strip() else []
            return records, data["sha"]
        if resp.status_code == 404:
            return [], None
        st.error(f"讀取 GitHub 紀錄失敗（{resp.status_code}）：{resp.text}")
        return [], None
    except requests.RequestException as e:
        st.error(f"讀取 GitHub 紀錄發生錯誤：{e}")
        return [], None


def save_records_to_github(records, sha):
    """寫回 GitHub，回傳新的 sha（失敗則回傳原本的 sha）。"""
    content_str = json.dumps(records, ensure_ascii=False, indent=2)
    payload = {
        "message": f"更新戒圍改大估算紀錄 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "content": base64.b64encode(content_str.encode("utf-8")).decode("utf-8"),
        "branch": GITHUB_BRANCH,
    }
    if sha:
        payload["sha"] = sha
    try:
        resp = requests.put(
            _github_contents_url(), headers=_github_headers(), json=payload, timeout=10,
        )
        if resp.status_code in (200, 201):
            return resp.json()["content"]["sha"]
        st.error(f"儲存到 GitHub 失敗（{resp.status_code}）：{resp.text}")
        return sha
    except requests.RequestException as e:
        st.error(f"儲存到 GitHub 發生錯誤：{e}")
        return sha


if "records" not in st.session_state:
    st.session_state.records, st.session_state.records_sha = load_records_from_github()


def add_record(entry: dict):
    st.session_state.records.insert(0, entry)
    st.session_state.records_sha = save_records_to_github(
        st.session_state.records, st.session_state.records_sha
    )


def apply_fetched_price():
    data = fetch_gold_price()
    if data:
        st.session_state["fetched_gold_data"] = data
        chosen = st.session_state.get("price_type", "黃金條塊售價")
        st.session_state["price"] = data[chosen]
    else:
        st.session_state["fetch_failed"] = True


# ---------------------------------------------------------------------------
# 頁面
# ---------------------------------------------------------------------------
st.set_page_config(page_title="戒圍改大補金估算器", page_icon="💍", layout="centered")

st.title("💍 戒圍改大補金估算器")
st.caption("台灣國際圍｜補料金料與金料成本估算")

st.subheader("輸入條件")

col1, col2 = st.columns(2)
with col1:
    fineness = st.selectbox("成色", ["750", "585", "Pt950"])
    to_size = st.selectbox(
        "改至戒圍", SIZE_LIST, index=SIZE_LIST.index(14), format_func=format_size
    )
with col2:
    st.write("")
    from_size = st.selectbox(
        "原戒圍", SIZE_LIST, index=SIZE_LIST.index(12), format_func=format_size
    )

col3, col4 = st.columns(2)
with col3:
    width = st.number_input("戒腳寬度（mm）", min_value=0.0, value=2.00, step=0.01, format="%.2f")
with col4:
    thickness = st.number_input("戒腳厚度（mm）", min_value=0.0, value=1.70, step=0.01, format="%.2f")

factor = st.number_input("加工係數", min_value=1.0, value=1.15, step=0.01, format="%.2f")

st.markdown("**金價（每錢）**")
pcol1, pcol2, pcol3 = st.columns([2, 2, 1])
with pcol1:
    price = st.number_input(
        "金價（每錢）", min_value=0.0, step=1.0, format="%.0f", key="price",
        label_visibility="collapsed",
    )
with pcol2:
    price_type = st.selectbox(
        "抓取價格類型", ["黃金條塊售價", "白金條塊售價"], key="price_type",
        label_visibility="collapsed",
    )
with pcol3:
    st.button("🔄 抓取金價", on_click=apply_fetched_price, use_container_width=True)

if st.session_state.get("fetch_failed"):
    st.warning("自動抓取金價失敗，請手動輸入金價。")
    st.session_state["fetch_failed"] = False
elif "fetched_gold_data" in st.session_state:
    d = st.session_state["fetched_gold_data"]
    st.caption(
        f"詮美珠寶 {d['time']} ｜黃金條塊售價 {d['黃金條塊售價']:,.0f}　"
        f"白金條塊售價 {d['白金條塊售價']:,.0f}　（每台錢）"
    )

st.divider()
st.subheader("估算結果")

valid = True
if to_size <= from_size:
    st.warning("請輸入改大的戒圍（改至戒圍需大於原戒圍）")
    valid = False
elif width <= 0 or thickness <= 0 or factor < 1:
    st.warning("請輸入有效的寬度、厚度與加工係數")
    valid = False

result = None
if valid:
    circ_from = circumference_mm(from_size)
    circ_to = circumference_mm(to_size)
    circ = circ_to - circ_from
    volume = width * thickness * circ
    tg = volume * DENSITY[fineness] / 1000
    rg = tg * factor
    tq = tg / GRAMS_PER_QIAN
    rq = rg / GRAMS_PER_QIAN

    r1c1, r1c2 = st.columns(2)
    r1c1.metric("原戒圍", format_size(from_size))
    r1c2.metric("改至戒圍", format_size(to_size))

    r2c1, r2c2 = st.columns(2)
    r2c1.metric("增加內圍長度", f"{circ:.2f} mm")
    r2c2.metric("增加圍數", f"{to_size - from_size:g} 號")

    r3c1, r3c2 = st.columns(2)
    r3c1.metric("理論成品增加重量", f"{tg:.3f} g（{tq:.3f} 錢）")
    r3c2.metric("建議投入補料金料", f"{rg:.3f} g（{rq:.3f} 錢）")

    if price <= 0:
        st.info("請輸入或抓取金價以估算金料成本")
    else:
        theoretical_cost = tq * price * RATIO[fineness]
        estimated_cost = rq * price * RATIO[fineness]
        r4c1, r4c2 = st.columns(2)
        r4c1.metric("理論成本（依理論重量）", f"{theoretical_cost:,.0f} 元")
        r4c2.metric("估算成本（依建議投入重量）", f"{estimated_cost:,.0f} 元")

        result = {
            "時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "成色": fineness,
            "原戒圍": format_size(from_size),
            "改至戒圍": format_size(to_size),
            "寬度mm": width,
            "厚度mm": thickness,
            "加工係數": factor,
            "金價": price,
            "理論重量g": round(tg, 3),
            "建議投入g": round(rg, 3),
            "理論成本": round(theoretical_cost, 0),
            "估算成本": round(estimated_cost, 0),
        }

    st.caption("理論成本 = 理論重量（錢）× 金價 × 成色比例｜估算成本 = 建議投入重量（錢）× 金價 × 成色比例")

    if result is not None:
        if st.button("💾 儲存本次估算紀錄"):
            add_record(result)
            st.success("已儲存紀錄")

st.divider()
hcol1, hcol2 = st.columns([4, 1])
with hcol1:
    st.subheader("歷史紀錄")
with hcol2:
    if st.button("🔄 重新載入"):
        st.session_state.records, st.session_state.records_sha = load_records_from_github()
        st.rerun()

if st.session_state.records:
    df = pd.DataFrame(st.session_state.records)
    st.dataframe(df, use_container_width=True, hide_index=True)
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "⬇️ 匯出 CSV",
            df.to_csv(index=False).encode("utf-8-sig"),
            file_name="ring_resize_records.csv",
            mime="text/csv",
        )
    with c2:
        if st.button("🗑️ 清空紀錄"):
            st.session_state.records = []
            st.session_state.records_sha = save_records_to_github([], st.session_state.records_sha)
            st.rerun()
else:
    st.caption("尚無紀錄")

st.divider()
st.caption(
    "注意：估算的是加工前投入補料金料，不是完成改圍後的實際增重。"
    "密度與加工係數可依實際案件持續校正。金價抓取來源：allbeauty.com.tw，僅供參考。"
    f"　紀錄儲存於 GitHub repo {GITHUB_OWNER}/{GITHUB_REPO}（{GITHUB_PATH}）。"
)
