import streamlit as st
import pandas as pd
from datetime import datetime

# --- 設定網頁標題 ---
st.set_page_config(page_title="金工報價系統 v7.0", layout="centered")
st.title("🛠️ 金工報價系統 v7.0")

# --- 核心邏輯 ---
def get_mold_labor_fee(w, material_type):
    """計算執模工費，Pt950 加成 1.3"""
    if w <= 0: return 0
    if w <= 0.5: base = 350
    elif w <= 1.0: base = 500
    elif w <= 2.0: base = 800
    else: base = 1000
    
    multiplier = 1.3 if material_type == "Pt950" else 1.0
    return int(base * multiplier)

def get_stone_price(w):
    """標準鑲嵌單價"""
    if w <= 0: return 0
    if w <= 0.09: return 35
    if w <= 0.19: return 50
    if w <= 0.29: return 100
    if w <= 0.79: return 200
    if w <= 2.00: return 400
    if w <= 3.00: return 600
    return 800

# --- 側邊欄：今日牌價 ---
st.sidebar.header("💰 今日牌價")
gold_sell = st.sidebar.number_input("黃金賣出價", value=0)
plat_sell = st.sidebar.number_input("白金賣出價", value=0)

# 計算即時參考價
v750 = int(gold_sell * 0.75 * 1.3)
v585 = int(gold_sell * 0.585 * 1.3)
vpt = int(plat_sell * 1.25)

st.sidebar.markdown(f"**750 參考:** `${v750}`")
st.sidebar.markdown(f"**585 參考:** `${v585}`")
st.sidebar.markdown(f"**Pt950 參考:** `${vpt}`")

price_map = {"750": v750, "585": v585, "Pt950": vpt}

# --- 主介面 ---
total_price = 0
details = []

# 1. 執模與金料
with st.expander("🛠️ 執模台工 & 金料計算", expanded=True):
    do_mold = st.checkbox("啟用此項目")
    if do_mold:
        col1, col2, col3 = st.columns(3)
        with col1:
            m1 = st.selectbox("材質 1", ["750", "585", "Pt950"])
            m2 = st.selectbox("材質 2", ["750", "585", "Pt950"])
        with col2:
            w1 = st.number_input("重量 1 (錢)", value=0.0, step=0.01)
            w2 = st.number_input("重量 2 (錢)", value=0.0, step=0.01)
        with col3:
            l1 = st.number_input("損耗 1 (倍率)", value=1.1, step=0.05)
            l2 = st.number_input("損耗 2 (倍率)", value=1.1, step=0.05)
        
        is_combined = st.checkbox("組合件/雙色 (+ $500)")
        
        # 計算
        g_fee = (price_map[m1]*w1*l1) + (price_map[m2]*w2*l2)
        l_fee = get_mold_labor_fee(w1, m1) + get_mold_labor_fee(w2, m2)
        if is_combined: l_fee += 500
        
        st.info(f"金料小計: ${int(g_fee)} | 工費小計: ${int(l_fee)}")
        total_price += (g_fee + l_fee)

# 2. 鑲嵌服務
with st.expander("💎 鑲嵌服務"):
    st.write("--- 標準鑲嵌 ---")
    for i in range(2):
        c1, c2, c3 = st.columns([2,2,1])
        with c1: sw = st.number_input(f"石重 {i+1} (ct)", value=0.0, key=f"sw{i}")
        with c2: sc = st.number_input(f"顆數 {i+1}", value=0, key=f"sc{i}")
        with c3: sv = st.checkbox("造型爪", key=f"sv{i}")
        if sc > 0:
            total_price += (get_stone_price(sw) + (50 if sv else 0)) * sc

# 3. 維修設計
with st.expander("🔨 維修與雷射"):
    col_a, col_b = st.columns(2)
    with col_a:
        hook_laser = st.number_input("鈎鍊+雷射 ($100) 次數", value=0)
        custom_laser = st.number_input("自訂雷射金額 ($)", value=0)
    with col_b:
        repair_labor = st.number_input("補金工資 ($)", value=0)
        repair_gold_w = st.number_input("補金金料 (錢)", value=0.0)
        repair_mat = st.radio("補金材質", ["金", "白金"], horizontal=True)
    
    st.write("--- 刻字服務 ---")
    eng_type = st.radio("刻字字數", ["無", "1-5字 ($50)", "5-10字/LOGO ($100)"], horizontal=True)
    rotary = st.checkbox("使用旋轉台 (+ $250)")
    
    # 維修計算
    sub_e = (hook_laser * 100) + custom_laser + repair_labor
    sub_e += repair_gold_w * (gold_sell if repair_mat == "金" else plat_sell)
    if "1-5字" in eng_type: sub_e += 50
    elif "5-10字" in eng_type: sub_e += 100
    if rotary: sub_e += 250
    total_price += sub_e

# 4. 拋光電鍍
with st.expander("✨ 拋光電鍍"):
    pol_cols = st.columns(2)
    with pol_cols[0]:
        p1 = st.checkbox("拋光 $300")
        p2 = st.checkbox("鍊類 $800")
    with pol_cols[1]:
        p3 = st.checkbox("白金/電鍍 +$50")
        p4 = st.checkbox("噴砂/雙色 +$100")
    
    sub_d = (300 if p1 else 0) + (800 if p2 else 0) + (50 if p3 else 0) + (100 if p4 else 0)
    total_price += sub_d

# --- 結帳區 ---
st.divider()
st.subheader(f"💰 應收總金額： :red[${int(total_price)}]")

note = st.text_area("📝 備註 (會儲存至紀錄)")

if st.button("💾 儲存這筆報價", type="primary"):
    # 在網頁版中，我們可以使用 Pandas 顯示歷史紀錄或下載 CSV
    st.success(f"已計算完成！總金額 ${int(total_price)}。 (網頁版紀錄建議搭配資料庫使用)")