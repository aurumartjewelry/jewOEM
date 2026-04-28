import tkinter as tk
from tkinter import ttk, messagebox
import csv
from datetime import datetime
import os

# --- 1. 核心價格邏輯 ---
def get_mold_labor_fee(w, material_type):
    """計算單件執模工費"""
    if w <= 0: return 0
    if w <= 0.5: base = 350
    elif w <= 1.0: base = 500
    elif w <= 2.0: base = 800
    else: base = 1000
    
    # 只有 Pt950 是 1.3 倍，750 和 585 視為一般 K金 (1.0)
    multiplier = 1.3 if material_type == "Pt950" else 1.0
    return int(base * multiplier)

def get_stone_price(w):
    if w <= 0: return 0
    if w <= 0.09: return 35
    if w <= 0.19: return 50
    if w <= 0.29: return 100
    if w <= 0.79: return 200
    if w <= 2.00: return 400
    if w <= 3.00: return 600
    return 800

# --- 2. 計算與存檔邏輯 ---
def calculate():
    try:
        g_sell = float(entry_gold_sell.get() or 0)
        p_sell_pt = float(entry_plat_sell_pt.get() or 0)

        # 頂部即時牌價
        v750 = int(g_sell * 0.75 * 1.3)
        v585 = int(g_sell * 0.585 * 1.3)
        vpt = int(p_sell_pt * 1.25)
        lbl_750.config(text=f"750: {v750}")
        lbl_585.config(text=f"585: {v585}")
        lbl_pt950.config(text=f"Pt950: {vpt}")

        price_map = {"750": v750, "585": v585, "Pt950": vpt}
        details = []

        # A. 執模台工與金料
        gold_total = 0
        labor_total = 0
        if var_do_mold.get():
            # 第一組
            m1 = var_m1.get()
            w1 = float(entry_w1.get() or 0)
            l1 = float(entry_l1.get() or 1.0) # 預設損耗 1.0 (不加)
            if w1 > 0:
                gold1 = price_map[m1] * w1 * l1
                gold_total += gold1
                labor1 = get_mold_labor_fee(w1, m1)
                labor_total += labor1
            
            # 第二組
            m2 = var_m2.get()
            w2 = float(entry_w2.get() or 0)
            l2 = float(entry_l2.get() or 1.0)
            if w2 > 0:
                gold2 = price_map[m2] * w2 * l2
                gold_total += gold2
                labor2 = get_mold_labor_fee(w2, m2)
                labor_total += labor2
            
            # 手動勾選組合件
            if var_is_combined.get():
                labor_total += 500
                details.append("組合費($500)")

            if gold_total > 0: details.append(f"金料(${int(gold_total)})")
            if labor_total > 0: details.append(f"執模工費(${int(labor_total)})")
            
        lbl_sub_a_gold.config(text=f"金料: ${int(gold_total)}")
        lbl_sub_a_labor.config(text=f"工費: ${int(labor_total)}")

        # B. 鑲嵌服務 (邏輯同前)
        sub_b = 0
        for w_e, c_e, v_c in stone_rows:
            w = float(w_e.get() or 0); count = int(c_e.get() or 0)
            if count > 0:
                p = (get_stone_price(w) + (50 if v_c.get() else 0)) * count
                sub_b += p
                details.append(f"標鑲{w}ct*{count}")
        for p_ct_e, tw_e in carat_rows:
            p_per_ct = float(p_ct_e.get() or 0); total_w = float(tw_e.get() or 0)
            if total_w > 0 and p_per_ct > 0:
                sub_b += (p_per_ct * total_w)
                details.append(f"克拉鑲({total_w}ct)")
        mp = float(manual_p.get() or 0); mc = int(manual_c.get() or 0)
        if mc > 0:
            sub_b += (mp + (50 if manual_v.get() else 0)) * mc
            details.append(f"手動鑲*{mc}")
        lbl_sub_b.config(text=f"小計: ${int(sub_b)}")

        # C. 改圍加價
        sub_c = 0
        if var_do_resize.get():
            sub_c = 300
            if var_r_plat.get(): sub_c += 100
            if var_r_wide.get(): sub_c += 100
            if var_r_back.get(): sub_c += 100
            if var_r_full.get(): sub_c += 100
            if var_r_big.get():
                bw = float(entry_big_w.get() or 0)
                mat_price = g_sell if var_r_big_mat.get() == 1 else p_sell_pt
                sub_c += 200 + (bw * mat_price)
            details.append(f"改圍(${int(sub_c)})")
        lbl_sub_c.config(text=f"小計: ${int(sub_c)}")

        # D. 拋光 / 電鍍
        sub_d = 0
        if var_pol_300.get(): sub_d += 300
        if var_pol_pen.get(): sub_d += 200
        if var_pol_ear.get(): sub_d += 150
        if var_pol_neck.get(): sub_d += 800
        if var_pol_pure.get(): sub_d += 100
        if var_pol_white.get(): sub_d += 50
        if var_pol_double.get(): sub_d += 100
        if var_pol_sand.get(): sub_d += 100
        if var_pol_wide.get(): sub_d += 50
        if var_pol_carat.get(): sub_d += 50
        lbl_sub_d.config(text=f"小計: ${sub_d}")
        if sub_d > 0: details.append(f"拋光電鍍(${sub_d})")

        # E. 維修設計
        sub_e = (int(rep_c.get() or 0) * 100) + float(entry_laser_fee.get() or 0)
        comb_c = int(rep_combine.get() or 0); comb_w = float(entry_rep_gold.get() or 0)
        comb_mat_p = g_sell if var_rep_comb_mat.get() == 1 else p_sell_pt
        sub_e += (comb_c * 200) + (comb_w * comb_mat_p)
        las_p = float(rep_laser_p.get() or 0); las_w = float(entry_laser_w.get() or 0)
        las_mat_p = g_sell if var_laser_mat.get() == 1 else p_sell_pt
        sub_e += las_p + (las_w * las_mat_p)
        
        if var_eng_1.get() == 1: sub_e += 50
        elif var_eng_1.get() == 2: sub_e += 100
        if var_rotary.get(): sub_e += 250
        if var_pattern.get(): sub_e += 500
        if var_3d.get(): sub_e += 500
        if var_draw.get(): sub_e += 1500
        lbl_sub_e.config(text=f"小計: ${int(sub_e)}")
        if sub_e > 0: details.append(f"維修設計(${int(sub_e)})")

        # 總計
        total = gold_total + labor_total + sub_b + sub_c + sub_d + sub_e
        result_label.config(text=f"應收總金額: ${int(total)}", fg="red")
        return int(total), " | ".join(details)
    except Exception:
        result_label.config(text="格式錯誤，請檢查輸入", fg="blue")
        return None, None

def clear_all():
    var_do_mold.set(False); var_is_combined.set(False)
    for v_m, e_w, e_l in [(var_m1, entry_w1, entry_l1), (var_m2, entry_w2, entry_l2)]:
        v_m.set("750"); e_w.delete(0, tk.END); e_w.insert(0, "0"); e_l.delete(0, tk.END); e_l.insert(0, "1.0")
    # ... 其他清除邏輯 (略)
    result_label.config(text="請點擊計算", fg="black")

def save_to_csv():
    res_tuple = calculate()
    if res_tuple[0] is None: return
    total_amt, details_str = res_tuple
    fn = "報價紀錄.csv"
    row = [datetime.now().strftime("%Y-%m-%d %H:%M"), entry_gold_sell.get(), total_amt, details_str, entry_note.get("1.0", tk.END).strip()]
    try:
        file_exists = os.path.isfile(fn)
        with open(fn, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f); 
            if not file_exists: writer.writerow(["時間", "金價", "金額", "明細", "備註"])
            writer.writerow(row)
        messagebox.showinfo("成功", "紀錄已儲存")
    except Exception:
        messagebox.showerror("錯誤", "寫入失敗，請關閉該 CSV 檔案後重試。")

# --- UI 介面 ---
root = tk.Tk(); root.title("金工報價系統 v6.9"); root.geometry("580x1100")

# 頂部牌價
f_top = tk.Frame(root, pady=10); f_top.pack(fill="x", padx=10)
tk.Label(f_top, text="黃金賣:").pack(side="left"); entry_gold_sell = tk.Entry(f_top, width=7); entry_gold_sell.insert(0,"0"); entry_gold_sell.pack(side="left", padx=2)
tk.Label(f_top, text="白金賣:").pack(side="left"); entry_plat_sell_pt = tk.Entry(f_top, width=7); entry_plat_sell_pt.insert(0,"0"); entry_plat_sell_pt.pack(side="left", padx=2)
lbl_750 = tk.Label(f_top, text="750: -", font=("", 10, "bold"), fg="#D4AF37"); lbl_750.pack(side="left", padx=5)
lbl_585 = tk.Label(f_top, text="585: -", font=("", 10, "bold"), fg="#E5AA70"); lbl_585.pack(side="left", padx=5)
lbl_pt950 = tk.Label(f_top, text="Pt950: -", font=("", 10, "bold"), fg="#4682B4"); lbl_pt950.pack(side="left", padx=5)

# 1. 執模台工與金料 (新版)
f1 = tk.LabelFrame(root, text="🛠️ 執模台工 & 金料計算", font=("", 10, "bold"), labelanchor="n"); f1.pack(fill="x", padx=10, pady=2)
lbl_sub_a_gold = tk.Label(f1, text="金料: $0", fg="darkgreen"); lbl_sub_a_gold.place(relx=0.75, y=-2)
lbl_sub_a_labor = tk.Label(f1, text="工費: $0", fg="blue"); lbl_sub_a_labor.place(relx=0.75, y=15)

var_do_mold = tk.BooleanVar(); tk.Checkbutton(f1, text="啟用執模/金料服務", variable=var_do_mold, font=("", 9, "bold")).pack()

f1_head = tk.Frame(f1); f1_head.pack()
tk.Label(f1_head, text="材質", width=8).grid(row=0, column=0); tk.Label(f1_head, text="重量(錢)", width=10).grid(row=0, column=1); tk.Label(f1_head, text="損耗(倍率)", width=10).grid(row=0, column=2)

# 第一組
f1_r1 = tk.Frame(f1); f1_r1.pack(pady=2)
var_m1 = tk.StringVar(value="750")
ttk.Combobox(f1_r1, textvariable=var_m1, values=["750", "585", "Pt950"], width=6, state="readonly").pack(side="left", padx=5)
entry_w1 = tk.Entry(f1_r1, width=8); entry_w1.insert(0,"0"); entry_w1.pack(side="left", padx=5)
entry_l1 = tk.Entry(f1_r1, width=8); entry_l1.insert(0,"1.0"); entry_l1.pack(side="left", padx=5)

# 第二組
f1_r2 = tk.Frame(f1); f1_r2.pack(pady=2)
var_m2 = tk.StringVar(value="750")
ttk.Combobox(f1_r2, textvariable=var_m2, values=["750", "585", "Pt950"], width=6, state="readonly").pack(side="left", padx=5)
entry_w2 = tk.Entry(f1_r2, width=8); entry_w2.insert(0,"0"); entry_w2.pack(side="left", padx=5)
entry_l2 = tk.Entry(f1_r2, width=8); entry_l2.insert(0,"1.0"); entry_l2.pack(side="left", padx=5)

var_is_combined = tk.BooleanVar(); tk.Checkbutton(f1, text="組合件/雙色 (工費另計+$500)", variable=var_is_combined, fg="red").pack()

# --- 2. 鑲嵌服務 (同前版本) ---
f2 = tk.LabelFrame(root, text="💎 鑲嵌服務", font=("", 10, "bold"), labelanchor="n"); f2.pack(fill="x", padx=10, pady=2)
lbl_sub_b = tk.Label(f2, text="小計: $0", fg="blue"); lbl_sub_b.place(relx=0.8, y=-2)
stone_rows = []
for i in range(3):
    r = tk.Frame(f2); r.pack()
    tk.Label(r, text="重:").pack(side="left"); we = tk.Entry(r, width=5); we.insert(0,"0"); we.pack(side="left")
    tk.Label(r, text="ct 數:").pack(side="left"); ce = tk.Entry(r, width=4); ce.insert(0,"0"); ce.pack(side="left")
    vc = tk.BooleanVar(); tk.Checkbutton(r, text="造型爪+50", variable=vc).pack(side="left"); stone_rows.append((we, ce, vc))
tk.Label(f2, text="--- 克拉單價與手動鑲 ---", fg="gray", font=("", 8)).pack()
carat_rows = []
for i in range(2):
    r = tk.Frame(f2); r.pack(pady=1)
    tk.Label(r, text="$:").pack(side="left"); pe = tk.Entry(r, width=7); pe.insert(0,"0"); pe.pack(side="left")
    tk.Label(r, text="/ct 總重:").pack(side="left"); twe = tk.Entry(r, width=6); twe.insert(0,"0"); twe.pack(side="left"); carat_rows.append((pe, twe))
r_m = tk.Frame(f2); r_m.pack()
manual_p = tk.Entry(r_m, width=7); manual_p.insert(0,"0"); manual_p.pack(side="left"); tk.Label(r_m, text="單價").pack(side="left")
manual_c = tk.Entry(r_m, width=4); manual_c.insert(0,"0"); manual_c.pack(side="left"); tk.Label(r_m, text="顆").pack(side="left"); manual_v = tk.BooleanVar(); tk.Checkbutton(r_m, text="造型爪", variable=manual_v).pack(side="left")

# --- 3. 改圍加價 ---
f3 = tk.LabelFrame(root, text="💍 改圍加價", font=("", 10, "bold"), labelanchor="n"); f3.pack(fill="x", padx=10, pady=2)
lbl_sub_c = tk.Label(f3, text="小計: $0", fg="blue"); lbl_sub_c.place(relx=0.8, y=-2)
var_do_resize = tk.BooleanVar(); tk.Checkbutton(f3, text="啟用改圍基礎$300", variable=var_do_resize).pack()
f3_r = tk.Frame(f3); f3_r.pack()
var_r_plat = tk.BooleanVar(); tk.Checkbutton(f3_r, text="白金+100", variable=var_r_plat).grid(row=0, column=0); var_r_wide = tk.BooleanVar(); tk.Checkbutton(f3_r, text="寬版+100", variable=var_r_wide).grid(row=0, column=1)
var_r_back = tk.BooleanVar(); tk.Checkbutton(f3_r, text="封底+100", variable=var_r_back).grid(row=1, column=0); var_r_full = tk.BooleanVar(); tk.Checkbutton(f3_r, text="滿鑽+100", variable=var_r_full).grid(row=1, column=1)
f3_b = tk.Frame(f3); f3_b.pack()
var_r_big = tk.BooleanVar(); tk.Checkbutton(f3_b, text="改大+200 金料(錢):", variable=var_r_big).pack(side="left")
entry_big_w = tk.Entry(f3_b, width=5); entry_big_w.insert(0,"0"); entry_big_w.pack(side="left")
var_r_big_mat = tk.IntVar(value=1); tk.Radiobutton(f3_b, text="金", variable=var_r_big_mat, value=1).pack(side="left"); tk.Radiobutton(f3_b, text="白", variable=var_r_big_mat, value=2).pack(side="left")

# --- 4. 拋光 / 電鍍 ---
f4 = tk.LabelFrame(root, text="✨ 拋光 / 電鍍", font=("", 10, "bold"), labelanchor="n"); f4.pack(fill="x", padx=10, pady=2)
lbl_sub_d = tk.Label(f4, text="小計: $0", fg="blue"); lbl_sub_d.place(relx=0.8, y=-2)
f4_grid = tk.Frame(f4); f4_grid.pack()
var_pol_300 = tk.BooleanVar(); tk.Checkbutton(f4_grid, text="拋光$300", variable=var_pol_300).grid(row=0, column=0)
var_pol_pen = tk.BooleanVar(); tk.Checkbutton(f4_grid, text="小墜$200", variable=var_pol_pen).grid(row=0, column=1)
var_pol_ear = tk.BooleanVar(); tk.Checkbutton(f4_grid, text="單耳$150", variable=var_pol_ear).grid(row=1, column=0)
var_pol_neck = tk.BooleanVar(); tk.Checkbutton(f4_grid, text="鍊類$800", variable=var_pol_neck).grid(row=1, column=1)
var_pol_pure = tk.BooleanVar(); tk.Checkbutton(f4, text="純電鍍 $100", variable=var_pol_pure).pack()
f4_opt = tk.Frame(f4); f4_opt.pack()
var_pol_white = tk.BooleanVar(); tk.Checkbutton(f4_opt, text="白金+50", variable=var_pol_white).grid(row=0, column=0)
var_pol_double = tk.BooleanVar(); tk.Checkbutton(f4_opt, text="雙色+100", variable=var_pol_double).grid(row=0, column=1)
var_pol_sand = tk.BooleanVar(); tk.Checkbutton(f4_opt, text="噴砂+100", variable=var_pol_sand).grid(row=1, column=0)
var_pol_wide = tk.BooleanVar(); tk.Checkbutton(f4_opt, text="寬版+50", variable=var_pol_wide).grid(row=1, column=1)
var_pol_carat = tk.BooleanVar(); tk.Checkbutton(f4, text="克拉+50", variable=var_pol_carat).pack()

# --- 5. 維修設計 ---
f5 = tk.LabelFrame(root, text="🔨 維修設計", font=("", 10, "bold"), labelanchor="n"); f5.pack(fill="x", padx=10, pady=2)
lbl_sub_e = tk.Label(f5, text="小計: $0", fg="blue"); lbl_sub_e.place(relx=0.8, y=-2)
rep_c = tk.Entry(tk.Frame(f5), width=8); tk.Label(f5, text="鈎鍊+雷射($100):").pack(side="left"); rep_c.insert(0,"0"); rep_c.pack() # 簡化顯示
entry_laser_fee = tk.Entry(tk.Frame(f5), width=8); tk.Label(f5, text="雷射金額($):").pack(side="left"); entry_laser_fee.insert(0,"0"); entry_laser_fee.pack()

f5_comb = tk.Frame(f5); f5_comb.pack()
tk.Label(f5_comb, text="黏耳/補爪($200):").pack(side="left"); rep_combine = tk.Entry(f5_comb, width=5); rep_combine.insert(0,"0"); rep_combine.pack(side="left")
tk.Label(f5_comb, text=" 金(錢):").pack(side="left"); entry_rep_gold = tk.Entry(f5_comb, width=5); entry_rep_gold.insert(0,"0"); entry_rep_gold.pack(side="left")
var_rep_comb_mat = tk.IntVar(value=1); tk.Radiobutton(f5_comb, text="金", variable=var_rep_comb_mat, value=1).pack(side="left"); tk.Radiobutton(f5_comb, text="白", variable=var_rep_comb_mat, value=2).pack(side="left")

f5_laser = tk.Frame(f5); f5_laser.pack()
tk.Label(f5_laser, text="補金($):").pack(side="left"); rep_laser_p = tk.Entry(f5_laser, width=6); rep_laser_p.insert(0,"0"); rep_laser_p.pack(side="left")
tk.Label(f5_laser, text=" 金(錢):").pack(side="left"); entry_laser_w = tk.Entry(f5_laser, width=5); entry_laser_w.insert(0,"0"); entry_laser_w.pack(side="left")
var_laser_mat = tk.IntVar(value=1); tk.Radiobutton(f5_laser, text="金", variable=var_laser_mat, value=1).pack(side="left"); tk.Radiobutton(f5_laser, text="白", variable=var_laser_mat, value=2).pack(side="left")

f5_eng = tk.Frame(f5); f5_eng.pack(); var_eng_1 = tk.IntVar(value=0)
tk.Radiobutton(f5_eng, text="1-5字($50)", variable=var_eng_1, value=1).pack(side="left"); tk.Radiobutton(f5_eng, text="5-10/LOGO($100)", variable=var_eng_1, value=2).pack(side="left")
var_rotary = tk.BooleanVar(); tk.Checkbutton(f5_eng, text="旋轉台(+250)", variable=var_rotary).pack(side="left")

f5_misc = tk.Frame(f5); f5_misc.pack()
var_pattern = tk.BooleanVar(); tk.Checkbutton(f5_misc, text="特殊圖案(+$500)", variable=var_pattern).pack(side="left")
var_3d = tk.BooleanVar(); tk.Checkbutton(f5_misc, text="3D(+500)", variable=var_3d).pack(side="left"); var_draw = tk.BooleanVar(); tk.Checkbutton(f5_misc, text="製圖(+1500)", variable=var_draw).pack(side="left")

# 備註與按鈕
tk.Label(root, text="📝 備註").pack()
entry_note = tk.Text(root, width=55, height=2, font=("", 10)); entry_note.pack(padx=10)
btn_f = tk.Frame(root, pady=10); btn_f.pack()
tk.Button(btn_f, text="計算總金額", command=calculate, bg="orange", font=("", 11, "bold"), width=12).pack(side="left", padx=5)
tk.Button(btn_f, text="儲存紀錄", command=save_to_csv, bg="#90EE90", width=12).pack(side="left", padx=5)
result_label = tk.Label(root, text="請點擊計算", font=("", 16, "bold"), pady=10); result_label.pack()

root.mainloop()