import tkinter as tk
from tkinter import ttk

RING_SIZES = {
    4:40.8,5:42.4,6:44.0,7:45.6,8:47.1,9:48.7,10:50.3,11:51.8,
    12:53.4,13:55.0,14:56.5,15:58.1,16:59.7,17:61.3,18:62.8,19:64.4,
    20:66.0,21:67.6,22:69.1,23:70.7,24:72.3,25:73.8,26:75.4,27:77.0,
    28:78.5,29:80.1,30:81.7
}
DENSITY = {"750":15.6, "585":13.2, "Pt950":21.45}  # g/cm³, estimate
RATIO = {"750":0.750, "585":0.585, "Pt950":0.950}
GRAMS_PER_QIAN = 3.75

class App:
    def __init__(self, root):
        self.root = root
        root.title("戒圍改大補金估算器")
        root.geometry("600x650")
        self.vars = {k:tk.StringVar(v) for k,v in {
            "fineness":"750","from_size":"12","to_size":"14",
            "width":"2.00","thickness":"1.70","factor":"1.15","price":""
        }.items()}
        self.out = {}
        self.build()
        self.calc()

    def build(self):
        f = ttk.Frame(self.root, padding=22); f.pack(fill="both", expand=True)
        ttk.Label(f,text="戒圍改大補金估算器",
                  font=("Microsoft JhengHei",22,"bold")).pack(anchor="w")
        ttk.Label(f,text="台灣國際圍｜補料金料與金料成本估算",
                  foreground="#666").pack(anchor="w",pady=(4,18))
        box=ttk.LabelFrame(f,text="輸入條件",padding=14); box.pack(fill="x")

        combos=[
            ("成色","fineness",["750","585","Pt950"]),
            ("原戒圍","from_size",[str(x) for x in RING_SIZES]),
            ("改至戒圍","to_size",[str(x) for x in RING_SIZES])
        ]
        for r,(lab,key,vals) in enumerate(combos):
            ttk.Label(box,text=lab).grid(row=r,column=0,sticky="w",pady=6)
            c=ttk.Combobox(box,textvariable=self.vars[key],values=vals,
                           state="readonly",width=20)
            c.grid(row=r,column=1,sticky="ew",pady=6)
            c.bind("<<ComboboxSelected>>",lambda e:self.calc())

        entries=[
            ("戒腳寬度（mm）","width"),("戒腳厚度（mm）","thickness"),
            ("加工係數","factor"),("金價（每錢）","price")
        ]
        for r,(lab,key) in enumerate(entries,3):
            ttk.Label(box,text=lab).grid(row=r,column=0,sticky="w",pady=6)
            e=ttk.Entry(box,textvariable=self.vars[key],width=22)
            e.grid(row=r,column=1,sticky="ew",pady=6)
            e.bind("<KeyRelease>",lambda e:self.calc())
        box.columnconfigure(1,weight=1)

        ttk.Button(f,text="計算",command=self.calc).pack(fill="x",pady=15)

        out=ttk.LabelFrame(f,text="估算結果",padding=14); out.pack(fill="x")
        rows=[
            ("增加圍數","diff","號"),("增加內圍長度","circ","mm"),
            ("理論成品增加重量","tg","g"),("理論成品增加重量","tq","錢"),
            ("建議投入補料金料","rg","g"),("建議投入補料金料","rq","錢"),
            ("金料估算成本","cost","")
        ]
        for r,(lab,key,unit) in enumerate(rows):
            ttk.Label(out,text=lab).grid(row=r,column=0,sticky="w",pady=4)
            v=tk.StringVar(value="—"); self.out[key]=v
            ttk.Label(out,textvariable=v,font=("Microsoft JhengHei",12,"bold")
                      ).grid(row=r,column=1,sticky="e",pady=4)
            if unit: ttk.Label(out,text=unit).grid(row=r,column=2,sticky="w",padx=5)
        ttk.Label(out,text="金料成本 = 建議投入重量（錢） × 金價 × 成色比例",
                  foreground="#666").grid(row=7,column=0,columnspan=3,sticky="w",pady=(10,0))

        ttk.Label(f,text="注意：估算的是加工前投入補料金料，不是完成改圍後的實際增重。"
                  "密度與加工係數可依實際案件持續校正。",
                  foreground="#666",wraplength=540,justify="left"
                  ).pack(anchor="w",pady=16)

    def calc(self):
        try:
            fin=self.vars["fineness"].get()
            a=int(self.vars["from_size"].get()); b=int(self.vars["to_size"].get())
            w=float(self.vars["width"].get()); t=float(self.vars["thickness"].get())
            factor=float(self.vars["factor"].get())
        except ValueError:
            return
        if w<=0 or t<=0 or factor<1 or b<=a:
            self.out["diff"].set("請輸入改大的戒圍")
            for k in ["circ","tg","tq","rg","rq","cost"]: self.out[k].set("—")
            return

        diff=b-a
        circ=RING_SIZES[b]-RING_SIZES[a]
        volume=w*t*circ
        tg=volume*DENSITY[fin]/1000
        rg=tg*factor
        tq=tg/GRAMS_PER_QIAN
        rq=rg/GRAMS_PER_QIAN

        self.out["diff"].set(str(diff))
        self.out["circ"].set(f"{circ:.2f}")
        self.out["tg"].set(f"{tg:.3f}")
        self.out["tq"].set(f"{tq:.3f}")
        self.out["rg"].set(f"{rg:.3f}")
        self.out["rq"].set(f"{rq:.3f}")

        p=self.vars["price"].get().strip()
        if not p: self.out["cost"].set("請輸入金價")
        else:
            try:
                cost=rq*float(p)*RATIO[fin]
                self.out["cost"].set(f"{cost:,.0f} 元")
            except ValueError:
                self.out["cost"].set("金價格式錯誤")

if __name__=="__main__":
    root=tk.Tk()
    App(root)
    root.mainloop()
