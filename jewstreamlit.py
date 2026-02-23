import streamlit as st
import pandas as pd
from datetime import datetime
import os

# 設定網頁標題與排版
st.set_page_config(page_title="金工報價系統 v4.9", layout="centered")

# --- 1. 價格邏輯函數 ---
def get_mold_price(w):
    if w <= 0: return 300
    if w <= 0.3: return 500
    if w <= 0.5: return 600
    if w <= 0.7: return 700
    if w <= 0.9: return 800
    if w <= 1.5: return 900
    if w <= 2.0: return 1000
    return 1100

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
if 'refresh' not in st.session_state:
    st.session_state.refresh = 0

def reset_fields():
    st.session_state.refresh += 1
    st.rerun()

# --- 3. 介面設計 ---
st.title("🛠️ 金工報價系統 v4.9")

# 今日牌價區
with st.expander("💰 今日牌價與損耗換算", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        g_sell = st.number_input("黃金賣出 (錢):", min_value=0.0, step=100.0, value=0.0)
    with col2:
        p_sell_pt = st.number_input("白金賣出 (錢):", min_value=0.0, step=100.0, value=0.0)
    
    # 損耗計算 (K金1.3, 白金1.25)
    p750 = int(g_sell * 0.75 * 1.3)
    p585 = int(g_sell * 0.585 * 1.3)
    ppt950 = int(p_sell_pt * 1.25)
    
    st.markdown(f"**750:** `{p750}` | **585:** `{p585}` | **Pt950:** `{ppt950}`")

# 核心變數收集
details = []
total = 0

# A. 執模台工
st.header("⚒️ 執模台工")
do_mold = st.checkbox("啟用執模服務", key=f"mold_chk_{st.session_state.refresh}")
if do_mold:
    m_w = st.number_input("輸入重量:", min_value=0.0, step=0.01, key=f"mw_{st.session_state.refresh}")
    base_mold = get_mold_price(m_w)
    st.info(f"基準工資: ${base_mold}")
    total += base_mold
    m_detail = f"執模(${base_mold})"
    
    c_m1, c_m2 = st.columns(2)
    if c_m1.checkbox("白金 +100", key=f"mp_{st.session_state.refresh}"):
        total += 100
        m_detail += "+白金"
    if c_m2.checkbox("雙色 +200", key=f"md_{st.session_state.refresh}"):
        total += 200
        m_detail += "+雙色"
    details.append(m_detail)

# B. 鑲嵌服務
st.header("💎 鑲嵌服務")
for i in range(3):
    c1, c2, c3 = st.columns([1, 1, 1])
    s_w = c1.number_input(f"重量 (ct) #{i+1}", min_value=0.0, step=0.01, key=f"sw{i}_{st.session_state.refresh}")
    s_c = c2.number_input(f"數量 #{i+1}", min_value=0, step=1, key=f"sc{i}_{st.session_state.refresh}")
    is_style = c3.checkbox(f"造型爪 +50 #{i+1}", key=f"ss{i}_{st.session_state.refresh}")
    
    if s_c > 0:
        p = get_stone_price(s_w)
        single_p = p + (50 if is_style else 0)
        total += single_p * s_c
        details.append(f"鑲嵌{s_w}ct*{s_c}" + ("(造型爪)" if is_style else ""))

# C. 改圍加價
st.header("💍 改圍加價")
do_resize = st.checkbox("啟用改圍基礎 $300", key=f"rs_{st.session_state.refresh}")
if do_resize:
    total += 300
    r_detail = "改圍($300)"
    cr1, cr2, cr3, cr4 = st.columns(4)
    if cr1.checkbox("白金 +100", key=f"rp_{st.session_state.refresh}"): total += 100; r_detail += "+白金"
    if cr2.checkbox("寬版 +100", key=f"rw_{st.session_state.refresh}"): total += 100; r_detail += "+寬版"
    if cr3.checkbox("封底 +100", key=f"rb_{st.session_state.refresh}"): total += 100; r_detail += "+封底"
    if cr4.checkbox("滿鑽 +100", key=f"rf_{st.session_state.refresh}"): total += 100; r_detail += "+滿鑽"
    
    if st.checkbox("改大 +200", key=f"r_big_{st.session_state.refresh}"):
        big_w = st.number_input("增加錢數:", min_value=0.0, key=f"rbw_{st.session_state.refresh}")
        curr_p = ppt950 if "白金" in r_detail else g_sell
        total += 200 + (big_w * curr_p)
        r_detail += f"+改大({big_w}錢)"
    details.append(r_detail)

# D. 拋光 / 電鍍
st.header("✨ 拋光 / 電鍍")
cp1, cp2, cp3, cp4 = st.columns(4)
pol_items = []
if cp1.checkbox("拋光 $300", key=f"p1_{st.session_state.refresh}"): total += 300; pol_items.append("基礎")
if cp2.checkbox("小墜 $200", key=f"p2_{st.session_state.refresh}"): total += 200; pol_items.append("小墜")
if cp3.checkbox("單耳 $150", key=f"p3_{st.session_state.refresh}"): total += 150; pol_items.append("單耳")
if cp4.checkbox("鍊類 $800", key=f"p4_{st.session_state.refresh}"): total += 800; pol_items.append("鍊類")
if st.checkbox("純電鍍 $100", key=f"pe_{st.session_state.refresh}"): total += 100; pol_items.append("純電鍍")

if pol_items:
    p_detail = f"拋光({','.join(pol_items)})"
    cp_s1, cp_s2, cp_s3, cp_s4 = st.columns(4)
    if cp_s1.checkbox("白金 +50", key=f"ps1_{st.session_state.refresh}"): total += 50; p_detail += "+白金"
    if cp_s2.checkbox("雙色 +100", key=f"ps2_{st.session_state.refresh}"): total += 100; p_detail += "+雙色"
    if cp_s3.checkbox("噴砂 +100", key=f"ps3_{st.session_state.refresh}"): total += 100; p_detail += "+噴砂"
    if cp_s4.checkbox("寬版 +50", key=f"ps4_{st.session_state.refresh}"): total += 50; p_detail += "+寬版"
    details.append(p_detail)

# E. 維修與設計
st.header("🔧 維修與設計")
rep_col1, rep_col2 = st.columns(2)
r_c = rep_col1.number_input("C圈 1點 ($100):", min_value=0, key=f"rc_{st.session_state.refresh}")
r_s = rep_col2.number_input("補字印 ($150):", min_value=0, key=f"rs_in_{st.session_state.refresh}")
r_cr = rep_col1.number_input("裂金 ($300):", min_value=0, key=f"rcr_{st.session_state.refresh}")
r_st = rep_col2.number_input("黏耳針 ($200):", min_value=0, key=f"rst_{st.session_state.refresh}")

claw_c = rep_col1.number_input("補爪支數 ($250):", min_value=0, key=f"rclaw_{st.session_state.refresh}")
claw_w = rep_col2.number_input("補爪金料 (錢):", min_value=0.0, key=f"rclaww_{st.session_state.refresh}")

if r_c: total += r_c * 100; details.append(f"C圈*{r_c}")
if r_s: total += r_s * 150; details.append(f"補字印*{r_s}")
if r_cr: total += r_cr * 300; details.append(f"裂金*{r_cr}")
if r_st: total += r_st * 200; details.append(f"黏耳針*{r_st}")
if claw_c or claw_w: 
    total += (claw_c * 250) + (claw_w * g_sell)
    details.append(f"補爪*{claw_c}(料{claw_w}錢)")

des_c1, des_c2 = st.columns(2)
if des_c1.checkbox("🎨 3D掃描 (+500)", key=f"d3d_{st.session_state.refresh}"): total += 500; details.append("3D掃描")
if des_c2.checkbox("📝 基本製圖 (+1500)", key=f"ddr_{st.session_state.refresh}"): total += 1500; details.append("製圖")

# --- 計算與結果 ---
st.divider()
final_price = total
discount_text = ""
if total >= 6000: final_price = total * 0.8; discount_text = "(單件8折)"
elif total >= 3000: final_price = total * 0.9; discount_text = "(單件9折)"

st.subheader(f"原始總計: `${int(total)}`")
st.error(f"### 應收金額: ${int(final_price)} {discount_text}")

note = st.text_area("📝 備註 (將儲存至 Excel)", key=f"note_{st.session_state.refresh}")

# --- 儲存按鈕 ---
col_btn1, col_btn2 = st.columns(2)

if col_btn1.button("💾 儲存報價紀錄", use_container_width=True):
    filename = "報價紀錄.csv"
    headers = ["日期時間", "黃金賣出", "白金賣出", "應收總金額", "報價明細", "備註"]
    details_str = " | ".join(details) if details else "無"
    new_data = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), g_sell, p_sell_pt, int(final_price), details_str, note]
    
    file_exists = os.path.isfile(filename)
    with open(filename, 'a', newline='', encoding='utf-8-sig') as f:
        import csv
        writer = csv.writer(f)
        if not file_exists: writer.writerow(headers)
        writer.writerow(new_data)
    st.success("儲存成功！紀錄已寫入 報價紀錄.csv")

if col_btn2.button("🧹 清除所有選項", use_container_width=True):
    reset_fields()

# 下載按鈕 (Streamlit 特色，可直接下載目前的所有紀錄檔案)
if os.path.exists("報價紀錄.csv"):
    with open("報價紀錄.csv", "rb") as file:
        st.download_button(
            label="📥 下載完整 Excel (CSV) 檔案",
            data=file,
            file_name="金工報價紀錄.csv",
            mime="text/csv",
        )
