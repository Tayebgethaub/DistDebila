import os, sys, pandas as pd, tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# مسار التطبيق والبيانات
curr_dir = os.path.dirname(os.path.abspath(sys.executable)) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
res_df, df_clean = None, None
file_path="/Users/ahmad/Desktop/BORGRAM DISTRIC/Charge BT JUILLET 2026.xlsx"

def handle_pick_files():
    p = path_in_var.get().strip()
    if p and os.path.exists(p): return error_lbl.config(text="✅ تم اعتماد المسار اليدوي!", fg="green")
    path = filedialog.askopenfilename(title="اختر ملف الإكسيل", filetypes=[("Excel files", "*.xlsx *.xls")])
    path="/Users/ahmad/Desktop/BORGRAM DISTRIC/Charge BT JUILLET 2026.xlsx"

    if path: path_in_var.set(path); 


    error_lbl.config(text="")

def start_process():
    global res_df, df_clean
    p = path_in_var.get().strip()
    if not p or not os.path.exists(p): return error_lbl.config(text="❌ المسار خاطئ أو فارغ!", fg="red")
    try:
        df_clean = pd.read_excel(p).dropna(subset=["POSTE", "I1", "I2", "I3"]).copy()
        df_clean["POSTE"] = df_clean["POSTE"].astype(str).str.replace("853P", "P", regex=True)
        df_clean["Total_I"] = df_clean["I1"] + df_clean["I2"] + df_clean["I3"]
        res_df = df_clean.loc[df_clean.groupby("POSTE")["Total_I"].idxmax()].copy()
        error_lbl.config(text="✅ تم تحميل ومعالجة البيانات بنجاح!", fg="green")
    except: error_lbl.config(text="❌ خطأ في بنية بيانات الملف!", fg="red")

def search_station():
    for item in tree.get_children(): tree.delete(item)
    q = search_in_var.get().strip().lower()
    if not q or res_df is None: return messagebox.showerror("خطأ", "تأكد من كتابة المحطة ومعالجة الملف!")
    match = res_df[res_df["POSTE"].astype(str).str.lower() == q]
    if not match.empty:
        r = match.iloc[0] # تأكيد جلب السطر الأول بدقة
        
        # جلب القيمة الأصلية للمقارنة الحسابية
        taux_val = r.get('taux de charge\n(%)')
        
        # دمج كل الخصائص في قائمة واحدة لتسهيل التلوين
        props = [
            ("I1", f"{int(r.get('I1'))}  A"),
            ("I2", f"{int(r.get('I2'))}  A"),
            ("I3", f"{int(r.get('I3'))}  A"),
            ("Total I", f"{int(r.get('Total_I'))}  A"), 
            ("V1", f"{int(r.get('V1'))}  V"),
            ("V2", f"{int(r.get('V2'))}  V"),
            ("V3", f"{int(r.get('V3'))}  V"),
            ("PUISSANCE", f"{int(r.get('PUISSANCE'))}  KVA"),
            ("HEURE", str(r.get('HEURE'))[0:5]),
            ("DATE", str(pd.to_datetime(r.get("DATE")).date())),
            ("taux de charge", f"{int(taux_val)}  %") # مدمجة هنا
        ]
        
        # المرور على الخصائص وطباعتها وتلوين نسبة الشحن بالأحمر إذا تجاوزت 80
        for p, v in props: 
            if p == "taux de charge" and float(taux_val) > 80:
                # إضافة وسم danger باللون الأحمر
                tree.insert("", "end", values=(p, v), tags=('danger',))
            else:
                tree.insert("", "end", values=(p, v))
                
    else: messagebox.showinfo("نتيجة", "❌ لم يتم العثور على هذه المحطة!")


def export_data():
    if res_df is None: return
    try:
        out_name = f"{os.path.splitext(os.path.basename(path_in_var.get().strip()))[0]}_Processed.xlsx"
        res_df.to_excel(os.path.join(os.path.expanduser("~"), "Desktop", out_name), index=False)
        error_lbl.config(text=f"✅ تم التصدير لسطح المكتب باسم: {out_name}", fg="green")
    except: error_lbl.config(text="❌ فشل التصدير، تأكد من إغلاق الملف.", fg="red")

def plot_station_currents():
    for w in graph_frame.winfo_children(): w.destroy()
    # هنا تم حذف القوس [135] ليعمل البحث والرسم بسلام
    q = graph_search_var.get().strip().lower()
    if not q or df_clean is None: return
    s_data = df_clean[df_clean['POSTE'].astype(str).str.lower() == q].sort_values('DATE')
    if not s_data.empty:
        fig, ax = plt.subplots(figsize=(5, 3.5), dpi=100)
        for col, c in zip(['I1', 'I2', 'I3'], ['#FF5722', '#4CAF50', '#2196F3']):
            ax.plot(s_data['DATE'].astype(str), s_data[col], label=col, marker='o', color=c)
        ax.set_title(f"POSTE: {q.upper()}"), ax.legend(), ax.grid(True, linestyle='--')
        plt.setp(ax.get_xticklabels(), rotation=30, ha='right', fontsize=8)
        fig.tight_layout()
        FigureCanvasTkAgg(fig, master=graph_frame).get_tk_widget().pack(fill="both", expand=True)
    else: messagebox.showinfo("نتيجة", "❌ لم يتم العثور على المركز للرسم!")

# الواجهة الرسومية
root = tk.Tk()
root.title("مشروع DistDebila")
root.geometry("600x700")


notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, pady=5)

# التبويب 1
t1 = tk.Frame(notebook, bg="white"); notebook.add(t1, text=" تحميل البيانات ")
path_in_var = tk.StringVar()
f_file = tk.Frame(t1, bg="white"); f_file.pack(pady=40)
tk.Entry(f_file, textvariable=path_in_var, width=35).pack(side="left", padx=5)
tk.Button(f_file, text="اختر الملف 📁", command=handle_pick_files).pack(side="left")
tk.Button(t1, text="معالجة البيانات", command=start_process, bg="#2196F3", fg="white").pack(pady=10)
error_lbl = tk.Label(t1, text="", bg="white"); error_lbl.pack()

# التبويب 2
t2 = tk.Frame(notebook, bg="white"); notebook.add(t2, text=" الاستعلام والتصدير ")
f_search = tk.Frame(t2, bg="white"); f_search.pack(pady=10)
search_in_var = tk.StringVar()
tk.Entry(f_search, textvariable=search_in_var, width=20).pack(side="left", padx=5)
tk.Button(f_search, text="ابحث", command=search_station, bg="#4CAF50", fg="white").pack(side="left")
tree = ttk.Treeview(t2, columns=("الخاصية", "القيمة"), show="headings", height=8)
tree.heading("الخاصية", text="الخاصية"); tree.heading("القيمة", text="القيمة"); tree.pack(pady=10, fill="both", expand=True, padx=20)
tk.Button(t2, text="تصدير التقرير كاملاً 📄", command=export_data, bg="#9C27B0", fg="white").pack(pady=10)

# التبويب 3
t3 = tk.Frame(notebook, bg="white"); notebook.add(t3, text=" المنحنى البياني 📈 ")
f_g_search = tk.Frame(t3, bg="white"); f_g_search.pack(pady=10)
graph_search_var = tk.StringVar()
tk.Entry(f_g_search, textvariable=graph_search_var, width=20).pack(side="left", padx=5)
tk.Button(f_g_search, text="رسم 📊", command=plot_station_currents, bg="#FF9800", fg="white").pack(side="left")
graph_frame = tk.Frame(t3, bg="#f5f5f5"); graph_frame.pack(fill="both", expand=True, padx=20, pady=10)

root.mainloop()




if __name__ == "__main__":
    root.mainloop()
