import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- 頁面設定 ---
st.set_page_config(page_title="金工報價系統", layout="centered")

# --- 1. 價格與計算邏輯 ---
def calculate_jewelry_fee(w1, m1, w2, m2):
    """執模台工費：包含兩件重量與材質，大於0視為雙色組合"""
    def get_base(w):
        if w <= 0: return 0
        if w <= 0.5: return 350
        elif w <= 1.0: return 500
        elif w <= 2.0: return 800
        else: return 1000

    fee1 = get_base(w1) * (1.3 if m1 == "白金" else 1.0)
    fee2 = get_base(w2) * (1.3 if m2 == "白金" else 1.0)
    total_fee = fee1 + fee2
    if w1 > 0 and w2 > 0:
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

# --- 2. 初始化 Session State (狀態管理) ---
if 'gold_price' not in st.session_state: st.session_state.gold_price = 0.0
if 'plat_price' not in st.session_state: st.session_state.plat_price = 0.0
if 'records' not in st.session_state: st.session_state.records = []

def reset_fields():
    """清除輸入欄位，保留金價與歷史紀錄"""
    keys_to_keep = ['gold_price', 'plat_price', 'records']
    for key in list(st.session_state.keys()):
        if key not in keys_to_keep:
            val = st.session_state[key]
            if isinstance(val, bool): st.session_state[key] = False
            elif isinstance(val, (int, float)): st.session_state[key] = 0.0
            elif isinstance(val, str): st.session_state[key] = ""
    # 預設值回歸
    st.session_state.mold_m1 = "K金"; st.session_state.mold_m2 = "K金"
    st.session_state.eng_choice = "無"; st.session_state.big_mat = "金"
    st.session_state.comb_m = "金"; st.session_state.laser_m = "金"

# --- 3. UI 介面 ---
st.markdown("<h1 style='text-align: center;'>今日金價</h1>", unsafe_allow_html=True)

col_p1, col_p2 = st.columns(2)
with col_p1: g_sell = st.number_input("黃金賣出價", value=st.session_state.gold_price, key='gold_price', step=10.0)
with col_p2: p_sell_pt = st.number_input("白金賣出價", value=st.session_state.plat_price, key='plat_price', step=10.0)

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
        c1, c2 = st.columns([1, 2])
        m1 = c1.selectbox("材質 1", ["K金", "白金"], key='mold_m1')
        w1 = c2.number_input("重量 1", min_value=0.0, step=0.01, key='mold_w1')
        
        c3, c4 = st.columns([1, 2])
        m2 = c3.selectbox("材質 2", ["K金", "白金"], key='mold_m2')
        w2 = c4.number_input("重量 2", min_value=0.0, step=0.01, key='mold_w2')
        
        sub_a = calculate_jewelry_fee(w1, m1, w2, m2)
        
        parts = []
        if w1 > 0: parts.append(f"{m1}{w1}錢")
        if w2 > 0: parts.append(f"{m2}{w2}錢")
        mold_desc = "+".join(parts)
        if w1 > 0 and w2 > 0: mold_desc += "(雙色組合)"
        if mold_desc: details.append(f"執模[{mold_desc}](${sub_a})")
        
    st.write(f"**執模小計: ${sub_a}**")
    total_sum += sub_a

# B. 鑲嵌服務
with st.expander("💎 鑲嵌服務", expanded=False):
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
            bw = st.number_input("金料(錢):", min_value=0.0, key='big_w')
            b_mat = st.radio("材質", ["金", "白金"], horizontal=True, key='big_mat')
            sub_c += (bw * (g_sell if b_mat == "金" else p_sell_pt))
        details.append(f"改圍(${int(sub_c)})")
    st.write(f"**改圍小計: ${int(sub_c)}**")
    total_sum += sub_c

# D. 拋光 / 電鍍
with st.expander("✨ 拋光 / 電鍍", expanded=False):
    sub_d = 0
    c1, c2 = st.columns(2)
    
    is_polish = c1.checkbox("拋光 $250", key='p_250')
    if is_polish: sub_d += 250
    
    is_pendant = c2.checkbox("小墜 $200", key='p_200')
    if is_pendant: sub_d += 200
    
    earring_q = c1.number_input("單耳數量 ($150/個)", min_value=0, step=1, key='earring_q')
    if earring_q > 0: sub_d += (earring_q * 150)
    
    is_chain = c2.checkbox("鍊類 $700", key='p_700')
    if is_chain: sub_d += 700

    # 智慧連動附加電鍍選項
    if is_polish or is_pendant or earring_q > 0:
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
    if c3.checkbox("寬版 +50", key='p_wide'): sub_d += 50
    if c4.checkbox("克拉 +50", key='p_carat'): sub_d += 50
    
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
    st.write("**黏耳針 / 補爪 ($200 + 金料)**")
    ce1, ce2, ce3 = st.columns([1, 1, 1])
    comb_q = ce1.number_input("次數", min_value=0, step=1, key='comb_q')
    comb_w = ce2.number_input("金料(錢)", min_value=0.0, step=0.01, key='comb_w')
    comb_m = ce3.radio("材質選擇", ["金", "白金"], key='comb_m', horizontal=True)
    sub_e += (comb_q * 200) + (comb_w * (g_sell if comb_m == "金" else p_sell_pt))

    st.write("---")
    st.write("**補金 ($自填工資 + 金料)**")
    le1, le2, le3 = st.columns([1, 1, 1])
    l_price = le1.number_input("補金工資($)", min_value=0.0, step=10.0, key='laser_p')
    l_weight = le2.number_input("金料(錢) ", min_value=0.0, step=0.01, key='laser_w')
    l_mat = le3.radio("補金材質", ["金", "白金"], key='laser_m', horizontal=True)
    sub_e += l_price + (l_weight * (g_sell if l_mat == "金" else p_sell_pt))

    st.write("---")
    eng_choice = st.radio("刻字服務", ["無", "1-5字($50)", "5-10字/LOGO($100)"], key='eng_choice', horizontal=True)
    if "1-5" in eng_choice: sub_e += 50
    elif "5-10" in eng_choice: sub_e += 100
    
    # 旋轉與特殊圖合併
    if st.checkbox("旋轉+特殊圖 (+$500)", key='rotary_pattern'): sub_e += 500
    if st.checkbox("3D掃描(+500)", key='3d_scan'): sub_e += 500
    
    # 製圖改為自訂輸入
    draw_fee = st.number_input("製圖金額 ($)", min_value=0, step=100, key='draw_fee')
    sub_e += draw_fee
    
    if sub_e > 0: details.append(f"維修(${int(sub_e)})")
    st.write(f"**維修小計: ${int(sub_e)}**")
    total_sum += sub_e

# 備註欄
note = st.text_area("📝 備註", key='note', height=80)

# --- 4. 結算與紀錄管理 ---
st.divider()
st.markdown(f"<h2 style='text-align: center; color: red;'>當前應收金額: ${int(total_sum)}</h2>", unsafe_allow_html=True)

col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    if st.button("🔄 清除當前輸入", on_click=reset_fields, use_container_width=True):
        st.rerun()

with col_btn2:
    if st.button("➕ 將此筆加入紀錄", use_container_width=True):
        st.session_state.records.append({
            "時間": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "黃金牌價": g_sell,
            "白金牌價": p_sell_pt,
            "總金額": int(total_sum),
            "明細": " | ".join(details) if details else "無項目",
            "備註": note
        })
        st.success("✅ 已加入紀錄清單！您可以清除畫面繼續輸入下一筆。")

# --- 5. 報價紀錄總表匯出 ---
if st.session_state.records:
    st.divider()
    st.write("### 📋 報價紀錄清單")
    df = pd.DataFrame(st.session_state.records)
    st.dataframe(df)
    
    # 產生真實的 .xlsx 檔案
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
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    with c_dl2:
        if st.button("🗑️ 清空所有紀錄", use_container_width=True):
            st.session_state.records = []
            st.rerun()