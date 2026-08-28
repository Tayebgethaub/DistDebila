import os, pandas as pd, tkinter as tk, matplotlib.pyplot as plt
from tkinter import ttk, messagebox, filedialog, simpledialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
res_df, df_clean = None, None
class CustomToolbar(NavigationToolbar2Tk):
    def __init__(self, canvas, window):
        self.toolitems = (('Back', '', 'back', 'back'), ('Forward', '', 'forward', 'forward'), (None,None,None,None), ('Zoom', '', 'zoom_to_rect', 'zoom'))
        super().__init__(canvas, window, pack_toolbar=False)
def handle_pick_files():
    path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
    if path: path_in_var.set(path); error_lbl.config(text="✅ تم اختيار الملف", fg="green")
def start_process():
    global res_df, df_clean
    p = path_in_var.get().strip()
    if not os.path.exists(p): return error_lbl.config(text="❌ المسار خاطئ!", fg="red")
    try:
        df_clean = pd.read_excel(p).dropna(subset=["POSTE", "I1", "I2", "I3"]).copy()
        df_clean["POSTE"] = df_clean["POSTE"].astype(str).str.replace("853P", "P", regex=True)
        df_clean["Total_I"] = df_clean["I1"] + df_clean["I2"] + df_clean["I3"]
        res_df = df_clean.loc[df_clean.groupby("POSTE")["Total_I"].idxmax()].copy()
        error_lbl.config(text="✅ تم معالجة البيانات بنجاح!", fg="green")
    except Exception as e: error_lbl.config(text=f"❌ خطأ: {str(e)}", fg="red")
def search_station():
    for item in tree.get_children(): tree.delete(item)
    q = search_in_var.get().strip().lower()
    if not q or res_df is None: return messagebox.showerror("خطأ", "تأكد من كتابة المحطة ومعالجة الملف!")
    match = res_df[res_df["POSTE"].astype(str).str.lower() == q]
    if not match.empty:
        r = match.iloc[0]
        taux = 0 if pd.isna(r.get('taux de charge\n(%)')) else r.get('taux de charge\n(%)')
        props = [
            ("I1", f"{int(r.get('I1', 0))} A"), ("I2", f"{int(r.get('I2', 0))} A"), ("I3", f"{int(r.get('I3', 0))} A"),
            ("Total I", f"{int(r.get('Total_I', 0))} A"), ("V1", f"{int(r.get('V1', 0))} V"), ("V2", f"{int(r.get('V2', 0))} V"),
            ("V3", f"{int(r.get('V3', 0))} V"), ("PUISSANCE", f"{int(r.get('PUISSANCE', 0))} KVA"),
            ("HEURE", str(r.get('HEURE', ''))[:5]), ("DATE", pd.to_datetime(r.get("DATE")).strftime('%d-%m-%Y') if pd.notna(r.get("DATE")) else ""),
            ("taux de charge", f"{int(taux)} %"), ("taux phase chargé ", f"{int(r.get('taux\nphase chargé \n(%)', 0))} %"), ("DESEQUILlibre", f"{int(r.get('DESEQUILlibre\n(%)', 0))} %")
        ]
        try: taux_float = float(str(taux).replace('%', '').strip())
        except: taux_float = 0
        for p, v in props: tree.insert("", "end", values=(p, v), tags=('danger',) if p == "taux de charge" and taux_float > 80 else ())
    else: messagebox.showinfo("نتيجة", "❌ لم يتم العثور على المحطة!")

def export_data():
    if res_df is None: return messagebox.showwarning("تنبيه", "⚠️ يرجى معالجة البيانات أولاً قبل التصدير!")
    try:
        out_name = f"{os.path.splitext(os.path.basename(path_in_var.get().strip()))[0]}_Processed.xlsx"
        res_df.to_excel(os.path.join(os.path.expanduser("~"), "Desktop", out_name), index=False)
        error_lbl.config(text=f"✅ تم التصدير لسطح المكتب: {out_name}", fg="green")
    except Exception as e: error_lbl.config(text=f"❌ فشل التصدير! {str(e)}", fg="red")

def export_by_taux():
    if res_df is None: return messagebox.showwarning("تنبيه", "⚠️ يرجى معالجة البيانات أولاً!")
    user_val = simpledialog.askinteger("تصفية البيانات", "أدخل الحد الأدنى لنسبة( taux de charge)  المُراد تصديرها :", minvalue=0, maxvalue=200)
    if user_val is None: return
    try:
        key_taux = 'taux de charge\n(%)'
        temp_df = res_df.copy()
        temp_df['taux_numeric'] = pd.to_numeric(temp_df[key_taux].astype(str).str.replace('%', '').str.strip(), errors='coerce').fillna(0)
        filtered_df = temp_df[temp_df['taux_numeric'] >= user_val].drop(columns=['taux_numeric'])
        if filtered_df.empty: return messagebox.showinfo("نتيجة", f"ℹ️ لا توجد محطات بنسبة تحميل أكبر من أو تساوي {user_val}%!")
        out_name = f"المحطات_الأعلى_من_{user_val}_بالمئة.xlsx"
        filtered_df.to_excel(os.path.join(os.path.expanduser("~"), "Desktop", out_name), index=False)
        error_lbl.config(text=f"✅ تم تصدير {len(filtered_df)} محطة لسطح المكتب باسم: {out_name}", fg="green")
    except Exception as e: error_lbl.config(text=f"❌ فشل تصفية البيانات! {str(e)}", fg="red")
def export_by_DESEQUILlibre():
    if res_df is None: return messagebox.showwarning("تنبيه", "⚠️ يرجى معالجة البيانات أولاً!")
    user_val = simpledialog.askinteger("تصفية البيانات", "أدخل الحد الأدنى لنسبة (DESEQUILlibre) المُراد تصديرها :", minvalue=0, maxvalue=200)
    if user_val is None: return
    try:
        key_DESEQUILlibre = 'DESEQUILlibre\n(%)'
        temp_df = res_df.copy()
        temp_df['DESEQUILlibre_numeric'] = pd.to_numeric(temp_df[key_DESEQUILlibre].astype(str).str.replace('%', '').str.strip(), errors='coerce').fillna(0)
        filtered_df = temp_df[temp_df['DESEQUILlibre_numeric'] >= user_val].drop(columns=['DESEQUILlibre_numeric'])
        if filtered_df.empty: return messagebox.showinfo("نتيجة", f"ℹ️ لا توجد محطات بنسبة تحميل أكبر من أو تساوي {user_val}%!")
        out_name = f"المحطات_الأعلى_من_{user_val}_بالمئة.xlsx"
        filtered_df.to_excel(os.path.join(os.path.expanduser("~"), "Desktop", out_name), index=False)
        error_lbl.config(text=f"✅ تم تصدير {len(filtered_df)} محطة لسطح المكتب باسم: {out_name}", fg="green")
    except Exception as e: error_lbl.config(text=f"❌ فشل تصفية البيانات! {str(e)}", fg="red")
def plot_station_currents():
    for w in graph_frame.winfo_children(): w.destroy()
    q = graph_search_var.get().strip().lower()
    if not q or df_clean is None: return messagebox.showinfo("تنبيه", "⚠️ يرجى معالجة الملف أولاً!")
    selected = []
    if chk_i1_var.get(): selected.append(('I1', '#FF5722'))
    if chk_i2_var.get(): selected.append(('I2', '#2ecc71'))
    if chk_i3_var.get(): selected.append(('I3', '#3498db'))
    if not selected: return messagebox.showinfo("تنبيه", "⚠️ اختر تياراً واحداً على الأقل!")
    s_data = df_clean[df_clean['POSTE'].astype(str).str.lower() == q].copy()
    if s_data.empty: return messagebox.showinfo("نتيجة", "❌ لم يتم العثور على المركز!")
    s_data_clean = s_data[(s_data['I1'] > 0) & (s_data['I2'] > 0) & (s_data['I3'] > 0)].copy()
    try:
        s_data_clean['datetime_comb'] = pd.to_datetime(s_data_clean['DATE'].astype(str) + ' ' + s_data_clean['HEURE'].astype(str).str.strip().str[:5])
        s_data_clean = s_data_clean.sort_values('datetime_comb')
        x_values = s_data_clean['datetime_comb'].dt.strftime('%d/%m %H:%M')
        title_period = f" ({pd.to_datetime(s_data_clean['DATE'].min()).strftime('%d-%m-%Y')} to {pd.to_datetime(s_data_clean['DATE'].max()).strftime('%d-%m-%Y')})"
    except: s_data_clean = s_data_clean.sort_values('HEURE'); x_values, title_period = s_data_clean['HEURE'].astype(str).str.strip().str[:5], ""
    fig, ax = plt.subplots(figsize=(5, 3.2), dpi=100)
    for col, c in selected: ax.plot(x_values, s_data_clean[col], label=col, marker='o', markersize=3, linewidth=1.5, color=c)
    ax.set_title(f"POSTE: {q.upper()}{title_period}", fontsize=9, fontweight='bold'); ax.legend(fontsize=8); ax.grid(True, linestyle='--', alpha=0.5)
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right', fontsize=8); fig.tight_layout()
    canvas = FigureCanvasTkAgg(fig, master=graph_frame); canvas.draw()
    toolbar = CustomToolbar(canvas, graph_frame); toolbar.update(); toolbar.pack(side=tk.TOP, fill=tk.X); canvas.get_tk_widget().pack(side=tk.TOP, fill="both", expand=True)
# 🖥️ الواجهة الرسومية
root = tk.Tk(); root.title("DistDebilaTf"); root.geometry("680x750")
notebook = ttk.Notebook(root); notebook.pack(fill="both", expand=True, padx=10, pady=5)

# التبويب 1
t1 = tk.Frame(notebook, bg="#f8f9fa"); notebook.add(t1, text="  تحميل البيانات 📂  ")
f_file = tk.LabelFrame(t1, text=" مسار ملف الإكسيل ", bg="white", fg="#7f8c8d"); f_file.pack(pady=20, padx=20, fill="x")
path_in_var = tk.StringVar(value="/Users/ahmad/Desktop/BORGRAM DISTRIC/Charge BT JUILLET 2026.xlsx")
tk.Entry(f_file, textvariable=path_in_var, font=("Arial", 11), bg="#f1f2f6", bd=0).pack(side="left", padx=10, pady=10, fill="x", expand=True)
tk.Button(f_file, text="اختر الملف 📁", command=handle_pick_files, bg="#7f8c8d", fg="white", bd=0).pack(side="right", padx=10, pady=10)
tk.Button(t1, text="بدء معالجة البيانات ⚙️", command=start_process, font=("Arial", 12, "bold"), bg="#2980b9", fg="white", bd=0).pack(pady=10, padx=20, fill="x")
tk.Button(t1, text="تصدير التقرير الكامل إلى سطح المكتب 📄", command=export_data, font=("Arial", 11, "bold"), bg="#8e44ad", fg="white", bd=0).pack(pady=10, padx=20, fill="x")
tk.Button(t1, text=" taux de charge 🎯", command=export_by_taux, font=("Arial", 11, "bold"), bg="#d35400", fg="white", bd=0).pack(pady=10, padx=20, fill="x")
tk.Button(t1, text=" DESEQUILlibre  🎯", command=export_by_DESEQUILlibre, font=("Arial", 11, "bold"), bg="#d35400", fg="white", bd=0).pack(pady=10, padx=20, fill="x")

error_lbl = tk.Label(t1, font=("Arial", 11, "bold"), bg="#f8f9fa"); error_lbl.pack(pady=10)

# التبويب 2
t2 = tk.Frame(notebook, bg="#f8f9fa"); notebook.add(t2, text="  الاستعلام 🔍  ")
f_search = tk.Frame(t2, bg="#f8f9fa"); f_search.pack(pady=10, padx=20, fill="x")
search_in_var = tk.StringVar()
tk.Entry(f_search, textvariable=search_in_var, font=("Arial", 12), width=20).pack(side="left", padx=5)
tk.Button(f_search, text="بحث سريع 🔍", command=search_station, bg="#27ae60", fg="white", bd=0).pack(side="left", padx=5)
tree = ttk.Treeview(t2, columns=("الخاصية", "القيمة"), show="headings", height=12)
tree.heading("الخاصية", text="الخاصية"); tree.heading("القيمة", text="القيمة"); tree.pack(pady=10, fill="both", expand=True, padx=20)
tree.tag_configure('danger', foreground='#e74c3c', font=('Arial', 11, 'bold'))

# التبويب 3
t3 = tk.Frame(notebook, bg="#f8f9fa"); notebook.add(t3, text="  المنحنى البياني 📈  ")
f_g_search = tk.Frame(t3, bg="#f8f9fa"); f_g_search.pack(pady=10, padx=20, fill="x")
graph_search_var = tk.StringVar()
tk.Entry(f_g_search, textvariable=graph_search_var, font=("Arial", 11), width=12).pack(side="left", padx=5)
chk_i1_var, chk_i2_var, chk_i3_var = tk.BooleanVar(value=True), tk.BooleanVar(value=True), tk.BooleanVar(value=True)
for name, var, col in [("I1", chk_i1_var, "#FF5722"), ("I2", chk_i2_var, "#2ecc71"), ("I3", chk_i3_var, "#3498db")]:
    tk.Checkbutton(f_g_search, text=name, variable=var, bg="#f8f9fa", fg=col, font=('Arial', 11, 'bold')).pack(side="left", padx=5)
tk.Button(f_g_search, text="رسم المخطط 📊", command=plot_station_currents, bg="#d35400", fg="white", bd=0).pack(side="right", padx=5)
graph_frame = tk.Frame(t3, bg="#ffffff", bd=1, relief="solid"); graph_frame.pack(fill="both", expand=True, padx=20, pady=10)
root.mainloop()

