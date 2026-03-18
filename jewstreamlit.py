```python
import tkinter as tk
from tkinter import messagebox
import csv
from datetime import datetime
import os

# --- 1. 價格邏輯 ---
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

# --- 2. 核心計算邏輯 ---
def calculate():
    try:
        g_sell = float(entry_gold_sell.get() or 0)
        p_sell_pt = float(entry_plat_sell_pt.get() or 0)

        # 頂部牌價更新
        v750 = int(g_sell*0.75*1.3)
        v585 = int(g_sell*0.585*1.3)
        vpt = int(p_sell_pt*1.25)
        lbl_750.config(text=f"750: {v750}")
        lbl_585.config(text=f"585: {v585}")
        lbl_pt950.config(text=f"Pt950: {vpt}")

        details = []

        # A. 執模台工
        sub_a = 0
        if var_do_mold.get():
            w = float(entry_mold_w.get() or 0)
            sub_a = get_mold_price(w)
            if var_mold_plat.get(): sub_a += 100
            if var_mold_double.get(): sub_a += 200
            details.append(f"執模(${sub_a})")
        lbl_sub_a.config(text=f"小計: ${sub_a}")

        # B. 鑲嵌服務
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
                # 依據選擇的材質帶入單價
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
        sub_e = (int(rep_c.get() or 0) * 100) + (int(rep_s.get() or 0) * 150)
        
        # 黏耳針/補爪 ($200) + 金料(依材質)
        comb_c = int(rep_combine.get() or 0)
        comb_w = float(entry_rep_gold.get() or 0)
        comb_mat_p = g_sell if var_rep_comb_mat.get() == 1 else p_sell_pt
        sub_e += (comb_c * 200) + (comb_w * comb_mat_p)

        # 雷射補金 (自填工資 + 金料依材質)
        las_p = float(rep_laser_p.get() or 0)
        las_w = float(entry_laser_w.get() or 0)
        las_mat_p = g_sell if var_laser_mat.get() == 1 else p_sell_pt
        sub_e += las_p + (las_w * las_mat_p)
        
        if var_eng_1.get() == 1: sub_e += 50
        elif var_eng_1.get() == 2: sub_e += 100
        if var_pattern.get(): sub_e += 500
        if var_3d.get(): sub_e += 500
        if var_draw.get(): sub_e += 1500
        lbl_sub_e.config(text=f"小計: ${int(sub_e)}")
        if sub_e > 0: details.append(f"維修設計(${int(sub_e)})")

        # 總計
        total = sub_a + sub_b + sub_c + sub_d + sub_e
        result_label.config(text=f"應收總金額: ${int(total)}", fg="red")
        return int(total), " | ".join(details)
    except Exception:
        result_label.config(text="格式錯誤，請檢查輸入的數字", fg="blue")
        return None, None

def clear_all():
    var_do_mold.set(False); entry_mold_w.delete(0, tk.END); entry_mold_w.insert(0, "0")
    var_mold_plat.set(False); var_mold_double.set(False)
    for w, c, v in stone_rows:
        w.delete(0, tk.END); w.insert(0, "0"); c.delete(0, tk.END); c.insert(0, "0"); v.set(False)
    for p, tw in carat_rows:
        p.delete(0, tk.END); p.insert(0, "0"); tw.delete(0, tk.END); tw.insert(0, "0")
    manual_p.delete(0, tk.END); manual_p.insert(0, "0"); manual_c.delete(0, tk.END); manual_c.insert(0, "0"); manual_v.set(False)
    
    var_do_resize.set(False); var_r_plat.set(False); var_r_wide.set(False); var_r_back.set(False); var_r_full.set(False); var_r_big.set(False)
    entry_big_w.delete(0, tk.END); entry_big_w.insert(0, "0")
    var_r_big_mat.set(1) # 重設為金
    
    for v in [var_pol_300, var_pol_pen, var_pol_ear, var_pol_neck, var_pol_pure, var_pol_white, var_pol_double, var_pol_sand, var_pol_wide, var_pol_carat]:
        v.set(False)
    
    for e in [rep_c, rep_s, rep_combine, entry_rep_gold, rep_laser_p, entry_laser_w]:
        e.delete(0, tk.END); e.insert(0, "0")
    var_rep_comb_mat.set(1); var_laser_mat.set(1) # 重設為金
    
    var_eng_1.set(0); var_pattern.set(False); var_3d.set(False); var_draw.set(False)
    
    entry_note.delete("1.0", tk.END)
    result_label.config(text="請點擊計算", fg="black")
    for lbl in [lbl_sub_a, lbl_sub_b, lbl_sub_c, lbl_sub_d, lbl_sub_e]: lbl.config(text="小計: $0")

def save_to_csv():
    res_tuple = calculate()
    if res_tuple[0] is None: return
    total_amt, details_str = res_tuple
    note_text = entry_note.get("1.0", tk.END).strip()
    
    fn = "報價紀錄.csv"
    row = [datetime.now().strftime("%Y-%m-%d %H:%M"), entry_gold_sell.get(), total_amt, details_str, note_text]
    try:
        file_exists = os.path.isfile(fn)
        with open(fn, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            if not file_exists: writer.writerow(["時間", "金價", "金額", "明細", "備註"])
            writer.writerow(row)
        messagebox.showinfo("成功", "紀錄已儲存至 報價紀錄.csv")
    except Exception:
        messagebox.showerror("錯誤", "無法寫入檔案！請檢查 Excel 是否已開啟該檔案。")

# --- UI 介面 ---
root = tk.Tk(); root.title("金工報價系統 v6.5"); root.geometry("550x1100")

# 頂部牌價
f_top = tk.Frame(root, pady=10); f_top.pack(fill="x", padx=10)
tk.Label(f_top, text="黃金賣:").pack(side="left"); entry_gold_sell = tk.Entry(f_top, width=8); entry_gold_sell.insert(0,"0"); entry_gold_sell.pack(side="left", padx=5)
tk.Label(f_top, text="白金賣:").pack(side="left"); entry_plat_sell_pt = tk.Entry(f_top, width=8); entry_plat_sell_pt.insert(0,"0"); entry_plat_sell_pt.pack(side="left", padx=5)
lbl_750 = tk.Label(f_top, text="750: -", font=("Arial", 11, "bold"), fg="#D4AF37"); lbl_750.pack(side="left", padx=8)
lbl_585 = tk.Label(f_top, text="585: -", font=("Arial", 11, "bold"), fg="#E5AA70"); lbl_585.pack(side="left", padx=8)
lbl_pt950 = tk.Label(f_top, text="Pt950: -", font=("Arial", 11, "bold"), fg="#4682B4"); lbl_pt950.pack(side="left", padx=8)

# 1. 執模台工
f1 = tk.LabelFrame(root, text="🛠️ 執模台工", font=("", 10, "bold"), labelanchor="n"); f1.pack(fill="x", padx=10, pady=2)
lbl_sub_a = tk.Label(f1, text="小計: $0", fg="blue"); lbl_sub_a.place(relx=0.8, y=-2)
var_do_mold = tk.BooleanVar(); tk.Checkbutton(f1, text="啟用執模服務", variable=var_do_mold).pack()
f1_r = tk.Frame(f1); f1_r.pack()
tk.Label(f1_r, text="輸入重量:").pack(side="left"); entry_mold_w = tk.Entry(f1_r, width=8); entry_mold_w.insert(0,"0"); entry_mold_w.pack(side="left")
f1_chk = tk.Frame(f1); f1_chk.pack()
var_mold_plat = tk.BooleanVar(); tk.Checkbutton(f1_chk, text="白金+100", variable=var_mold_plat).pack(side="left", padx=20)
var_mold_double = tk.BooleanVar(); tk.Checkbutton(f1_chk, text="雙色+200", variable=var_mold_double).pack(side="left", padx=20)

# 2. 鑲嵌服務
f2 = tk.LabelFrame(root, text="💎 鑲嵌服務", font=("", 10, "bold"), labelanchor="n"); f2.pack(fill="x", padx=10, pady=2)
lbl_sub_b = tk.Label(f2, text="小計: $0", fg="blue"); lbl_sub_b.place(relx=0.8, y=-2)
stone_rows = []
for i in range(3):
    r = tk.Frame(f2); r.pack()
    tk.Label(r, text="重:").pack(side="left"); we = tk.Entry(r, width=5); we.insert(0,"0"); we.pack(side="left")
    tk.Label(r, text="ct 數:").pack(side="left"); ce = tk.Entry(r, width=4); ce.insert(0,"0"); ce.pack(side="left")
    vc = tk.BooleanVar(); tk.Checkbutton(r, text="造型爪+50", variable=vc).pack(side="left"); stone_rows.append((we, ce, vc))
tk.Label(f2, text="--- 克拉單價計算 (單價 × 總重) ---", fg="#0056b3", font=("", 9, "bold")).pack()
carat_rows = []
for i in range(3):
    r = tk.Frame(f2); r.pack(pady=1)
    tk.Label(r, text="$:").pack(side="left"); pe = tk.Entry(r, width=7); pe.insert(0,"0"); pe.pack(side="left")
    tk.Label(r, text="/ct 總重:").pack(side="left"); twe = tk.Entry(r, width=6); twe.insert(0,"0"); twe.pack(side="left"); carat_rows.append((pe, twe))
tk.Label(f2, text="--- 手動單價 ---", fg="green", font=("", 9)).pack()
r_m = tk.Frame(f2); r_m.pack()
manual_p = tk.Entry(r_m, width=7); manual_p.insert(0,"0"); manual_p.pack(side="left"); tk.Label(r_m, text="單價").pack(side="left")
manual_c = tk.Entry(r_m, width=4); manual_c.insert(0,"0"); manual_c.pack(side="left"); tk.Label(r_m, text="顆").pack(side="left")
manual_v = tk.BooleanVar(); tk.Checkbutton(r_m, text="造型爪", variable=manual_v).pack(side="left")

# 3. 改圍加價
f3 = tk.LabelFrame(root, text="💍 改圍加價", font=("", 10, "bold"), labelanchor="n"); f3.pack(fill="x", padx=10, pady=2)
lbl_sub_c = tk.Label(f3, text="小計: $0", fg="blue"); lbl_sub_c.place(relx=0.8, y=-2)
var_do_resize = tk.BooleanVar(); tk.Checkbutton(f3, text="啟用改圍基礎$300", variable=var_do_resize).pack()
f3_r = tk.Frame(f3); f3_r.pack()
var_r_plat = tk.BooleanVar(); tk.Checkbutton(f3_r, text="白金+100", variable=var_r_plat).grid(row=0, column=0); var_r_wide = tk.BooleanVar(); tk.Checkbutton(f3_r, text="寬版+100", variable=var_r_wide).grid(row=0, column=1)
var_r_back = tk.BooleanVar(); tk.Checkbutton(f3_r, text="封底+100", variable=var_r_back).grid(row=1, column=0); var_r_full = tk.BooleanVar(); tk.Checkbutton(f3_r, text="滿鑽+100", variable=var_r_full).grid(row=1, column=1)
f3_b = tk.Frame(f3); f3_b.pack()
var_r_big = tk.BooleanVar(); tk.Checkbutton(f3_b, text="改大+200 金料(錢):", variable=var_r_big).pack(side="left")
entry_big_w = tk.Entry(f3_b, width=5); entry_big_w.insert(0,"0"); entry_big_w.pack(side="left")
var_r_big_mat = tk.IntVar(value=1) # 1:金, 2:白金
tk.Radiobutton(f3_b, text="金", variable=var_r_big_mat, value=1).pack(side="left")
tk.Radiobutton(f3_b, text="白金", variable=var_r_big_mat, value=2).pack(side="left")

# 4. 拋光 / 電鍍
f4 = tk.LabelFrame(root, text="✨ 拋光 / 電鍍", font=("", 10, "bold"), labelanchor="n"); f4.pack(fill="x", padx=10, pady=2)
lbl_sub_d = tk.Label(f4, text="小計: $0", fg="blue"); lbl_sub_d.place(relx=0.8, y=-2)
f4_1 = tk.Frame(f4); f4_1.pack()
var_pol_300 = tk.BooleanVar(); tk.Checkbutton(f4_1, text="拋光$300", variable=var_pol_300).grid(row=0, column=0); var_pol_pen = tk.BooleanVar(); tk.Checkbutton(f4_1, text="小墜$200", variable=var_pol_pen).grid(row=0, column=1)
var_pol_ear = tk.BooleanVar(); tk.Checkbutton(f4_1, text="單耳$150", variable=var_pol_ear).grid(row=1, column=0); var_pol_neck = tk.BooleanVar(); tk.Checkbutton(f4_1, text="鍊類$800", variable=var_pol_neck).grid(row=1, column=1)
var_pol_pure = tk.BooleanVar(); tk.Checkbutton(f4, text="純電鍍 $100", variable=var_pol_pure).pack()
f4_2 = tk.Frame(f4); f4_2.pack()
var_pol_white = tk.BooleanVar(); tk.Checkbutton(f4_2, text="白金+50", variable=var_pol_white).grid(row=0, column=0); var_pol_double = tk.BooleanVar(); tk.Checkbutton(f4_2, text="雙色+100", variable=var_pol_double).grid(row=0, column=1)
var_pol_sand = tk.BooleanVar(); tk.Checkbutton(f4_2, text="噴砂+100", variable=var_pol_sand).grid(row=1, column=0); var_pol_wide = tk.BooleanVar(); tk.Checkbutton(f4_2, text="寬版+50", variable=var_pol_wide).grid(row=1, column=1)
var_pol_carat = tk.BooleanVar(); tk.Checkbutton(f4, text="克拉+50", variable=var_pol_carat).pack()

# 5. 維修設計
f5 = tk.LabelFrame(root, text="🔨 維修設計", font=("", 10, "bold"), labelanchor="n"); f5.pack(fill="x", padx=10, pady=2)
lbl_sub_e = tk.Label(f5, text="小計: $0", fg="blue"); lbl_sub_e.place(relx=0.8, y=-2)
def rep_row(parent, text):
    r = tk.Frame(parent); r.pack(); tk.Label(r, text=text, width=15).pack(side="left"); e = tk.Entry(r, width=8); e.insert(0,"0"); e.pack(side="left"); return e
rep_c = rep_row(f5, "C圈1點($100):"); rep_s = rep_row(f5, "補字印($150):")

# 黏耳針/補爪 + 材質選擇
f5_comb = tk.Frame(f5); f5_comb.pack()
tk.Label(f5_comb, text="黏耳針/補爪($200):").pack(side="left")
rep_combine = tk.Entry(f5_comb, width=5); rep_combine.insert(0,"0"); rep_combine.pack(side="left")
tk.Label(f5_comb, text=" 金料(錢):").pack(side="left")
entry_rep_gold = tk.Entry(f5_comb, width=5); entry_rep_gold.insert(0,"0"); entry_rep_gold.pack(side="left")
var_rep_comb_mat = tk.IntVar(value=1)
tk.Radiobutton(f5_comb, text="金", variable=var_rep_comb_mat, value=1).pack(side="left")
tk.Radiobutton(f5_comb, text="白金", variable=var_rep_comb_mat, value=2).pack(side="left")

# 新增：雷射補金 + 材質選擇
f5_laser = tk.Frame(f5); f5_laser.pack()
tk.Label(f5_laser, text="雷射補金($):").pack(side="left")
rep_laser_p = tk.Entry(f5_laser, width=6); rep_laser_p.insert(0,"0"); rep_laser_p.pack(side="left")
tk.Label(f5_laser, text=" 金料(錢):").pack(side="left")
entry_laser_w = tk.Entry(f5_laser, width=5); entry_laser_w.insert(0,"0"); entry_laser_w.pack(side="left")
var_laser_mat = tk.IntVar(value=1)
tk.Radiobutton(f5_laser, text="金", variable=var_laser_mat, value=1).pack(side="left")
tk.Radiobutton(f5_laser, text="白金", variable=var_laser_mat, value=2).pack(side="left")

f5_eng = tk.Frame(f5); f5_eng.pack(); var_eng_1 = tk.IntVar(value=0)
tk.Radiobutton(f5_eng, text="無", variable=var_eng_1, value=0).pack(side="left"); tk.Radiobutton(f5_eng, text="1-5字($50)", variable=var_eng_1, value=1).pack(side="left"); tk.Radiobutton(f5_eng, text="5-10字($100)", variable=var_eng_1, value=2).pack(side="left")
var_pattern = tk.BooleanVar(); tk.Checkbutton(f5_eng, text="特殊圖案(+$500)", variable=var_pattern).pack(side="left")
f5_misc = tk.Frame(f5); f5_misc.pack()
var_3d = tk.BooleanVar(); tk.Checkbutton(f5_misc, text="3D掃描(+500)", variable=var_3d).pack(side="left"); var_draw = tk.BooleanVar(); tk.Checkbutton(f5_misc, text="製圖(+1500)", variable=var_draw).pack(side="left")

# 備註欄
tk.Label(root, text="📝 備註").pack(pady=(10,0))
entry_note = tk.Text(root, width=55, height=3, font=("", 10)); entry_note.pack(padx=10)

# 底部按鈕區塊
btn_f = tk.Frame(root, pady=10); btn_f.pack()
tk.Button(btn_f, text="計算總金額", command=calculate, bg="orange", font=("", 11, "bold"), width=12).pack(side="left", padx=5)
tk.Button(btn_f, text="儲存至 Excel", command=save_to_csv, bg="#90EE90", font=("", 11, "bold"), width=12).pack(side="left", padx=5)
tk.Button(btn_f, text="清除全部", command=clear_all, bg="lightgray", font=("", 11, "bold"), width=10).pack(side="left", padx=5)

result_label = tk.Label(root, text="請點擊計算", font=("", 16, "bold"), pady=10); result_label.pack()

root.mainloop()
        )
