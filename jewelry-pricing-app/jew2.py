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
def calculate_jewelry_fee(w1, m1, w2, m2, is_combo):
    """執模台工費：包含兩件重量與材質，勾選組合件才加 $500"""
    def get_base(w):
        if w <= 0: return 0
        if w <= 0.5: return 350
        elif w <= 1.0: return 500
        elif w <= 2.0: return 800
        else: return 1000

    fee1 = get_base(w1) * (1.3 if m1 == "白金" else 1.0)
    fee2 = get_base(w2) * (1.3 if m2 == "白金" else 1.0)
    total_fee = fee1 + fee2
    if is_combo and w1 > 0 and w2 > 0:
        total_fee += 500
    return int(total_fee)

def get_stone_price(w):
    if w <= 0: return 0
    if w <= 0.09: return 35
    if w <= 0.19: return 50
    if w <= 0.29: return 100
    if w <= 0.79: return 200
    if w <= 2.00: return 400
    if w <= 3.00: return 600
    return 800

def get_material_base_price(mat, g_sell, p_sell_pt):
    """依材質取得每錢的基本賣出價（不含損耗，損耗由使用者填入）"""
    if mat == "750":
        return g_sell * 0.75
    elif mat == "585":
        return g_sell * 0.585
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

def reset_fields():
    keys_to_keep = ['gold_price', 'plat_price', 'records', 'fetch_msg', 'fetch_ok',
                    'gh_sha', 'records_loaded']
    for key in list(st.session_state.keys()):
        if key not in keys_to_keep:
            val = st.session_state[key]
            if isinstance(val, bool): st.session_state[key] = False
            elif isinstance(val, (int, float)): st.session_state[key] = 0.0
            elif isinstance(val, str): st.session_state[key] = ""
    st.session_state.mold_m1 = "K金"; st.session_state.mold_m2 = "K金"
    st.session_state.eng_choice = "無"; st.session_state.big_mat = "金"
    st.session_state.comb_m = "金"; st.session_state.laser_m = "金"
    st.session_state.gw_mat1 = "750"; st.session_state.gw_mat2 = "750"

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

v750 = int(g_sell * 0.75 * 1.3)
v585 = int(g_sell * 0.585 * 1.3)
vpt = int(p_sell_pt * 1.25)  # 牌價顯示用 1.25

st.markdown(
    f"""
    <div style="display: flex; justify-content: space-around; background-color: #f0f2f6; padding: 10px; border-radius: 10px; margin-bottom: 20px;">
        <span style="color: #D4AF37; font-weight: bold;">750: {v750}</span>
        <span style="color: #E5AA70; font-weight: bold;">585: {v585}</span>
        <span style="color: #4682B4; font-weight: bold;">Pt950: {vpt}</span>
    </div>
    """, unsafe_allow_html=True
)

details = []
total_sum = 0

# A. 執模台工
with st.expander("🛠️ 執模台工", expanded=False):
    do_mold = st.checkbox("啟用執模服務", key='do_mold')
    sub_a_labor = 0   # 執模工費
    sub_a_gold = 0    # 金重金額

    if do_mold:

        # ── 金重計算區（兩組） ──────────────────────────────────
        st.markdown("#### 💰 金重計算")
        st.caption("帶入黃金／白金賣出價，損耗倍率自行填入，計算金料費用")

        # 組 A
        gw_col1, gw_col2, gw_col3, gw_col4 = st.columns([2, 2, 2, 2])
        gw_mat1  = gw_col1.selectbox("材質 A", ["750", "585", "Pt950"], key='gw_mat1')
        gw_w1    = gw_col2.number_input("重量 A (錢)", min_value=0.0, step=0.001, format="%.3f", key='gw_w1')
        gw_loss1 = gw_col3.number_input("損耗 A", min_value=1.0, max_value=2.0, value=1.3, step=0.01, key='gw_loss1')
        base1    = get_material_base_price(gw_mat1, g_sell, p_sell_pt)
        unit_price1 = int(base1 * gw_loss1)
        gw_amt1  = int(gw_w1 * unit_price1)
        gw_col4.metric("金額 A", f"${gw_amt1}", help=f"單價/錢: ${unit_price1}")

        # 組 B
        gw_col5, gw_col6, gw_col7, gw_col8 = st.columns([2, 2, 2, 2])
        gw_mat2  = gw_col5.selectbox("材質 B", ["750", "585", "Pt950"], key='gw_mat2')
        gw_w2    = gw_col6.number_input("重量 B (錢)", min_value=0.0, step=0.001, format="%.3f", key='gw_w2')
        gw_loss2 = gw_col7.number_input("損耗 B", min_value=1.0, max_value=2.0, value=1.3, step=0.01, key='gw_loss2')
        base2    = get_material_base_price(gw_mat2, g_sell, p_sell_pt)
        unit_price2 = int(base2 * gw_loss2)
        gw_amt2  = int(gw_w2 * unit_price2)
        gw_col8.metric("金額 B", f"${gw_amt2}", help=f"單價/錢: ${unit_price2}")

        sub_a_gold = gw_amt1 + gw_amt2

        st.markdown(
            f"<div style='background:#fff8e1;border-left:4px solid #D4AF37;padding:8px 14px;border-radius:6px;margin:8px 0;color:#5a4000;'>"
            f"💰 <b>金重小計：${sub_a_gold}</b>"
            f"（A: ${gw_amt1}　B: ${gw_amt2}）"
            f"</div>",
            unsafe_allow_html=True
        )

        st.divider()

        # ── 執模工費區 ──────────────────────────────────────────
        st.markdown("#### 🔧 執模工費")

        c1, c2 = st.columns([1, 2])
        m1 = c1.selectbox("材質 1", ["K金", "白金"], key='mold_m1')
        w1 = c2.number_input("重量 1 (錢)", min_value=0.0, step=0.001, format="%.3f", key='mold_w1')

        c3, c4 = st.columns([1, 2])
        m2 = c3.selectbox("材質 2", ["K金", "白金"], key='mold_m2')
        w2 = c4.number_input("重量 2 (錢)", min_value=0.0, step=0.001, format="%.3f", key='mold_w2')

        is_combo = False
        if w1 > 0 and w2 > 0:
            is_combo = st.checkbox("🔗 雙色組合件 +$500", key='mold_combo')

        sub_a_labor = calculate_jewelry_fee(w1, m1, w2, m2, is_combo)

        parts = []
        if w1 > 0: parts.append(f"{m1}{w1}錢")
        if w2 > 0: parts.append(f"{m2}{w2}錢")
        mold_desc = "+".join(parts)
        if is_combo and w1 > 0 and w2 > 0: mold_desc += "(雙色組合)"

        st.markdown(
            f"<div style='background:#e8f4f8;border-left:4px solid #4682B4;padding:8px 14px;border-radius:6px;margin:8px 0;color:#0d2e4a;'>"
            f"🔧 <b>執模工費小計：${sub_a_labor}</b>"
            f"</div>",
            unsafe_allow_html=True
        )

        if mold_desc:
            gw_detail = ""
            if gw_w1 > 0: gw_detail += f"{gw_mat1}{gw_w1:.3f}錢×{gw_loss1}"
            if gw_w2 > 0: gw_detail += f"+{gw_mat2}{gw_w2:.3f}錢×{gw_loss2}"
            details.append(f"執模[{mold_desc}](工${sub_a_labor}|金{gw_detail}=${sub_a_gold})")

    # 分開顯示總計
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
    st.write("### 標鑲計算 (重量 × 顆數)")
    for i in range(3):
        c1, c2, c3 = st.columns([2, 2, 2])
        sw = c1.number_input(f"重量(ct) #{i+1}", min_value=0.0, step=0.001, format="%.3f", key=f'sw_{i}')
        sc = c2.number_input(f"顆數 #{i+1}", min_value=0, step=1, key=f'sc_{i}')
        sv = c3.checkbox(f"造型爪+50 #{i+1}", key=f'sv_{i}')
        if sc > 0:
            p = (get_stone_price(sw) + (50 if sv else 0)) * sc
            sub_b += p
            details.append(f"標鑲{sw}ct*{sc}")

    st.divider()
    st.write("### 克拉單價計算 (單價 × 總重)")
    for j in range(3):
        c_p_col, c_w_col = st.columns(2)
        cp = c_p_col.number_input(f"單價/ct #{j+1}", min_value=0.0, key=f'cp_{j}')
        cw = c_w_col.number_input(f"總重量(ct) #{j+1}", min_value=0.0, step=0.001, format="%.3f", key=f'cw_{j}')
        if cp > 0 and cw > 0:
            sub_b += (cp * cw)
            details.append(f"克拉鑲({cw}ct)")

    st.divider()
    st.write("### 手動單價")
    mc1, mc2, mc3 = st.columns([2, 2, 2])
    manual_p = mc1.number_input("手動單價", min_value=0.0, key='mp')
    manual_c = mc2.number_input("顆數 ", min_value=0, step=1, key='mc')
    manual_v = mc3.checkbox("造型爪+50 ", key='mv')
    if manual_c > 0:
        p_m = (manual_p + (50 if manual_v else 0)) * manual_c
        sub_b += p_m
        details.append(f"手動鑲*{manual_c}")
    st.write(f"**鑲嵌小計: ${int(sub_b)}**")
    total_sum += sub_b

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
        if c2.checkbox("滿鑽 +100", key='r_full'): sub_c += 100
        if st.checkbox("改大 +200", key='r_big'):
            sub_c += 200
            rb1, rb2, rb3, rb4 = st.columns([2, 2, 2, 2])
            b_mat2 = rb1.selectbox("成色", ["750", "585", "Pt950"], key='big_mat2')
            bw     = rb2.number_input("金料(錢)", min_value=0.0, step=0.001, format="%.3f", key='big_w')
            b_loss = rb3.number_input("損耗", min_value=1.0, max_value=2.0, value=1.3, step=0.01, key='big_loss')
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
    c1, c2 = st.columns(2)

    is_polish = c1.checkbox("拋光 $200", key='p_250')
    if is_polish: sub_d += 200

    earring_q = c2.number_input("單耳/墜子 ($150/個)", min_value=0, step=1, key='earring_q')
    if earring_q > 0: sub_d += (earring_q * 150)

    is_necklace = c1.checkbox("項鍊 $400", key='p_necklace')
    if is_necklace:
        sub_d += 400
        if st.checkbox("✨ 項鍊附加電鍍 +$100", key='necklace_plate'):
            sub_d += 100

    is_bracelet = c2.checkbox("手鍊/手鐲 $500", key='p_bracelet')
    if is_bracelet:
        sub_d += 500
        if st.checkbox("✨ 手鍊/手鐲附加電鍍 +$200", key='bracelet_plate'):
            sub_d += 200

    if is_polish or earring_q > 0:
        if st.checkbox("✨ 附加電鍍 +$50", key='cond_plate'):
            sub_d += 50

    st.divider()
    st.write("**其他電鍍選項**")
    custom_plate = st.number_input("自訂電鍍金額 ($)", min_value=0, step=10, key='custom_plate')
    sub_d += custom_plate

    c3, c4 = st.columns(2)
    if c3.checkbox("純電鍍 $100", key='p_100'): sub_d += 100
    if c4.checkbox("白金 +50", key='p_white'): sub_d += 50
    if c3.checkbox("雙色 +100", key='p_double'): sub_d += 100
    if c4.checkbox("噴砂 +100", key='p_sand'): sub_d += 100
    if c3.checkbox("大件 +50", key='p_wide'): sub_d += 50
    if c4.checkbox("克拉 +50", key='p_carat'): sub_d += 50
    if c3.checkbox("整新 +100", key='p_renew'): sub_d += 100

    if sub_d > 0: details.append(f"拋光電鍍(${int(sub_d)})")
    st.write(f"**拋光電鍍小計: ${int(sub_d)}**")
    total_sum += sub_d

# E. 維修設計
with st.expander("🔨 維修設計", expanded=False):
    sub_e = 0
    col_e1, col_e2 = st.columns(2)
    sub_e += col_e1.number_input("鈎鍊+雷射 ($100)", min_value=0, step=1, key='rep_c') * 100
    sub_e += col_e2.number_input("雷射金額 ($)", min_value=0.0, step=10.0, key='entry_laser_fee')

    st.write("---")
    st.write("**黏耳針 / 補爪 ($150 + 金料)**")
    ce1, ce2, ce3, ce4, ce5 = st.columns([1, 2, 2, 2, 2])
    comb_q  = ce1.number_input("次數", min_value=0, step=1, key='comb_q')
    comb_m2 = ce2.selectbox("成色", ["750", "585", "Pt950"], key='comb_m2')
    comb_w  = ce3.number_input("金料(錢)", min_value=0.0, step=0.001, format="%.3f", key='comb_w')
    comb_loss = ce4.number_input("損耗", min_value=1.0, max_value=2.0, value=1.3, step=0.01, key='comb_loss')
    comb_base = get_material_base_price(comb_m2, g_sell, p_sell_pt)
    comb_unit = int(comb_base * comb_loss)
    comb_gold_amt = int(comb_w * comb_unit)
    ce5.metric("金料金額", f"${comb_gold_amt}", help=f"單價/錢: ${comb_unit}")
    comb_labor = comb_q * 150
    sub_e += comb_labor + comb_gold_amt
    if comb_q > 0:
        details.append(f"補爪×{comb_q}(金{comb_m2}{comb_w:.3f}錢×損耗{comb_loss},金料${comb_gold_amt})")

    st.write("---")
    st.write("**補金 ($自填工資 + 金料)**")
    le1, le2, le3, le4, le5 = st.columns([2, 2, 2, 2, 2])
    l_price   = le1.number_input("補金工資($)", min_value=0.0, step=10.0, key='laser_p')
    l_mat2    = le2.selectbox("成色", ["750", "585", "Pt950"], key='laser_mat2')
    l_weight  = le3.number_input("金料(錢)", min_value=0.0, step=0.001, format="%.3f", key='laser_w')
    l_loss    = le4.number_input("損耗", min_value=1.0, max_value=2.0, value=1.3, step=0.01, key='laser_loss')
    l_base    = get_material_base_price(l_mat2, g_sell, p_sell_pt)
    l_unit    = int(l_base * l_loss)
    l_gold_amt = int(l_weight * l_unit)
    le5.metric("金料金額", f"${l_gold_amt}", help=f"單價/錢: ${l_unit}")
    sub_e += l_price + l_gold_amt
    if l_weight > 0 or l_price > 0:
        details.append(f"補金(工${int(l_price)},{l_mat2}{l_weight:.3f}錢×損耗{l_loss},金料${l_gold_amt})")

    st.write("---")
    eng_choice = st.radio("刻字服務", ["無", "1-5字($50)", "5-10字/LOGO($100)"], key='eng_choice', horizontal=True)
    if "1-5" in eng_choice: sub_e += 50
    elif "5-10" in eng_choice: sub_e += 100

    if st.checkbox("11-20字/特殊圖樣 (+$300)", key='rotary_pattern'): sub_e += 300
    if st.checkbox("3D掃描(+500)", key='3d_scan'): sub_e += 500

    draw_fee = st.number_input("製圖金額 ($)", min_value=0, step=100, key='draw_fee')
    sub_e += draw_fee

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

        WAX_UNIT = 500   # 每克蠟單價
        DESIGN_FEE = 250 # 1.5g 以下圖面處理費（每件）

        wax_material = int(wax_w * WAX_UNIT * wax_qty)
        design_total = DESIGN_FEE * wax_qty if wax_w <= 1.5 and wax_w > 0 else 0
        sub_f = wax_material + design_total

        # 顯示明細
        fee_note = f"蠟料 {wax_w}g×{wax_qty}件×${WAX_UNIT}/g = ${wax_material}"
        if design_total > 0:
            fee_note += f"　+ 圖面處理費 ${DESIGN_FEE}×{wax_qty}件 = ${design_total}"

        st.markdown(
            f"<div style='background:#f3f0ff;border-left:4px solid #7c5cbf;padding:8px 14px;"
            f"border-radius:6px;margin:8px 0;color:#2e1a5e;font-size:13px;'>"
            f"🕯️ {fee_note}"
            f"</div>",
            unsafe_allow_html=True
        )
        if sub_f > 0:
            details.append(f"3D出蠟({wax_w}g×{wax_qty}件,${sub_f})")

    st.write(f"**3D出蠟小計: ${int(sub_f)}**")
    total_sum += sub_f

# 散客加價
st.divider()
is_walkin = st.checkbox("👤 散客（所有工資 ×2）", key='is_walkin')

# 計算工資總額（不含金屬料）與金屬料總額，分開後套用倍率
# 金屬料：sub_a_gold（金重）、改圍金料、補爪金料、補金金料 → 已混入各 sub，需拆出
# 設計：各區塊工資已分開計算，散客倍率只套在「純工資」部分
walkin_mult = 2 if is_walkin else 1

# 重新計算含散客倍率的總金額
# A. 執模：工費 × 倍率，金重不變
final_a = int(sub_a_labor * walkin_mult) + sub_a_gold

# B. 鑲嵌：全部為工費 × 倍率
final_b = int(sub_b * walkin_mult)

# C. 改圍：拆出金料 vs 工費
resize_gold = 0
resize_labor = 0
if st.session_state.get('do_resize', False):
    r_big_val  = st.session_state.get('r_big', False)
    if r_big_val:
        bw_val     = st.session_state.get('big_w', 0.0)
        b_loss_val = st.session_state.get('big_loss', 1.3)
        b_mat2_val = st.session_state.get('big_mat2', '750')
        b_base_val = get_material_base_price(b_mat2_val, g_sell, p_sell_pt)
        resize_gold = int(bw_val * int(b_base_val * b_loss_val))
    resize_labor = sub_c - resize_gold - 200  # 扣掉改大工費200也算工資
    resize_labor = sub_c - resize_gold
final_c = int(resize_labor * walkin_mult) + int(resize_gold)

# D. 拋光電鍍：全部工費 × 倍率
final_d = int(sub_d * walkin_mult)

# E. 維修設計：拆出金料（補爪＋補金），工費倍率
comb_w_val    = st.session_state.get('comb_w', 0.0)
comb_loss_val = st.session_state.get('comb_loss', 1.3)
comb_m2_val   = st.session_state.get('comb_m2', '750')
comb_base_val = get_material_base_price(comb_m2_val, g_sell, p_sell_pt)
comb_gold_val = int(comb_w_val * int(comb_base_val * comb_loss_val))

laser_w_val    = st.session_state.get('laser_w', 0.0)
laser_loss_val = st.session_state.get('laser_loss', 1.3)
laser_m2_val   = st.session_state.get('laser_mat2', '750')
laser_base_val = get_material_base_price(laser_m2_val, g_sell, p_sell_pt)
laser_gold_val = int(laser_w_val * int(laser_base_val * laser_loss_val))

repair_gold  = comb_gold_val + laser_gold_val
repair_labor = sub_e - repair_gold
final_e = int(repair_labor * walkin_mult) + int(repair_gold)

total_final = final_a + final_b + final_c + final_d + final_e

# F. 3D出蠟：蠟料不加倍，圖面處理費（工費）加倍
wax_w_val   = st.session_state.get('wax_w', 0.0)
wax_qty_val = st.session_state.get('wax_qty', 1)
do_wax_val  = st.session_state.get('do_wax', False)
if do_wax_val:
    wax_mat_cost    = int(wax_w_val * 500 * wax_qty_val)
    design_fee_each = 250 * wax_qty_val if wax_w_val <= 1.5 and wax_w_val > 0 else 0
    final_f = wax_mat_cost + int(design_fee_each * walkin_mult)
else:
    final_f = 0

total_final = final_a + final_b + final_c + final_d + final_e + final_f

# 備註欄
note = st.text_area("📝 備註", key='note', height=80)

# --- 4. 結算與紀錄管理 ---
st.divider()
if is_walkin:
    st.markdown(
        f"<div style='background:#fff0f0;border-left:4px solid #e00;padding:8px 14px;border-radius:6px;margin:4px 0;color:#7a0000;font-size:14px;'>"
        f"👤 散客模式：工資 ×2（金屬料不變）"
        f"</div>", unsafe_allow_html=True
    )
st.markdown(f"<h2 style='text-align: center; color: red;'>當前應收金額: ${int(total_final)}</h2>", unsafe_allow_html=True)

col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    if st.button("🔄 清除當前輸入", on_click=reset_fields, use_container_width=True):
        st.rerun()

with col_btn2:
    if st.button("➕ 將此筆加入紀錄", use_container_width=True):
        new_record = {
            "時間": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "黃金牌價": g_sell,
            "白金牌價": p_sell_pt,
            "總金額": int(total_final),
            "散客": "是" if is_walkin else "否",
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
