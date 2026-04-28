import tkinter as tk
from tkinter import ttk, messagebox
import csv
from datetime import datetime
import os

# --- 1. 核心邏輯計算 ---
def get_mold_labor_fee(w, material_type):
    """計算單件執模工費，Pt950 加成 1.3"""
    if w <= 0: return 0
    if w <= 0.5: base = 350
    elif w <= 1.0: base = 500
    elif w <= 2.0: base = 800
    else: base = 1000
    
    multiplier = 1.3 if material_type == "Pt950" else 1.0
    return int(base * multiplier)

def get_stone_price(w):
    """標準鑲嵌單價表"""
    if w <= 0: return 0
    if w <= 0.09: return 35
    if w <= 0.19: return 50
    if w <= 0.29: return 100
    if w <= 0.79: return 200
    if w <= 2.00: return 400
    if w <= 3.00: return 600
    return 800

# --- 2. 主計算功能 ---
def calculate():
    try:
        g_sell = float(entry_gold_sell.get() or 0)
        p_sell_pt = float(entry_plat_sell_pt.get() or 0)

        # 更新即時參考牌價
        v750 = int(g_sell * 0.75 * 1.3)
        v585 = int(g_sell * 0.585 * 1.3)
        vpt = int(p_sell_pt * 1.25)
        lbl_750.config(text=f"750: {v750}")
        lbl_585.config(text=f"585: {v585}")
        lbl_pt950.config(text=f"Pt950: {vpt}")

        price_map = {"750": v750, "585": v585, "Pt950": vpt}
        details = []

        # A. 執模台工與金料 (新邏輯)
        gold_total = 0
        labor_total = 0
        if var_do_mold.get():
            # 第一組計算
            m1 = var_m1.get(); w1 = float(entry_w1.get() or 0); l1 = float(entry_l1.get() or 1.0)
            if w1 > 0:
                gold_total += price_map[m1] * w1 * l1
                labor_total += get_mold_labor_fee(w1, m1)
            
            # 第二組計算
            m2 = var_m2.get(); w2 = float(entry_w2.get() or 0); l2 = float(entry_l2.get() or 1.0)
            if w2 > 0:
                gold_total += price_map[m2] * w2 * l2
                labor_total += get_mold_labor_fee(w2, m2)
            
            # 組合件勾選
            if var_is_combined.get():
                labor_total += 500
                details.append("組合加收($500)")

            if gold_total > 0: details.append(f"金料(${int(gold_total)})")
            if labor_total > 0: details.append(f"執模工費(${int(labor_total)})")
            
        lbl_sub_a_gold.config(text=f"金料: ${int(gold_total)}")
        lbl_sub_a_labor.config(text=f"工費: ${int(labor_total)}")

        # B. 鑲嵌服務
        sub_b = 0
        for w_e, c_e, v_c in stone_rows:
            w = float(w_e.get() or 0); count = int(c_e.get() or 0)
            if count > 0:
                sub_b += (get_stone_price(w) + (50 if v_c.get() else 0)) * count
        for p_ct_e, tw_e in carat_rows:
            p_per_ct = float(p_ct_e.get() or 0); total_w = float(tw_e.get() or 0)
            if total_w > 0: sub_b += (p_per_ct * total_w)
        mp = float(manual_p.get() or 0); mc = int(manual_c.get() or 0)
        if mc > 0: sub_b += (mp + (50 if manual_v.get() else 0)) * mc
        lbl_sub_b.config(text=f"小計: ${int(sub_b)}")

        # C. 改圍與拋光 (略，保持前版本邏輯)
        # ... (此處省略部分重複邏輯以節省篇幅)

        # E. 維修設計 (更新項目)
        sub_e = (int(rep_c.get() or 0) * 100) + float(entry_laser_fee.get() or 0)
        
        # 補金計算 (補金工資 + 金料)
        las_p = float(rep_laser_p.get() or 0); las_w = float(entry_laser_w.get() or 0)
        las_mat_p = g_sell if var_laser_mat.get() == 1 else p_sell_pt
        sub_e += las_p + (las_w * las_mat_p)
        
        # 刻字與旋轉台
        if var_eng_1.get() == 1: sub_e += 50
        elif var_eng_1.get() == 2: sub_e += 100
        if var_rotary.get(): sub_e += 250
        
        lbl_sub_e.config(text=f"小計: ${int(sub_e)}")

        total = gold_total + labor_total + sub_b + (300 if var_do_resize.get() else 0) + sub_e # 簡化範例
        result_label.config(text=f"應收總金額: ${int(total)}", fg="red")
        return int(total)
    except:
        result_label.config(text="輸入格式錯誤", fg="blue")

# --- 3. UI 介面佈局 ---
root = tk.Tk(); root.title("金工報價系統 v7.0"); root.geometry("580x950")

# 今日牌價
f0 = tk.Frame(root, pady=5); f0.pack(fill="x", padx=10)
tk.Label(f0, text="黃金賣:").pack(side="left"); entry_gold_sell = tk.Entry(f0, width=8); entry_gold_sell.pack(side="left")
tk.Label(f0, text=" 白金賣:").pack(side="left"); entry_plat_sell_pt = tk.Entry(f0, width=8); entry_plat_sell_pt.pack(side="left")
lbl_750 = tk.Label(f0, text="750: -", fg="#D4AF37", font=("", 9, "bold")); lbl_750.pack(side="left", padx=5)
lbl_pt950 = tk.Label(f0, text="Pt950: -", fg="#4682B4", font=("", 9, "bold")); lbl_pt950.pack(side="left", padx=5)

# A. 執模與金料計算區
f1 = tk.LabelFrame(root, text="🛠️ 執模台工 & 金料 (工料分離)", font=("", 10, "bold")); f1.pack(fill="x", padx=10, pady=5)
var_do_mold = tk.BooleanVar(); tk.Checkbutton(f1, text="啟用計算", variable=var_do_mold).pack(anchor="w")

# 顯示小計
lbl_sub_a_gold = tk.Label(f1, text="金料: $0", fg="darkgreen"); lbl_sub_a_gold.place(relx=0.7, y=10)
lbl_sub_a_labor = tk.Label(f1, text="工費: $0", fg="blue"); lbl_sub_a_labor.place(relx=0.7, y=30)

# 計算列
for i in range(2):
    r = tk.Frame(f1); r.pack(pady=2)
    var_m = tk.StringVar(value="750") if i==0 else tk.StringVar(value="750")
    if i==0: var_m1 = var_m; entry_w1 = tk.Entry(r, width=7); entry_l1 = tk.Entry(r, width=5)
    else: var_m2 = var_m; entry_w2 = tk.Entry(r, width=7); entry_l2 = tk.Entry(r, width=5)
    
    ttk.Combobox(r, textvariable=var_m, values=["750", "585", "Pt950"], width=6).pack(side="left", padx=2)
    tk.Label(r, text="重:").pack(side="left"); (entry_w1 if i==0 else entry_w2).pack(side="left")
    tk.Label(r, text=" 損耗:").pack(side="left"); (entry_l1 if i==0 else entry_l2).pack(side="left")
    (entry_w1 if i==0 else entry_w2).insert(0,"0"); (entry_l1 if i==0 else entry_l2).insert(0,"1.0")

var_is_combined = tk.BooleanVar()
tk.Checkbutton(f1, text="組合件/雙色 (工費另加 $500)", variable=var_is_combined, fg="red").pack()

# E. 維修與刻字 (重點更新區)
f5 = tk.LabelFrame(root, text="🔨 維修設計", font=("", 10, "bold")); f5.pack(fill="x", padx=10, pady=5)
lbl_sub_e = tk.Label(f5, text="小計: $0", fg="blue"); lbl_sub_e.place(relx=0.8, y=-2)

r1 = tk.Frame(f5); r1.pack(anchor="w")
tk.Label(r1, text="鈎鍊+雷射($100):").pack(side="left"); rep_c = tk.Entry(r1, width=5); rep_c.insert(0,"0"); rep_c.pack(side="left")
tk.Label(r1, text="  雷射金額($):").pack(side="left"); entry_laser_fee = tk.Entry(r1, width=8); entry_laser_fee.insert(0,"0"); entry_laser_fee.pack(side="left")

r2 = tk.Frame(f5); r2.pack(anchor="w", pady=5)
tk.Label(r2, text="補金(工):").pack(side="left"); rep_laser_p = tk.Entry(r2, width=6); rep_laser_p.insert(0,"0"); rep_laser_p.pack(side="left")
tk.Label(r2, text=" 金料(錢):").pack(side="left"); entry_laser_w = tk.Entry(r2, width=5); entry_laser_w.insert(0,"0"); entry_laser_w.pack(side="left")
var_laser_mat = tk.IntVar(value=1); tk.Radiobutton(r2, text="金", variable=var_laser_mat, value=1).pack(side="left"); tk.Radiobutton(r2, text="白", variable=var_laser_mat, value=2).pack(side="left")

r3 = tk.Frame(f5); r3.pack(anchor="w")
var_eng_1 = tk.IntVar(value=0)
tk.Radiobutton(r3, text="1-5字($50)", variable=var_eng_1, value=1).pack(side="left")
tk.Radiobutton(r3, text="5-10字/LOGO($100)", variable=var_eng_1, value=2).pack(side="left")
var_rotary = tk.BooleanVar(); tk.Checkbutton(r3, text="旋轉台(+250)", variable=var_rotary, fg="purple").pack(side="left")

# 底部按鈕
tk.Button(root, text="計算總金額", command=calculate, bg="orange", font=("", 12, "bold"), pady=5).pack(fill="x", padx=50, pady=10)
result_label = tk.Label(root, text="請點擊計算", font=("", 16, "bold")); result_label.pack()

root.mainloop()