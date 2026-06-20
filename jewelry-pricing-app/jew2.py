import streamlit as st
import pandas as pd
from datetime import datetime
import io
import requests
import json
import base64
from bs4 import BeautifulSoup

# --- 頁面設定 ---
st.set_page_config(page_title="金工報價系統", layout="centered")

# --- 1. 價格與計算邏輯 ---
def calculate_jewelry_fee(w, m):
    """單件執模工費"""
    if w <= 0: return 0
    if w <= 0.5:  base = 400
    elif w <= 1.0: base = 600
    elif w <= 2.0: base = 800
    elif w <= 5.0: base = 1000
    elif w <= 10.0: base = 1300
    else: base = 1600
    return int(base * (1.3 if m == "白金" else 1.0))

def get_stone_price(w):
    if w <= 0: return 0
    if w <= 0.09: return 35
    if w <= 0.19: return 50
    if w <= 0.25: return 100
    if w <= 0.79: return 200
    if w <= 2.00: return 400
    if w <= 3.00: return 600
    return 800

def get_material_base_price(mat, g_sell, p_sell_pt):
    """依材質取得每錢的基本賣出價（不含損耗，損耗由使用者填入）"""
    if mat == "18K(750)":
        return g_sell * 0.75
    elif mat == "14K(585)":
        return g_sell * 0.585
    elif mat == "9K(375)":
        return g_sell * 0.375
    elif mat == "Pt950":
        return p_sell_pt
    return 0.0

@st.cache_data(ttl=300)  # 快取 5 分鐘，避免重複抓取
def fetch_allbeauty_prices():
    """
    從詮美珠寶抓取今日黃金條塊(台錢)售價 與 白金條塊售價
    回傳 (gold_sell, plat_sell, update_time, error_msg)
    """
    try:
        url = "https://www.allbeauty.com.tw/GoldPrice/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "zh-TW,zh;q=0.9",
            "Referer": "https://www.allbeauty.com.tw/",
        }
        resp = requests.get(url, headers=headers, timeout=8)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")

        # 找所有 <table>，逐一掃描含「台錢」且含「售價」的那行
        gold_sell = None
        plat_sell = None
        update_time = ""

        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = [td.get_text(strip=True).replace(",", "") for td in row.find_all(["td", "th"])]
                text = " ".join(cells)

                # 抓更新時間（含日期格式的列）
                if not update_time and any(c for c in cells if len(c) > 8 and "-" in c):
                    update_time = cells[0] if cells else ""

                # 黃金條塊台錢售價：該列包含「台錢」且黃金欄售價在前
                if "台錢" in text:
                    # 典型欄位順序：發佈時間 | 單位 | 黃金售價 | 黃金回收 | 白金售價 | 白金回收
                    # 找包含台錢的列，依序取數值
                    nums = []
                    for c in cells:
                        try:
                            nums.append(float(c))
                        except ValueError:
                            pass
                    if len(nums) >= 4:
                        gold_sell = int(nums[0])   # 黃金售價
                        plat_sell = int(nums[2])   # 白金售價

        if gold_sell and plat_sell:
            return gold_sell, plat_sell, update_time, None
        else:
            return None, None, "", "找不到金價資料，請確認網頁結構是否改變"

    except requests.exceptions.Timeout:
        return None, None, "", "連線逾時，請稍後再試"
    except Exception as e:
        return None, None, "", f"抓取失敗：{e}"

# --- GitHub JSON 永久儲存 ---
def _gh_headers():
    token = st.secrets.get("github", {}).get("token", "")
    return {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

def _gh_file_url():
    owner = st.secrets.get("github", {}).get("owner", "")
    repo  = st.secrets.get("github", {}).get("repo", "")
    path  = st.secrets.get("github", {}).get("path", "records.json")
    return f"https://api.github.com/repos/{owner}/{repo}/contents/{path}", path

def load_records_from_github():
    try:
        url, _ = _gh_file_url()
        r = requests.get(url, headers=_gh_headers(), timeout=8)
        if r.status_code == 404:
            return [], None          # 檔案尚未建立
        r.raise_for_status()
        data = r.json()
        sha      = data["sha"]
        content  = base64.b64decode(data["content"]).decode("utf-8")
        records  = json.loads(content)
        return records, sha
    except Exception:
        return [], None

def save_records_to_github(records, sha=None):
    try:
        url, path = _gh_file_url()
        content_b64 = base64.b64encode(json.dumps(records, ensure_ascii=False, indent=2).encode("utf-8")).decode("utf-8")
        payload = {
            "message": f"update records {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "content": content_b64,
        }
        if sha:
            payload["sha"] = sha
        r = requests.put(url, headers=_gh_headers(), json=payload, timeout=10)
        r.raise_for_status()
        # 更新 sha 以備下次使用
        st.session_state.gh_sha = r.json()["content"]["sha"]
        return True
    except Exception as e:
        return False

# --- 2. 初始化 Session State ---
if 'gold_price' not in st.session_state: st.session_state.gold_price = 0.0
if 'plat_price' not in st.session_state: st.session_state.plat_price = 0.0
if 'fetch_msg' not in st.session_state: st.session_state.fetch_msg = ""
if 'fetch_ok' not in st.session_state: st.session_state.fetch_ok = True
if 'gh_sha' not in st.session_state: st.session_state.gh_sha = None
if 'records_loaded' not in st.session_state:
    loaded, sha = load_records_from_github()
    st.session_state.records = loaded
    st.session_state.gh_sha  = sha
    st.session_state.records_loaded = True
if 'records' not in st.session_state: st.session_state.records = []

# 動態列數計數器
for _k, _d in [('gw_rows', 1), ('mold_rows', 1),
                ('diamond_rows', 1), ('gem_rows', 1), ('crystal_rows', 1),
                ('bare_rows', 1)]:
    if _k not in st.session_state: st.session_state[_k] = _d

# 預先初始化動態 widget key（最多支援 20 列），確保 reset 時不會觸發 NotAllowedError
_MAT_OPTS = ["18K(750)", "14K(585)", "9K(375)", "Pt950"]
_MOLD_OPTS = ["K金", "白金"]
for _i in range(20):
    for _k, _v in [
        (f'gw_mat_{_i}',  _MAT_OPTS[0]),
        (f'gw_w_{_i}',    0.0),
        (f'gw_loss_{_i}', 1.35),
        (f'mold_m_{_i}',  _MOLD_OPTS[0]),
        (f'mold_w_{_i}',  0.0),
        (f'sw_{_i}',      0.0),
        (f'sc_{_i}',      0),
        (f'sv_{_i}',      False),
        (f'clamp_{_i}',   False),
        (f'silver_{_i}',  False),
        (f'row_{_i}',     False),
        (f'gem_w_{_i}',   0.0),
        (f'gem_c_{_i}',   0),
        (f'gem_v_{_i}',   False),
        (f'cry_w_{_i}',   0.0),
        (f'cry_c_{_i}',   0),
        (f'cry_v_{_i}',   False),
        (f'cp_{_i}',      0.0),
        (f'cw_{_i}',      0.0),
        (f'ct_type_{_i}', "天然"),
    ]:
        if _k not in st.session_state:
            st.session_state[_k] = _v

# 若有重設旗標，在 widget 渲染前清除所有 state
if st.session_state.get('_do_reset', False):
    st.session_state['_do_reset'] = False
    keys_to_keep = {'gold_price', 'plat_price', 'records', 'fetch_msg', 'fetch_ok',
                    'gh_sha', 'records_loaded', '_do_reset',
                    'gw_rows', 'mold_rows', 'diamond_rows', 'gem_rows', 'crystal_rows', 'bare_rows'}
    widget_button_keys = {
        "add_gw","del_gw","add_mold","del_mold",
        "add_diamond","del_diamond","add_gem","del_gem",
        "add_crystal","del_crystal","add_bare","del_bare"
    }
    for key in list(st.session_state.keys()):
        if key in keys_to_keep or key in widget_button_keys:
            continue
        try:
            val = st.session_state[key]
            if isinstance(val, bool):            st.session_state[key] = False
            elif isinstance(val, (int, float)):  st.session_state[key] = 0.0
            elif isinstance(val, str):           st.session_state[key] = ""
        except Exception:
            pass
    st.session_state.eng_choice    = "無"
    st.session_state.polish_choice = "無"

def reset_fields():
    st.session_state['_do_reset'] = True

# 動態列數 callback（具名函數，避免 lambda 在部分 Streamlit 版本的問題）
def _add(k):    st.session_state[k] += 1
def _del(k):    st.session_state[k] = max(1, st.session_state[k] - 1)

def cb_add_gw():    _add('gw_rows')
def cb_del_gw():    _del('gw_rows')
def cb_add_mold():  _add('mold_rows')
def cb_del_mold():  _del('mold_rows')
def cb_add_dia():   _add('diamond_rows')
def cb_del_dia():   _del('diamond_rows')
def cb_add_gem():   _add('gem_rows')
def cb_del_gem():   _del('gem_rows')
def cb_add_cry():   _add('crystal_rows')
def cb_del_cry():   _del('crystal_rows')
def cb_add_bare():  _add('bare_rows')
def cb_del_bare():  _del('bare_rows')

# --- 3. UI 介面 ---
st.markdown("<h1 style='text-align: center;'>今日金價</h1>", unsafe_allow_html=True)

# 自動抓取按鈕
fetch_col, _ = st.columns([2, 3])
with fetch_col:
    if st.button("🔄 自動抓取詮美今日金價", use_container_width=True):
        with st.spinner("正在連線詮美珠寶..."):
            g_fetched, p_fetched, upd_time, err = fetch_allbeauty_prices()
        if err:
            st.session_state.fetch_msg = f"⚠️ {err}"
            st.session_state.fetch_ok = False
        else:
            st.session_state.gold_price = float(g_fetched)
            st.session_state.plat_price = float(p_fetched)
            st.session_state.fetch_msg = f"✅ 已更新！詮美報價時間：{upd_time}"
            st.session_state.fetch_ok = True
            fetch_allbeauty_prices.clear()  # 清快取，下次可重新抓
            st.rerun()

if st.session_state.fetch_msg:
    color = "#1a7a1a" if st.session_state.fetch_ok else "#a00"
    bg    = "#f0fff0" if st.session_state.fetch_ok else "#fff0f0"
    st.markdown(
        f"<div style='background:{bg};border-left:4px solid {color};padding:6px 12px;"
        f"border-radius:6px;color:{color};font-size:13px;margin-bottom:8px;'>"
        f"{st.session_state.fetch_msg}</div>",
        unsafe_allow_html=True
    )

col_p1, col_p2 = st.columns(2)
with col_p1: g_sell = st.number_input("黃金賣出價", value=st.session_state.gold_price, key='gold_price', step=10.0)
with col_p2: p_sell_pt = st.number_input("白金賣出價", value=st.session_state.plat_price, key='plat_price', step=10.0)

v18k = int(g_sell * 0.75 * 1.35)
v14k = int(g_sell * 0.585 * 1.35)
v9k  = int(g_sell * 0.375 * 1.35)
vpt  = int(p_sell_pt * 1.2)

st.markdown(
    f"""
    <div style="display: flex; justify-content: space-around; background-color: #f0f2f6; padding: 10px; border-radius: 10px; margin-bottom: 20px;">
        <span style="color: #D4AF37; font-weight: bold;">18K: {v18k}</span>
        <span style="color: #E5AA70; font-weight: bold;">14K: {v14k}</span>
        <span style="color: #c8a96e; font-weight: bold;">9K: {v9k}</span>
        <span style="color: #4682B4; font-weight: bold;">Pt950: {vpt}</span>
    </div>
    """, unsafe_allow_html=True
)

details = []
total_sum = 0

# A. 執模台工
with st.expander("🛠️ 執模台工", expanded=False):
    do_mold = st.checkbox("啟用執模服務", key='do_mold')
    sub_a_labor = 0
    sub_a_gold  = 0

    if do_mold:
        # ── 金重計算（動態列）──
        st.markdown("#### 💰 金重計算")
        st.caption("帶入黃金／白金賣出價，損耗倍率自行填入")

        gw_n = st.session_state.gw_rows
        gw_amts = []
        for i in range(gw_n):
            gc1, gc2, gc3, gc4 = st.columns([2, 2, 2, 2])
            mat  = gc1.selectbox("成色", ["18K(750)", "14K(585)", "9K(375)", "Pt950"], key=f'gw_mat_{i}')
            wt   = gc2.number_input("重量(錢)", min_value=0.0, step=0.001, format="%.3f", key=f'gw_w_{i}')
            loss = gc3.number_input("損耗", min_value=1.0, max_value=2.0, value=1.35, step=0.01, key=f'gw_loss_{i}')
            base = get_material_base_price(mat, g_sell, p_sell_pt)
            amt  = int(wt * int(base * loss))
            gc4.metric("金額", f"${amt}", help=f"單價/錢: ${int(base*loss)}")
            gw_amts.append((mat, wt, loss, amt))

        col_add_gw, col_del_gw = st.columns(2)
        col_add_gw.button("＋ 新增金料", key='add_gw', on_click=cb_add_gw)
        if gw_n > 1:
            col_del_gw.button("－ 移除最後一組", key='del_gw', on_click=cb_del_gw)

        sub_a_gold = sum(a[3] for a in gw_amts)
        st.markdown(
            f"<div style='background:#fff8e1;border-left:4px solid #D4AF37;padding:8px 14px;"
            f"border-radius:6px;margin:8px 0;color:#5a4000;'>"
            f"💰 <b>金重小計：${sub_a_gold}</b></div>", unsafe_allow_html=True)

        st.divider()

        # ── 執模工費（動態列）──
        st.markdown("#### 🔧 執模工費")
        mold_n = st.session_state.mold_rows
        mold_parts = []
        for i in range(mold_n):
            mc1, mc2 = st.columns([1, 2])
            mm = mc1.selectbox("材質", ["K金", "白金"], key=f'mold_m_{i}')
            mw = mc2.number_input("重量(錢)", min_value=0.0, step=0.001, format="%.3f", key=f'mold_w_{i}')
            mold_parts.append((mw, mm))

        col_add_m, col_del_m = st.columns(2)
        col_add_m.button("＋ 新增件數", key='add_mold', on_click=cb_add_mold)
        if mold_n > 1:
            col_del_m.button("－ 移除最後一件", key='del_mold', on_click=cb_del_mold)

        is_combo = False
        active_parts = [p for p in mold_parts if p[0] > 0]
        combo_fee = 0
        if len(active_parts) >= 2:
            combo_choice = st.radio(
                "🔗 組合件加價",
                ["無", "單邊組合 +$300", "雙邊組合 +$500"],
                key='mold_combo', horizontal=True
            )
            if "300" in combo_choice: combo_fee = 300
            elif "500" in combo_choice: combo_fee = 500

        # 每件各自計算工費後加總，再加組合費
        sub_a_labor = sum(calculate_jewelry_fee(p[0], p[1]) for p in mold_parts) + combo_fee

        mold_desc = "+".join(f"{p[1]}{p[0]:.3f}錢" for p in mold_parts if p[0] > 0)
        if combo_fee > 0: mold_desc += f"(組合件+${combo_fee})"

        st.markdown(
            f"<div style='background:#e8f4f8;border-left:4px solid #4682B4;padding:8px 14px;"
            f"border-radius:6px;margin:8px 0;color:#0d2e4a;'>"
            f"🔧 <b>執模工費小計：${sub_a_labor}</b></div>", unsafe_allow_html=True)

        if mold_desc:
            gw_detail = "+".join(f"{a[0]}{a[1]:.3f}錢×{a[2]}" for a in gw_amts if a[1] > 0)
            details.append(f"執模[{mold_desc}](工${sub_a_labor}|金{gw_detail}=${sub_a_gold})")

    sub_a_total = sub_a_labor + sub_a_gold
    st.divider()
    col_la, col_ga, col_ta = st.columns(3)
    col_la.metric("執模工費", f"${sub_a_labor}")
    col_ga.metric("金重費用", f"${sub_a_gold}")
    col_ta.metric("執模合計", f"${sub_a_total}")
    total_sum += sub_a_total

# B. 鑲嵌服務
with st.expander("💎 鑲嵌服務", expanded=False):
    sub_b = 0

    # 標鑲
    st.write("### 標鑲計算 (重量 × 顆數)")
    dn = st.session_state.diamond_rows
    for i in range(dn):
        c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
        sw = c1.number_input("重量(ct)", min_value=0.0, step=0.001, format="%.3f", key=f'sw_{i}')
        sc = c2.number_input("顆數", min_value=0, step=1, key=f'sc_{i}')

        if sc > 0 and sw > 0:
            base_price = get_stone_price(sw)

            if sw <= 0.09:
                # 0.09以下：特殊選項區
                opt_col1, opt_col2 = st.columns(2)
                is_clamp  = opt_col1.checkbox("夾鑲（$50/顆）", key=f'clamp_{i}')
                is_silver = opt_col1.checkbox("銀飾（$45/顆）", key=f'silver_{i}')
                is_row    = opt_col2.checkbox("排鑽位（+$15/顆）", key=f'row_{i}')
                # 夾鑲與造型爪互斥
                sv = False if is_clamp else c3.checkbox("造型爪+50", key=f'sv_{i}')
                if is_clamp:
                    unit = 50
                elif is_silver:
                    unit = 45
                else:
                    unit = base_price
                if is_row: unit += 15
                unit += (50 if sv else 0)
                p = unit * sc
                tag = "夾鑲" if is_clamp else ("銀飾" if is_silver else "標鑲")
                if is_row: tag += "+排鑽"
            else:
                sv = c3.checkbox("造型爪+50", key=f'sv_{i}')
                p = (base_price + (50 if sv else 0)) * sc
                tag = "標鑲"

            sub_b += p
            c4.metric("小計", f"${int(p)}")
            details.append(f"{tag}{sw:.3f}ct×{sc}(${int(p)})")
    col_add_d, col_del_d = st.columns(2)
    col_add_d.button("＋ 新增標鑲", key='add_diamond', on_click=cb_add_dia)
    if dn > 1:
        col_del_d.button("－ 移除", key='del_diamond', on_click=cb_del_dia)

    st.divider()

    # 寶石類
    st.write("### 寶石類 (紅藍寶、碧璽)")
    st.caption("≤5ct $400｜5~10ct $500｜>10ct $600")
    gn = st.session_state.gem_rows
    for i in range(gn):
        gs1, gs2, gs3, gs4 = st.columns([2, 2, 2, 2])
        g_w = gs1.number_input("重量(ct)", min_value=0.0, step=0.001, format="%.3f", key=f'gem_w_{i}')
        g_c = gs2.number_input("顆數", min_value=0, step=1, key=f'gem_c_{i}')
        g_v = gs3.checkbox("造型爪+50", key=f'gem_v_{i}')
        if g_c > 0 and g_w > 0:
            g_unit = 400 if g_w <= 5 else (500 if g_w <= 10 else 600)
            g_p = (g_unit + (50 if g_v else 0)) * g_c
            sub_b += g_p
            gs4.metric("小計", f"${g_p}")
            details.append(f"寶石鑲{g_w:.3f}ct×{g_c}(${g_p})")
    col_add_g, col_del_g = st.columns(2)
    col_add_g.button("＋ 新增寶石", key='add_gem', on_click=cb_add_gem)
    if gn > 1:
        col_del_g.button("－ 移除 ", key='del_gem', on_click=cb_del_gem)

    st.divider()

    # 水晶類
    st.write("### 水晶類")
    st.caption("≤5ct $300｜5~10ct $400｜>10ct $500")
    cn = st.session_state.crystal_rows
    for i in range(cn):
        cs1, cs2, cs3, cs4 = st.columns([2, 2, 2, 2])
        c_w = cs1.number_input("重量(ct)", min_value=0.0, step=0.001, format="%.3f", key=f'cry_w_{i}')
        c_c = cs2.number_input("顆數", min_value=0, step=1, key=f'cry_c_{i}')
        c_v = cs3.checkbox("造型爪+50", key=f'cry_v_{i}')
        if c_c > 0 and c_w > 0:
            c_unit = 300 if c_w <= 5 else (400 if c_w <= 10 else 500)
            c_p = (c_unit + (50 if c_v else 0)) * c_c
            sub_b += c_p
            cs4.metric("小計", f"${c_p}")
            details.append(f"水晶鑲{c_w:.3f}ct×{c_c}(${c_p})")
    col_add_c, col_del_c = st.columns(2)
    col_add_c.button("＋ 新增水晶", key='add_crystal', on_click=cb_add_cry)
    if cn > 1:
        col_del_c.button("－ 移除  ", key='del_crystal', on_click=cb_del_cry)

    st.divider()
    st.write("### 手動單價")
    mc1, mc2, mc3, mc4 = st.columns([2, 2, 2, 2])
    manual_p = mc1.number_input("手動單價", min_value=0.0, key='mp')
    manual_c = mc2.number_input("顆數", min_value=0, step=1, key='mc')
    manual_v = mc3.checkbox("造型爪+50", key='mv')
    if manual_c > 0:
        p_m = (manual_p + (50 if manual_v else 0)) * manual_c
        sub_b += p_m
        mc4.metric("小計", f"${int(p_m)}")
        details.append(f"手動鑲×{manual_c}")

    st.write(f"**鑲嵌小計: ${int(sub_b)}**")
    total_sum += sub_b

# B2. 裸石價格
with st.expander("💍 裸石價格", expanded=False):
    sub_b2 = 0
    st.write("### 克拉單價計算 (單價 × 總重)")
    bn = st.session_state.bare_rows
    for j in range(bn):
        cp_col, cw_col, ct_col, amt_col = st.columns([2, 2, 2, 2])
        cp = cp_col.number_input("單價/ct", min_value=0.0, key=f'cp_{j}')
        cw = cw_col.number_input("總重量(ct)", min_value=0.0, step=0.001, format="%.3f", key=f'cw_{j}')
        ct_type = ct_col.selectbox("類型", ["天然", "培育"], key=f'ct_type_{j}')
        if cp > 0 and cw > 0:
            amt = cp * cw
            sub_b2 += amt
            amt_col.metric("金額", f"${int(amt)}")
            details.append(f"裸石({ct_type}){cw:.3f}ct×${int(cp)}=${int(amt)}")
    col_add_b, col_del_b = st.columns(2)
    col_add_b.button("＋ 新增裸石", key='add_bare', on_click=cb_add_bare)
    if bn > 1:
        col_del_b.button("－ 移除   ", key='del_bare', on_click=cb_del_bare)
    st.write(f"**裸石小計: ${int(sub_b2)}**")
    total_sum += sub_b2

# C. 改圍加價
with st.expander("💍 改圍加價", expanded=False):
    do_resize = st.checkbox("啟用改圍 (基礎 $300)", key='do_resize')
    sub_c = 0
    if do_resize:
        sub_c = 300
        c1, c2 = st.columns(2)
        if c1.checkbox("白金 +100", key='r_plat'): sub_c += 100
        if c2.checkbox("寬版 +100", key='r_wide'): sub_c += 100
        if c1.checkbox("封底 +100", key='r_back'): sub_c += 100
        if c2.checkbox("拆石回鑲(珊瑚、珍珠) +100", key='r_full'): sub_c += 100
        if st.checkbox("改大 +200", key='r_big'):
            sub_c += 200
            rb1, rb2, rb3, rb4 = st.columns([2, 2, 2, 2])
            b_mat2 = rb1.selectbox("成色", ["18K(750)", "14K(585)", "9K(375)", "Pt950"], key='big_mat2')
            bw     = rb2.number_input("金料(錢)", min_value=0.0, step=0.001, format="%.3f", key='big_w')
            b_loss = rb3.number_input("損耗", min_value=1.0, max_value=2.0, value=1.35, step=0.01, key='big_loss')
            b_base = get_material_base_price(b_mat2, g_sell, p_sell_pt)
            b_unit = int(b_base * b_loss)
            b_amt  = int(bw * b_unit)
            rb4.metric("金料金額", f"${b_amt}", help=f"單價/錢: ${b_unit}")
            sub_c += b_amt
        details.append(f"改圍(${int(sub_c)})")
    st.write(f"**改圍小計: ${int(sub_c)}**")
    total_sum += sub_c

# D. 拋光 / 電鍍
with st.expander("✨ 拋光 / 電鍍", expanded=False):
    sub_d = 0

    # 主項目：單選（防呆）
    polish_choice = st.radio(
        "拋光項目",
        ["無",
         "局部拋光(單耳／單鑲口) $50",
         "局部拋光(戒指／墜子)、單耳、單鑲口 $100",
         "基礎拋光(戒指／墜子) $200",
         "項鍊／手鍊 $250",
         "手鐲 $300"],
        key='polish_choice'
    )

    if "$50" in polish_choice and "局部" in polish_choice:
        sub_d += 50
        if st.checkbox("附加電鍍 +$50", key='p_add_plate'):
            sub_d += 50
    elif "$100" in polish_choice:
        sub_d += 100
        if st.checkbox("附加電鍍 +$50", key='p_add_plate'):
            sub_d += 50
    elif "$200" in polish_choice:
        sub_d += 200
        if st.checkbox("附加電鍍 +$50", key='p_add_plate'):
            sub_d += 50
    elif "$250" in polish_choice:
        sub_d += 250
        if st.checkbox("附加電鍍 +$100", key='p_add_plate'):
            sub_d += 100
    elif "$300" in polish_choice:
        sub_d += 300
        if st.checkbox("附加電鍍 +$100", key='p_add_plate'):
            sub_d += 100

    st.divider()
    st.write("**其他電鍍選項**")

    ca1, ca2 = st.columns(2)
    if ca1.checkbox("純電鍍 $100", key='p_100'): sub_d += 100
    if ca2.checkbox("白金 +$50", key='p_white'): sub_d += 50
    if ca1.checkbox("大件 +$50", key='p_wide'): sub_d += 50
    if ca2.checkbox("過砂紙 +$50", key='p_sandpaper'): sub_d += 50
    if ca1.checkbox("雙色 +$100", key='p_double'): sub_d += 100
    if ca2.checkbox("拉砂 +$100", key='p_pull_sand'): sub_d += 100
    if ca1.checkbox("噴砂 +$100", key='p_sand'): sub_d += 100
    if ca2.checkbox("執模後粗拋 +$50", key='p_rough'): sub_d += 50

    st.divider()
    custom_plate = st.number_input("自訂電鍍金額 ($)", min_value=0, step=10, key='custom_plate')
    sub_d += custom_plate

    if sub_d > 0: details.append(f"拋光電鍍(${int(sub_d)})")
    st.write(f"**拋光電鍍小計: ${int(sub_d)}**")
    total_sum += sub_d

# E. 維修
with st.expander("🔨 維修", expanded=False):
    sub_e = 0
    col_e1, col_e2, col_e3 = st.columns(3)
    sub_e += col_e1.number_input("鈎鍊+雷射 ($100)", min_value=0, step=1, key='rep_c') * 100
    sub_e += col_e2.number_input("明火焊接 ($200)", min_value=0, step=1, key='rep_weld') * 200
    sub_e += col_e3.number_input("焊接自訂金額 ($)", min_value=0.0, step=10.0, key='entry_laser_fee')

    st.write("---")
    st.write("**黏耳針 / 補爪 ($150 + 金料)**")
    ce1, ce2, ce3, ce4, ce5 = st.columns([1, 2, 2, 2, 2])
    comb_q  = ce1.number_input("次數", min_value=0, step=1, key='comb_q')
    comb_m2 = ce2.selectbox("成色", ["18K(750)", "14K(585)", "9K(375)", "Pt950"], key='comb_m2')
    comb_w  = ce3.number_input("金料(錢)", min_value=0.0, step=0.001, format="%.3f", key='comb_w')
    comb_loss = ce4.number_input("損耗", min_value=1.0, max_value=2.0, value=1.35, step=0.01, key='comb_loss')
    comb_base = get_material_base_price(comb_m2, g_sell, p_sell_pt)
    comb_unit = int(comb_base * comb_loss)
    comb_gold_amt = int(comb_w * comb_unit)
    ce5.metric("金料金額", f"${comb_gold_amt}", help=f"單價/錢: ${comb_unit}")
    comb_labor = comb_q * 150
    sub_e += comb_labor + comb_gold_amt
    if comb_q > 0:
        details.append(f"補爪×{comb_q}({comb_m2}{comb_w:.3f}錢×{comb_loss},${comb_gold_amt})")

    st.write("---")
    st.write("**補金 ($自填工資 + 金料)**")
    le1, le2, le3, le4, le5 = st.columns([2, 2, 2, 2, 2])
    l_price   = le1.number_input("補金工資($)", min_value=0.0, step=10.0, key='laser_p')
    l_mat2    = le2.selectbox("成色", ["18K(750)", "14K(585)", "9K(375)", "Pt950"], key='laser_mat2')
    l_weight  = le3.number_input("金料(錢)", min_value=0.0, step=0.001, format="%.3f", key='laser_w')
    l_loss    = le4.number_input("損耗", min_value=1.0, max_value=2.0, value=1.35, step=0.01, key='laser_loss')
    l_base    = get_material_base_price(l_mat2, g_sell, p_sell_pt)
    l_unit    = int(l_base * l_loss)
    l_gold_amt = int(l_weight * l_unit)
    le5.metric("金料金額", f"${l_gold_amt}", help=f"單價/錢: ${l_unit}")
    sub_e += l_price + l_gold_amt
    if l_weight > 0 or l_price > 0:
        details.append(f"補金(工${int(l_price)},{l_mat2}{l_weight:.3f}錢×{l_loss},${l_gold_amt})")

    st.write("---")
    eng_choice = st.radio("刻字服務", ["無", "1-5字($50)", "6-12字($200)", "簡易向量圖($100)", "12字以上($400)"], key='eng_choice', horizontal=True)
    if "1-5" in eng_choice: sub_e += 50
    elif "6-12字" in eng_choice: sub_e += 200
    elif "向量" in eng_choice: sub_e += 100
    elif "12字以上" in eng_choice: sub_e += 400

    eng_custom = st.number_input("自訂刻字金額 ($)", min_value=0, step=50, key='eng_custom')
    sub_e += eng_custom

    if sub_e > 0: details.append(f"維修(${int(sub_e)})")
    st.write(f"**維修小計: ${int(sub_e)}**")
    total_sum += sub_e

# F. 3D 出蠟
with st.expander("🕯️ 3D 出蠟", expanded=False):
    sub_f = 0
    do_wax = st.checkbox("啟用 3D 出蠟", key='do_wax')
    if do_wax:
        wax_col1, wax_col2 = st.columns(2)
        wax_qty  = wax_col1.number_input("件數", min_value=1, step=1, key='wax_qty')
        wax_w    = wax_col2.number_input("蠟重 (克/件)", min_value=0.0, step=0.001, format="%.3f", key='wax_w')

        WAX_UNIT = 500
        DESIGN_FEE = 250

        wax_material = int(wax_w * WAX_UNIT * wax_qty)
        design_total = DESIGN_FEE * wax_qty if wax_w <= 1.5 and wax_w > 0 else 0
        sub_f = wax_material + design_total

        fee_note = f"蠟料 {wax_w:.3f}g×{wax_qty}件×${WAX_UNIT}/g = ${wax_material}"
        if design_total > 0:
            fee_note += f"　+ 圖面處理費 ${DESIGN_FEE}×{wax_qty}件 = ${design_total}"
        st.markdown(
            f"<div style='background:#f3f0ff;border-left:4px solid #7c5cbf;padding:8px 14px;"
            f"border-radius:6px;margin:8px 0;color:#2e1a5e;font-size:13px;'>"
            f"🕯️ {fee_note}</div>", unsafe_allow_html=True)
        if sub_f > 0:
            details.append(f"3D出蠟({wax_w:.3f}g×{wax_qty}件,${sub_f})")

    st.divider()
    scan_fee_check = st.checkbox("3D掃描 +$500", key='3d_scan')
    scan_fee = 500 if scan_fee_check else 0
    sub_f += scan_fee

    draw_fee = st.number_input("製圖金額 ($)", min_value=0, step=100, key='draw_fee')
    sub_f += draw_fee

    if scan_fee > 0: details.append(f"3D掃描(${scan_fee})")
    if draw_fee > 0: details.append(f"製圖(${draw_fee})")

    st.write(f"**3D出蠟小計: ${int(sub_f)}**")
    total_sum += sub_f

# 報價模式
st.divider()
pricing_mode = st.radio(
    "報價模式",
    ["一般報價（同業）", "零售維修報價（工費 ×2）", "零售新訂報價（分項倍率）"],
    key='pricing_mode', horizontal=True
)

is_retail_repair = (pricing_mode == "零售維修報價（工費 ×2）")
is_walkin        = (pricing_mode == "零售新訂報價（分項倍率）")

def walkin_loss_add(mat):
    """零售新訂模式下補金損耗加成"""
    if not is_walkin: return 0.0
    if mat == "Pt950": return 0.3
    return 0.25

# ── 計算各區塊金料（不加倍部分）──
resize_gold = 0
if st.session_state.get('do_resize', False) and st.session_state.get('r_big', False):
    bw_val     = st.session_state.get('big_w', 0.0)
    b_loss_val = st.session_state.get('big_loss', 1.35)
    b_mat2_val = st.session_state.get('big_mat2', '18K(750)')
    b_base_val = get_material_base_price(b_mat2_val, g_sell, p_sell_pt)
    resize_gold = int(bw_val * int(b_base_val * b_loss_val))

comb_w_val    = st.session_state.get('comb_w', 0.0)
comb_loss_val = st.session_state.get('comb_loss', 1.35)
comb_m2_val   = st.session_state.get('comb_m2', '18K(750)')
comb_base_val = get_material_base_price(comb_m2_val, g_sell, p_sell_pt)
comb_loss_eff = comb_loss_val + walkin_loss_add(comb_m2_val)
comb_gold_val = int(comb_w_val * int(comb_base_val * comb_loss_eff))

laser_w_val    = st.session_state.get('laser_w', 0.0)
laser_loss_val = st.session_state.get('laser_loss', 1.35)
laser_m2_val   = st.session_state.get('laser_mat2', '18K(750)')
laser_base_val = get_material_base_price(laser_m2_val, g_sell, p_sell_pt)
laser_loss_eff = laser_loss_val + walkin_loss_add(laser_m2_val)
laser_gold_val = int(laser_w_val * int(laser_base_val * laser_loss_eff))

repair_gold  = comb_gold_val + laser_gold_val
repair_labor = sub_e - (int(comb_w_val * int(comb_base_val * comb_loss_val)) +
                        int(laser_w_val * int(laser_base_val * laser_loss_val)))

wax_w_val    = st.session_state.get('wax_w', 0.0)
wax_qty_val  = st.session_state.get('wax_qty', 1)
do_wax_val   = st.session_state.get('do_wax', False)
scan_fee_val = 500 if st.session_state.get('3d_scan', False) else 0
draw_fee_val = st.session_state.get('draw_fee', 0)

# ── 零售維修報價：所有工費 ×2，金料不加倍 ──
if is_retail_repair:
    final_a  = int(sub_a_labor * 2) + sub_a_gold
    final_b  = int(sub_b * 2)
    final_b2 = int(sub_b2)
    final_c  = int((sub_c - resize_gold) * 2) + int(resize_gold)
    final_d  = int(sub_d * 2)
    final_e  = int(repair_labor * 2) + int(repair_gold)
    if do_wax_val:
        wax_mat_cost    = int(wax_w_val * 500 * wax_qty_val)
        design_fee_each = 250 * wax_qty_val if wax_w_val <= 1.5 and wax_w_val > 0 else 0
        final_f = wax_mat_cost + int(design_fee_each * 2)
    else:
        final_f = 0
    final_f += int(scan_fee_val * 2) + int(draw_fee_val * 2)

# ── 零售新訂報價：分項倍率 ──
elif is_walkin:
    final_a  = int(sub_a_labor * 3) + sub_a_gold
    final_b  = int(sub_b * 3)
    final_b2 = int(sub_b2)
    final_c  = int((sub_c - resize_gold) * 2.5) + int(resize_gold)
    final_d  = int(sub_d * 2.5)
    final_e  = int(repair_labor * 3) + int(repair_gold)
    if do_wax_val:
        wax_mat_cost    = int(wax_w_val * 500 * wax_qty_val)
        design_fee_each = 250 * wax_qty_val if wax_w_val <= 1.5 and wax_w_val > 0 else 0
        final_f = wax_mat_cost + int(design_fee_each * 2)
    else:
        final_f = 0
    final_f += int(scan_fee_val * 2) + int(draw_fee_val * 2)

# ── 一般報價：不加倍 ──
else:
    final_a  = sub_a_labor + sub_a_gold
    final_b  = int(sub_b)
    final_b2 = int(sub_b2)
    final_c  = int(sub_c)
    final_d  = int(sub_d)
    final_e  = int(sub_e)
    if do_wax_val:
        wax_mat_cost    = int(wax_w_val * 500 * wax_qty_val)
        design_fee_each = 250 * wax_qty_val if wax_w_val <= 1.5 and wax_w_val > 0 else 0
        final_f = wax_mat_cost + design_fee_each
    else:
        final_f = 0
    final_f += scan_fee_val + draw_fee_val

total_final = final_a + final_b + final_b2 + final_c + final_d + final_e + final_f

# 備註欄
note = st.text_area("📝 備註", key='note', height=80)

# 工時輸入
st.write("⏱️ **工時記錄**")
wt_col1, wt_col2 = st.columns(2)
work_min = wt_col1.number_input("工時（分鐘）", min_value=0, step=5, key='work_min')
if work_min > 0:
    wt_h = work_min // 60
    wt_m = work_min % 60
    if wt_h > 0 and wt_m > 0:
        wt_str = f"{wt_h} 小時 {wt_m} 分鐘"
    elif wt_h > 0:
        wt_str = f"{wt_h} 小時"
    else:
        wt_str = f"{wt_m} 分鐘"
    wt_col2.markdown(f"<div style='padding-top:28px;font-size:15px;'>= <b>{wt_str}</b></div>", unsafe_allow_html=True)

# ── 拆分工費 / 金料 ──
# 金料部分：sub_a_gold（執模金料）、resize_gold（改大金料）、repair_gold（補爪+補金金料）、裸石 sub_b2
total_gold   = sub_a_gold + int(resize_gold) + int(repair_gold) + int(sub_b2)
total_labor  = total_final - total_gold

st.divider()
if is_retail_repair:
    st.markdown(
        f"<div style='background:#fff8e1;border-left:4px solid #e6a817;padding:8px 14px;"
        f"border-radius:6px;margin:4px 0;color:#7a4a00;font-size:13px;'>"
        f"🔧 零售維修報價｜所有工費 ×2，金料不加倍"
        f"</div>", unsafe_allow_html=True
    )
elif is_walkin:
    st.markdown(
        f"<div style='background:#fff0f0;border-left:4px solid #e00;padding:8px 14px;"
        f"border-radius:6px;margin:4px 0;color:#7a0000;font-size:13px;'>"
        f"👤 零售新訂報價｜執模/鑲嵌/維修 ×3　改圍/電鍍 ×2.5　3D掃描/製圖 ×2　金料損耗+0.25（Pt+0.3）"
        f"</div>", unsafe_allow_html=True
    )

# 三欄金額顯示
col_lf, col_gf, col_tf = st.columns(3)
col_lf.metric("💼 工費金額", f"${int(total_labor)}")
col_gf.metric("💰 金料金額", f"${int(total_gold)}")
col_tf.metric("💎 總金額",   f"${int(total_final)}")
st.markdown(f"<h2 style='text-align: center; color: red;'>當前應收金額: ${int(total_final)}</h2>", unsafe_allow_html=True)

col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    if st.button("🔄 清除當前輸入", use_container_width=True):
        reset_fields()
        st.rerun()

with col_btn2:
    if st.button("➕ 將此筆加入紀錄", use_container_width=True):
        new_record = {
            "時間": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "黃金牌價": g_sell,
            "白金牌價": p_sell_pt,
            "工費金額": int(total_labor),
            "金料金額": int(total_gold),
            "總金額": int(total_final),
            "報價模式": "零售維修" if is_retail_repair else ("零售新訂" if is_walkin else "一般"),
            "工時": wt_str if work_min > 0 else "",
            "明細": " | ".join(details) if details else "無項目",
            "備註": note
        }
        st.session_state.records.append(new_record)
        ok = save_records_to_github(st.session_state.records, st.session_state.gh_sha)
        if ok:
            st.success("✅ 已加入紀錄並永久儲存至 GitHub！")
        else:
            st.warning("✅ 已加入本機紀錄，但 GitHub 同步失敗，請確認 Secrets 設定。")

# --- 5. 報價紀錄總表匯出 ---
if st.session_state.records:
    st.divider()
    st.write("### 📋 報價紀錄清單")
    df = pd.DataFrame(st.session_state.records)
    st.dataframe(df)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='報價紀錄')
    excel_data = output.getvalue()

    c_dl1, c_dl2 = st.columns(2)
    with c_dl1:
        st.download_button(
            label="📥 下載完整 Excel (.xlsx)",
            data=excel_data,
            file_name=f"報價總表_{datetime.now().strftime('%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedomain.spreadsheetml.sheet",
            use_container_width=True
        )
    with c_dl2:
        if st.button("🗑️ 清空所有紀錄", use_container_width=True):
            ok = save_records_to_github([], st.session_state.gh_sha)
            st.session_state.records = []
            if ok:
                st.success("🗑️ 已清空所有紀錄（GitHub 同步完成）")
            else:
                st.warning("本機已清空，但 GitHub 同步失敗，請確認 Secrets 設定。")
            st.rerun()
