import streamlit as st

RING_SIZES = {
    4: 40.8, 5: 42.4, 6: 44.0, 7: 45.6, 8: 47.1, 9: 48.7, 10: 50.3, 11: 51.8,
    12: 53.4, 13: 55.0, 14: 56.5, 15: 58.1, 16: 59.7, 17: 61.3, 18: 62.8, 19: 64.4,
    20: 66.0, 21: 67.6, 22: 69.1, 23: 70.7, 24: 72.3, 25: 73.8, 26: 75.4, 27: 77.0,
    28: 78.5, 29: 80.1, 30: 81.7
}
DENSITY = {"750": 15.6, "585": 13.2, "Pt950": 21.45}  # g/cm³, estimate
RATIO = {"750": 0.750, "585": 0.585, "Pt950": 0.950}
GRAMS_PER_QIAN = 3.75

st.set_page_config(page_title="戒圍改大補金估算器", page_icon="💍", layout="centered")

st.title("💍 戒圍改大補金估算器")
st.caption("台灣國際圍｜補料金料與金料成本估算")

st.subheader("輸入條件")

col1, col2 = st.columns(2)
with col1:
    fineness = st.selectbox("成色", ["750", "585", "Pt950"])
    from_size = st.selectbox("原戒圍", list(RING_SIZES.keys()), index=8)  # 12
with col2:
    to_size = st.selectbox("改至戒圍", list(RING_SIZES.keys()), index=10)  # 14

col3, col4 = st.columns(2)
with col3:
    width = st.number_input("戒腳寬度（mm）", min_value=0.0, value=2.00, step=0.01, format="%.2f")
with col4:
    thickness = st.number_input("戒腳厚度（mm）", min_value=0.0, value=1.70, step=0.01, format="%.2f")

col5, col6 = st.columns(2)
with col5:
    factor = st.number_input("加工係數", min_value=1.0, value=1.15, step=0.01, format="%.2f")
with col6:
    price = st.number_input("金價（每錢）", min_value=0.0, value=0.0, step=1.0, format="%.0f")

st.divider()
st.subheader("估算結果")

if to_size <= from_size:
    st.warning("請輸入改大的戒圍（改至戒圍需大於原戒圍）")
elif width <= 0 or thickness <= 0 or factor < 1:
    st.warning("請輸入有效的寬度、厚度與加工係數")
else:
    diff = to_size - from_size
    circ = RING_SIZES[to_size] - RING_SIZES[from_size]
    volume = width * thickness * circ
    tg = volume * DENSITY[fineness] / 1000
    rg = tg * factor
    tq = tg / GRAMS_PER_QIAN
    rq = rg / GRAMS_PER_QIAN

    r1c1, r1c2 = st.columns(2)
    r1c1.metric("增加圍數", f"{diff} 號")
    r1c2.metric("增加內圍長度", f"{circ:.2f} mm")

    r2c1, r2c2 = st.columns(2)
    r2c1.metric("理論成品增加重量", f"{tg:.3f} g")
    r2c2.metric("理論成品增加重量", f"{tq:.3f} 錢")

    r3c1, r3c2 = st.columns(2)
    r3c1.metric("建議投入補料金料", f"{rg:.3f} g")
    r3c2.metric("建議投入補料金料", f"{rq:.3f} 錢")

    if price <= 0:
        st.info("請輸入金價以估算金料成本")
    else:
        cost = rq * price * RATIO[fineness]
        st.metric("金料估算成本", f"{cost:,.0f} 元")

    st.caption("金料成本 = 建議投入重量（錢）× 金價 × 成色比例")

st.divider()
st.caption(
    "注意：估算的是加工前投入補料金料，不是完成改圍後的實際增重。"
    "密度與加工係數可依實際案件持續校正。"
)
