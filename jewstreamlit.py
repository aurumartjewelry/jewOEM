import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- 頁面設定 ---
st.set_page_config(page_title="金工報價系統 v7.0", layout="centered")

# --- 1. 價格與計算邏輯 ---
def get_mold_price(w):
    if w <= 0: return 300
    if w <= 0.3: return 400
    if w <= 0.5: return 500
    if w <= 0.7: return 600
    if w <= 0.9: return 700
    if w <= 1.5: return 800
    if w <= 2.0: return 900
    return 1000

def get_stone_price(w):
    if w <= 0: return 0
    if w <= 0.09: return 35
    if w <= 0.19: return 50
    if w <= 0.29: return 100
    if w <= 0.79: return 200
    if w <= 2.00: return 400
    if w <= 3.00: return 600
    return 800

# --- 2. 初始化 Session State (用於清除功能) ---
if 'gold_price' not in st.session_state:
    st.session_state.gold_price = 0.0
if 'plat_price' not in st.session_state:
    st.session_state.plat_price = 0.0

def reset_fields():
    """清除按鈕邏輯：保留金價與白金價格"""
    keys_to_keep = ['gold_price', 'plat_price']
    for key in st.session_state.keys():
        if key not in keys_to_keep:
            # 根據類型給予預設值
            if isinstance(st.session_state[key], bool):
                st.session_state[key] = False
            elif isinstance(st.session_state[key], (int, float)):
                st.session_state[key] = 0.0
            elif isinstance(st.session_state[key], str):
                st.session_state[key] = ""
    # 特別處理 Radio Button 預設值
    st.session_state.eng_choice = "無"
    st.session_state.big_mat = "金"
    st.session_state.comb_m = "金"
    st.session_state.laser_m = "金"

# --- 3. UI 介面 ---
st.markdown("<h1 style='text-align: center;'>今日金價</h1>", unsafe_allow_html=True) #

col_p1, col_p2 = st.columns(2)
with col_p1:
    g_sell = st.number_input("黃金賣出價", value=st.session_state.gold_price, key='gold_price', step=10.0)
with col_p2:
    p_sell_pt = st.number_input("白金賣出價", value=st.session_state.plat_price, key='plat_price', step=10.0)

# 計算牌價 (套用最新耗損係數)
v750 = int(g_sell * 0.75 * 1.3)
v585 = int(g_sell * 0.585 * 1.3)
vpt = int(p_sell_pt * 1.25)

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
with st.expander("🛠️ 執模台工", expanded=True):
    do_mold = st.checkbox("啟用執模服務", key='do_mold')
    sub_a = 0
    if do_mold:
        mold_w = st.number_input("輸入重量", min_value=0.0, step=0.01, key='mold_w')
        sub_a = get_mold_price(mold_w)
        col_a1, col_a2 = st.columns(2)
        if col_a1.checkbox("白金 +100", key='mold_plat'): sub_a += 100
        if col_a2.checkbox("雙色 +200", key='mold_double'): sub_a += 200
        details.append(f"執模(${sub_a})")
    st.write(f"**執模小計: ${sub_a}**")
    total_sum += sub_a

# B. 鑲嵌服務
with st.expander("💎 鑲嵌服務", expanded=True):
    sub_b = 0
    st.write("**標鑲計算**")
    for i in range(2):
        c1, c2, c3 = st.columns([2, 2, 2])
        sw = c1.number_input(f"重量(ct) #{i+1}", min_value=0.0, step=0.01, key=f'sw_{i}')
        sc = c2.number_input(f"顆數 #{i+1}", min_value=0, step=1, key=f'sc_{i}')
        sv = c3.checkbox(f"造型爪+50 #{i+1}", key=f'sv_{i}')
        if sc > 0:
            p = (get_stone_price(sw) + (50 if sv else 0)) * sc
            sub_b += p
            details.append(f"標鑲{sw}ct*{sc}")
    
    st.write("**克拉單價計算**")
    c_p, c_w = st.columns(2)
    carat_p = c_p.number_input("單價/ct", min_value=0.0, key='carat_p')
    carat_w = c_w.number_input("總重量(ct)", min_value=0.0, key='carat_w')
    if carat_p > 0 and carat_w > 0:
        sub_b += (carat_p * carat_w)
        details.append(f"克拉鑲({carat_w}ct)")
    st.write(f"**鑲嵌小計: ${int(sub_b)}**")
    total_sum += sub_b

# C. 改圍加價
with st.expander("💍 改圍加價"):
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
            bw = st.number_input("加金重量(錢)", min_value=0.0, key='big_w')
            b_mat = st.radio("改大金料材質", ["金", "白金"], horizontal=True, key='big_mat')
            mat_p = g_sell if b_mat == "金" else p_sell_pt
            sub_c += (bw * mat_p)
        details.append(f"改圍(${int(sub_c)})")
    st.write(f"**改圍小計: ${int(sub_c)}**")
    total_sum += sub_c

# D. 拋光 / 電鍍
with st.expander("✨ 拋光 / 電鍍"):
    sub_d = 0
    c1, c2 = st.columns(2)
    if c1.checkbox("拋光 $300", key='p_300'): sub_d += 300
    if c2.checkbox("小墜 $200", key='p_200'): sub_d += 200
    if c1.checkbox("單耳 $150", key='p_150'): sub_d += 150
    if c2.checkbox("鍊類 $800", key='p_800'): sub_d += 800
    if st.checkbox("純電鍍 $100", key='p_100'): sub_d += 100
    
    st.write("**加價項目**")
    c3, c4 = st.columns(2)
    if c3.checkbox("白金 +50", key='p_white'): sub_d += 50 #
    if c4.checkbox("雙色 +100", key='p_double'): sub_d += 100
    if c3.checkbox("噴砂 +100", key='p_sand'): sub_d += 100
    if c4.checkbox("寬版 +50", key='p_wide'): sub_d += 50
    if st.checkbox("克拉 +50", key='p_carat'): sub_d += 50
    
    if sub_d > 0: details.append(f"拋光電鍍(${sub_d})")
    st.write(f"**拋光電鍍小計: ${sub_d}**")
    total_sum += sub_d

# E. 維修設計 (補足所有遺失欄位)
with st.expander("🔨 維修設計", expanded=True):
    sub_e = 0
    col_e1, col_e2 = st.columns(2)
    c_q = col_e1.number_input("C圈1點 ($100)", min_value=0, step=1, key='rep_c')
    s_q = col_e2.number_input("補字印 ($150)", min_value=0, step=1, key='rep_s')
    sub_e += (c_q * 100) + (s_q * 150)
    
    st.divider()
    st.write("**黏耳針 / 補爪 ($200 + 金料)**")
    ce1, ce2, ce3 = st.columns([1, 1, 1])
    comb_q = ce1.number_input("次數", min_value=0, step=1, key='comb_q')
    comb_w = ce2.number_input("金料重量", min_value=0.0, step=0.01, key='comb_w')
    comb_m = ce3.radio("材質", ["金", "白金"], key='comb_m', horizontal=True)
    sub_e += (comb_q * 200) + (comb_w * (g_sell if comb_m == "金" else p_sell_pt))

    st.divider()
    st.write("**雷射補金 (自填工資 + 金料)**")
    le1, le2, le3 = st.columns([1, 1, 1])
    laser_p = le1.number_input("雷射工資", min_value=0.0, step=10.0, key='laser_p')
    laser_w = le2.number_input("補金重量", min_value=0.0, step=0.01, key='laser_w')
    laser_m = le3.radio("補金材質", ["金", "白金"], key='laser_m', horizontal=True)
    sub_e += laser_p + (laser_w * (g_sell if laser_m == "金" else p_sell_pt))

    st.divider()
    eng_choice = st.radio("刻字服務", ["無", "1-5字 ($50)", "5-10字 ($100)"], key='eng_choice', horizontal=True)
    if "1-5" in eng_choice: sub_e += 50
    elif "5-10" in eng_choice: sub_e += 100
    
    col_m1, col_m2 = st.columns(2)
    if col_m1.checkbox("特殊圖案 (+$500)", key='pattern'): sub_e += 500
    if col_m2.checkbox("3D 掃描 (+$500)", key='3d_scan'): sub_e += 500
    if col_m1.checkbox("製圖 (+$1500)", key='draw'): sub_e += 1500
    
    if sub_e > 0: details.append(f"維修設計(${int(sub_e)})")
    st.write(f"**維修小計: ${int(sub_e)}**")
    total_sum += sub_e

# 備註欄
note = st.text_area("備註", key='note', placeholder="輸入客戶特殊要求...")

# --- 4. 底部結算區 ---
st.divider()
st.markdown(f"<h2 style='text-align: center; color: red;'>應收總金額: ${int(total_sum)}</h2>", unsafe_allow_html=True)

col_btn1, col_btn2 = st.columns(2)
if col_btn1.button("清除全部內容", on_click=reset_fields, use_container_width=True):
    st.rerun()

# 儲存與匯出功能
if col_btn2.button("準備匯出紀錄", use_container_width=True):
    df = pd.DataFrame([{
        "時間": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "當日金價": g_sell,
        "總金額": int(total_sum),
        "明細": " | ".join(details),
        "備註": note
    }])
    
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
    st.download_button(
        label="點此下載報價紀錄 CSV",
        data=csv_buffer.getvalue(),
        file_name=f"報價紀錄_{datetime.now().strftime('%m%d_%H%M')}.csv",
        mime="text/csv"
    )