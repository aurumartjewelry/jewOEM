import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- 頁面設定 ---
st.set_page_config(page_title="金工報價系統 v9.0", layout="centered")

# --- 1. 價格邏輯 (完全參照 jew2.py) ---
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

# --- 2. 初始化 Session State (保留金價功能) ---
if 'gold_price' not in st.session_state:
    st.session_state.gold_price = 0.0
if 'plat_price' not in st.session_state:
    st.session_state.plat_price = 0.0

def reset_fields():
    """清除全部內容，但保留黃金和白金價格"""
    keys_to_keep = ['gold_price', 'plat_price']
    for key in list(st.session_state.keys()):
        if key not in keys_to_keep:
            val = st.session_state[key]
            if isinstance(val, bool): st.session_state[key] = False
            elif isinstance(val, (int, float)): st.session_state[key] = 0.0
            elif isinstance(val, str): st.session_state[key] = ""
    st.session_state.eng_choice = "無"

# --- 3. UI 介面 ---
st.markdown("<h1 style='text-align: center;'>今日金價</h1>", unsafe_allow_html=True) #

col_p1, col_p2 = st.columns(2)
with col_p1:
    g_sell = st.number_input("黃金賣出價", value=st.session_state.gold_price, key='gold_price', step=10.0)
with col_p2:
    p_sell_pt = st.number_input("白金賣出價", value=st.session_state.plat_price, key='plat_price', step=10.0)

# 計算牌價 (套用 1.3 與 1.25 耗損)
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
with st.expander("🛠️ 執模台工", expanded=False):
    do_mold = st.checkbox("啟用執模服務", key='do_mold')
    sub_a = 0
    if do_mold:
        mold_w = st.number_input("輸入重量", min_value=0.0, step=0.01, key='mold_w')
        sub_a = get_mold_price(mold_w)
        if st.checkbox("白金 +100", key='mold_plat'): sub_a += 100
        if st.checkbox("雙色 +200", key='mold_double'): sub_a += 200
        details.append(f"執模(${sub_a})")
    st.write(f"**執模小計: ${sub_a}**")
    total_sum += sub_a

# B. 鑲嵌服務 (完整還原 3+3+1 結構)
with st.expander("💎 鑲嵌服務", expanded=True):
    sub_b = 0
    st.write("### 標鑲計算 (重量 × 顆數)")
    for i in range(3):
        c1, c2, c3 = st.columns([2, 2, 2])
        sw = c1.number_input(f"重量(ct) #{i+1}", min_value=0.0, step=0.01, key=f'sw_{i}')
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
        cw = c_w_col.number_input(f"總重量(ct) #{j+1}", min_value=0.0, key=f'cw_{j}')
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

# C. 改圍加價 (完整還原改大加價)
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
            bw = st.number_input("加金重量(錢)", min_value=0.0, key='big_w')
            b_mat = st.radio("改大材質", ["金", "白金"], horizontal=True, key='big_mat')
            sub_c += (bw * (g_sell if b_mat == "金" else p_sell_pt))
        details.append(f"改圍(${int(sub_c)})")
    st.write(f"**改圍小計: ${int(sub_c)}**")
    total_sum += sub_c

# D. 拋光 / 電鍍
with st.expander("✨ 拋光 / 電鍍", expanded=False):
    sub_d = 0
    c1, c2 = st.columns(2)
    if c1.checkbox("拋光 $300", key='p_300'): sub_d += 300
    if c2.checkbox("小墜 $200", key='p_200'): sub_d += 200
    if c1.checkbox("單耳 $150", key='p_150'): sub_d += 150
    if c2.checkbox("鍊類 $800", key='p_800'): sub_d += 800
    if st.checkbox("純電鍍 $100", key='p_100'): sub_d += 100
    if st.checkbox("白金 + 50", key='p_white'): sub_d += 50 #
    if st.checkbox("雙色 +100", key='p_double'): sub_d += 100
    if st.checkbox("噴砂 +100", key='p_sand'): sub_d += 100
    if st.checkbox("寬版 +50", key='p_wide'): sub_d += 50
    if st.checkbox("克拉 +50", key='p_carat'): sub_d += 50
    if sub_d > 0: details.append(f"拋光電鍍(${sub_d})")
    st.write(f"**拋光電鍍小計: ${sub_d}**")
    total_sum += sub_d

# E. 維修設計 (完整還原雷射與工資計算)
with st.expander("🔨 維修設計", expanded=False):
    sub_e = 0
    col_e1, col_e2 = st.columns(2)
    sub_e += col_e1.number_input("C圈1點 ($100)", min_value=0, step=1, key='rep_c') * 100
    sub_e += col_e2.number_input("補字印 ($150)", min_value=0, step=1, key='rep_s') * 150
    
    st.write("---")
    st.write("**黏耳針 / 補爪 ($200 + 金料)**")
    ce1, ce2, ce3 = st.columns([1, 1, 1])
    comb_q = ce1.number_input("次數", min_value=0, step=1, key='comb_q')
    comb_w = ce2.number_input("金料重(錢)", min_value=0.0, step=0.01, key='comb_w')
    comb_m = ce3.radio("材質選擇", ["金", "白金"], key='comb_m', horizontal=True)
    sub_e += (comb_q * 200) + (comb_w * (g_sell if comb_m == "金" else p_sell_pt))

    st.write("---")
    st.write("**雷射補金 (工資 + 金料)**")
    le1, le2, le3 = st.columns([1, 1, 1])
    l_price = le1.number_input("雷射工資", min_value=0.0, step=10.0, key='laser_p')
    l_weight = le2.number_input("補金重量(錢)", min_value=0.0, step=0.01, key='laser_w')
    l_mat = le3.radio("補金材質", ["金", "白金"], key='laser_m', horizontal=True)
    sub_e += l_price + (l_weight * (g_sell if l_mat == "金" else p_sell_pt))

    st.write("---")
    eng_choice = st.radio("刻字服務", ["無", "1-5字 ($50)", "5-10字 ($100)"], key='eng_choice', horizontal=True)
    if "1-5" in eng_choice: sub_e += 50
    elif "5-10" in eng_choice: sub_e += 100
    
    c_m1, c_m2 = st.columns(2)
    if c_m1.checkbox("特殊圖案 (+$500)", key='pattern'): sub_e += 500
    if c_m2.checkbox("3D 掃描 (+$500)", key='3d_scan'): sub_e += 500
    if st.checkbox("製圖 (+$1500)", key='draw'): sub_e += 1500
    
    st.write(f"**維修小計: ${int(sub_e)}**")
    total_sum += sub_e

# 備註欄 (加寬)
note = st.text_area("備註", key='note', height=100)

# --- 4. 底部結算與匯出 ---
st.divider()
st.markdown(f"<h2 style='text-align: center; color: red;'>應收總金額: ${int(total_sum)}</h2>", unsafe_allow_html=True)

# 解決亂碼的核心邏輯：
# 1. 使用 utf-8-sig
# 2. 將 StringIO 轉換為 BytesIO 並加上 BOM (Byte Order Mark)
df = pd.DataFrame([{
    "時間": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "金價": g_sell,
    "總金額": int(total_sum),
    "明細": " | ".join(details),
    "備註": note
}])

csv_buffer = io.StringIO()
df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
csv_bytes = csv_buffer.getvalue().encode('utf-8-sig') # 強制轉為含 BOM 的位元組

col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    if st.button("清除全部內容", on_click=reset_fields, use_container_width=True):
        st.rerun()

with col_btn2:
    st.download_button(
        label="下載 Excel 報價單",
        data=csv_bytes,
        file_name=f"報價單_{datetime.now().strftime('%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True
    )