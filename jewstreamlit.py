import streamlit as st

# 設定頁面資訊
st.set_page_config(page_title="金工報價系統 v5.0", layout="centered")

def get_mold_price(w):
    if w <= 0: return 300
    if w <= 0.3: return 500
    if w <= 0.5: return 600
    if w <= 0.7: return 700
    if w <= 0.9: return 800
    if w <= 1.5: return 900
    if w <= 2.0: return 1000
    return 1100

st.title("💎 金工報價系統 v5.0")
st.caption("網頁自適應版 - 支援手機與電腦瀏覽")

# --- A. 今日牌價 ---
st.header("💰 今日牌價")
col1, col2 = st.columns(2)
with col1:
    g_sell = st.number_input("黃金賣出:", min_value=0.0, value=0.0, step=100.0)
with col2:
    p_sell_pt = st.number_input("白金Pt賣出:", min_value=0.0, value=0.0, step=100.0)

price_750 = g_sell * 0.75 * 1.27
price_585 = g_sell * 0.585 * 1.27
price_pt950 = p_sell_pt * 1.3

st.info(f"💡 換算參考：**750**: {int(price_750)} | **585**: {int(price_585)} | **Pt950**: {int(price_pt950)}")

# --- B. 執模台工 ---
st.header("🛠️ 執模台工")
do_mold = st.checkbox("啟用執模服務")
if do_mold:
    w_val = st.number_input("輸入重量:", min_value=0.0, value=0.0, step=0.1)
    base_mold = get_mold_price(w_val)
    st.write(f"👉 目前級距基準工資：**${base_mold}**")
    
    m_col1, m_col2 = st.columns(2)
    mold_plat = m_col1.checkbox("白金 +100")
    mold_double = m_col2.checkbox("雙色 +200")
else:
    base_mold = 0
    mold_plat = mold_double = False

# --- C. 鑲嵌服務 ---
st.header("💎 鑲嵌服務")
stone_opts = ["0-0.09 ($35)", "0.10-0.19 ($50)", "0.20-0.29 ($100)", "0.30-0.79 ($200)", "0.80-2.00 ($400)", "2.01-3.00 ($600)", "3.01-4.00 ($800)"]
stone_prices = [35, 50, 100, 200, 400, 600, 800]

total_stone_cost = 0
for i in range(3):
    s_col1, s_col2, s_col3 = st.columns([2, 1, 1])
    with s_col1:
        opt = st.selectbox(f"級距 {i+1}", stone_opts, key=f"opt{i}")
    with s_col2:
        count = st.number_input(f"數量", min_value=0, value=0, key=f"cnt{i}")
    with s_col3:
        special = st.checkbox(f"造型爪", key=f"sp{i}")
    
    if count > 0:
        p = stone_prices[stone_opts.index(opt)]
        if special: p += 50
        total_stone_cost += p * count

# --- D. 改圍加價 ---
st.header("💍 改圍加價")
do_resize = st.checkbox("啟用改圍基礎 $300")
resize_cost = 300 if do_resize else 0
if do_resize:
    r_col1, r_col2 = st.columns(2)
    r_plat = r_col1.checkbox("白金 +100")
    r_wide = r_col2.checkbox("寬版 +100")
    r_back = r_col1.checkbox("封底 +100")
    r_full = r_col2.checkbox("滿鑽 +100")
    r_big = st.checkbox("改大 +200")
    if r_big:
        big_w = st.number_input("增加錢數:", min_value=0.0, value=0.0)
        curr_p = price_pt950 if r_plat else g_sell
        resize_cost += 200 + (big_w * curr_p)
    
    if r_plat: resize_cost += 100
    if r_wide: resize_cost += 100
    if r_back: resize_cost += 100
    if r_full: resize_cost += 100

# --- E. 拋光 / 電鍍 ---
st.header("✨ 拋光 / 電鍍")
p_col1, p_col2 = st.columns(2)
do_polish = p_col1.checkbox("拋光基礎 $300")
p_pendant = p_col2.checkbox("小墜子 $200")
p_ear = p_col1.checkbox("單邊耳環 $150")
p_neck = p_col2.checkbox("項鍊手鍊 $800")
p_electro = st.checkbox("純電鍍 $100")

polish_cost = 0
if do_polish: polish_cost += 300
if p_pendant: polish_cost += 200
if p_ear: polish_cost += 150
if p_neck: polish_cost += 800
if p_electro: polish_cost += 100

if any([do_polish, p_pendant, p_ear, p_neck, p_electro]):
    ps_col1, ps_col2 = st.columns(2)
    if ps_col1.checkbox("白金/電鍍 +50"): polish_cost += 50
    if ps_col2.checkbox("雙色 +100"): polish_cost += 100
    if ps_col1.checkbox("打噴砂 +100"): polish_cost += 100
    if ps_col2.checkbox("寬版 +50"): polish_cost += 50
    if ps_col1.checkbox("克拉 +50"): polish_cost += 50

# --- F. 維修與設計 ---
st.header("🔧 維修與設計")
rep_c = st.number_input("C圈1點 ($100) 數量:", min_value=0, value=0)
rep_s = st.number_input("補字印 ($150) 數量:", min_value=0, value=0)
rep_crack = st.number_input("裂金 ($300) 數量:", min_value=0, value=0)
rep_stick = st.number_input("黏耳針 ($200) 數量:", min_value=0, value=0)
rep_claw = st.number_input("補爪支數 ($250):", min_value=0, value=0)
claw_w = st.number_input("補爪金料錢數:", min_value=0.0, value=0.0)

repair_cost = (rep_c*100) + (rep_s*150) + (rep_crack*300) + (rep_stick*200) + (rep_claw*250) + (claw_w*g_sell)
if st.checkbox("3D掃描 +500"): repair_cost += 500
if st.checkbox("基本製圖 +1500"): repair_cost += 1500

# --- 計算結果 ---
st.divider()
raw_total = (base_mold + (100 if mold_plat else 0) + (200 if mold_double else 0) + 
             total_stone_cost + resize_cost + polish_cost + repair_cost)

final_total = raw_total
discount_text = ""
if raw_total >= 6000:
    final_total = raw_total * 0.8
    discount_text = "(單件 8 折)"
elif raw_total >= 3000:
    final_total = raw_total * 0.9
    discount_text = "(單件 9 折)"

st.subheader(f"原始總計: ${int(raw_total)}")
st.title(f"應收金額: ${int(final_total)}")
if discount_text:
    st.success(discount_text)