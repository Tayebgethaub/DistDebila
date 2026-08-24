import os, sys, pandas as pd, tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.dates as mdates  
import matplotlib.ticker as mticker  

# مسار التطبيق والبيانات
res_df, df_clean = None, None

# 🛠️ تخصيص شريط الأدوات لإظهار التراجع والزوم فقط وحذف زر الهوم تماماً
class CustomToolbar(NavigationToolbar2Tk):
    def __init__(self, canvas, window, pack_toolbar=False):
        self.toolitems = (
            ('Back', 'Back to previous view', 'back', 'back'),
            ('Forward', 'Forward to next view', 'forward', 'forward'),
            (None, None, None, None),
            ('Zoom', 'Zoom to rectangle', 'zoom_to_rect', 'zoom'),
        )
        super().__init__(canvas, window, pack_toolbar=pack_toolbar)

def handle_pick_files():
    p = path_in_var.get().strip()
    if p and os.path.exists(p): return error_lbl.config(text="✅ تم اعتماد المسار اليدوي!", fg="green")
    path = filedialog.askopenfilename(title="اختر ملف الإكسيل", filetypes=[("Excel files", "*.xlsx *.xls")])
    if path: path_in_var.set(path); error_lbl.config(text="✅ تم اختيار الملف بنجاح", fg="green")

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
    except Exception as e: error_lbl.config(text=f"❌ خطأ في الملف! {str(e)}", fg="red")

def search_station():
    for item in tree.get_children(): tree.delete(item)
    q = search_in_var.get().strip().lower()
    if not q or res_df is None: return messagebox.showerror("خطأ", "تأكد من كتابة المحطة ومعالجة الملف!")
    match = res_df[res_df["POSTE"].astype(str).str.lower() == q]
    if not match.empty:
        r = match.iloc
        taux_val = 0 if pd.isna(r.get('taux de charge\n(%)')) else r.get('taux de charge\n(%)')
        props = [
            ("I1", f"{int(r.get('I1', 0))}  A"), ("I2", f"{int(r.get('I2', 0))}  A"), ("I3", f"{int(r.get('I3', 0))}  A"),
            ("Total I", f"{int(r.get('Total_I', 0))}  A"), ("V1", f"{int(r.get('V1', 0))}  V"), ("V2", f"{int(r.get('V2', 0))}  V"),
            ("V3", f"{int(r.get('V3', 0))}  V"), ("PUISSANCE", f"{int(r.get('PUISSANCE', 0))}  KVA"),
            ("HEURE", str(r.get('HEURE', ''))[0:5]), ("DATE", pd.to_datetime(r.get("DATE")).strftime('%d-%m-%Y') if pd.notna(r.get("DATE")) else ""),
            ("taux de charge", f"{int(taux_val)}  %")
        ]
        for p, v in props:
            tree.insert("", "end", values=(p, v), tags=('danger',) if p == "taux de charge" and float(taux_val) > 80 else ())
    else: messagebox.showinfo("نتيجة", "❌ لم يتم العثور على هذه المحطة!")

def export_data():
    if res_df is None: return
    try:
        out_name = f"{os.path.splitext(os.path.basename(path_in_var.get().strip()))}_Processed.xlsx"
        res_df.to_excel(os.path.join(os.path.expanduser("~"), "Desktop", out_name), index=False)
        error_lbl.config(text=f"✅ تم التصدير لسطح المكتب: {out_name}", fg="green")
    except: error_lbl.config(text="❌ فشل التصدير، تأكد من إغلاق الملف.", fg="red")

def plot_station_currents():
    for w in graph_frame.winfo_children(): w.destroy()
    q = graph_search_var.get().strip().lower()
    if not q or df_clean is None: return
    
    selected_currents = []
    if chk_i1_var.get(): selected_currents.append(('I1', '#FF5722'))
    if chk_i2_var.get(): selected_currents.append(('I2', '#4CAF50'))
    if chk_i3_var.get(): selected_currents.append(('I3', '#2196F3'))
    if not selected_currents: return messagebox.showinfo("تنبيه", "⚠️ يرجى اختيار تيار واحد على الأقل للرسم!")

    s_data = df_clean[df_clean['POSTE'].astype(str).str.lower() == q].copy()
    if s_data.empty: return messagebox.showinfo("نتيجة", "❌ لم يتم العثور على المركز!")
    
    s_data_clean = s_data[(s_data['I1'] > 0) & (s_data['I2'] > 0) & (s_data['I3'] > 0)].copy()
    if s_data_clean.empty: return messagebox.showinfo("تنبيه", "⚠️ جميع قراءات التيارات تساوي 0!")
        
    try:
        s_data_clean['time_str'] = s_data_clean['HEURE'].astype(str).str.strip().str[:5]
        s_data_clean['date_str'] = pd.to_datetime(s_data_clean['DATE']).dt.strftime('%Y-%m-%d')
        s_data_clean['datetime_comb'] = pd.to_datetime(s_data_clean['date_str'] + ' ' + s_data_clean['time_str'])
        s_data_clean = s_data_clean.sort_values('datetime_comb')
        
        # 📈 تعديل ذكي: تحويل خط الوقت إلى قراءات نصية مفصلة (اليوم/الشهر الساعة:الدقيقة) لتعرض بالكامل لكل نقطة دون إغفال أي ساعة
        s_data_clean['display_time'] = s_data_clean['datetime_comb'].dt.strftime('%d/%m %H:%M')
        x_values = s_data_clean['display_time']
        
        d_min, d_max = pd.to_datetime(s_data_clean['DATE'].min()).strftime('%d-%m-%Y'), pd.to_datetime(s_data_clean['DATE'].max()).strftime('%d-%m-%Y')
        title_period = f" ({d_min} to {d_max})" if d_min != d_max else f" ({d_min})"
    except:
        s_data_clean = s_data_clean.sort_values('HEURE')
        x_values, title_period = s_data_clean['HEURE'].astype(str).str.strip().str[:5], ""

    fig, ax = plt.subplots(figsize=(5, 3.5), dpi=100)
    
    for col, c in selected_currents:
        ax.plot(x_values, s_data_clean[col], label=col, marker='o', markersize=3, linewidth=1, color=c)
        
    ax.set_title(f"POSTE: {q.upper()}{title_period}", fontsize=9, fontweight='bold')
    ax.legend(fontsize=8), ax.grid(True, linestyle='--', alpha=0.5)
    
    # تدوير النصوص بزاوية مائلة لتتسع جميع المدخلات والساعات المفصلة تحت بعضها بدون تداخل
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right', fontsize=8)
    fig.tight_layout()
    
    canvas = FigureCanvasTkAgg(fig, master=graph_frame)
    canvas.draw()
    
    toolbar = CustomToolbar(canvas, graph_frame)
    toolbar.update()
    toolbar.pack(side=tk.TOP, fill=tk.X)
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

# الواجهة الرسومية (GUI)
root = tk.Tk()
root.title("مشروع DistDebilaTf")
root.geometry("650x780")

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, pady=5)

# التبويب 1
t1 = tk.Frame(notebook, bg="white"); notebook.add(t1, text=" تحميل البيانات ")
path_in_var = tk.StringVar(value="")
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
tree.tag_configure('danger', foreground='red', font=('Arial', 10, 'bold'))
tk.Button(t2, text="تصدير التقرير كامل 📄", command=export_data, bg="#9C27B0", fg="white").pack(pady=10)

# التبويب 3
t3 = tk.Frame(notebook, bg="white"); notebook.add(t3, text=" المنحنى البياني 📈 ")
f_g_search = tk.Frame(t3, bg="white"); f_g_search.pack(pady=10)
graph_search_var = tk.StringVar()
tk.Entry(f_g_search, textvariable=graph_search_var, width=15).pack(side="left", padx=5)

chk_i1_var, chk_i2_var, chk_i3_var = tk.BooleanVar(value=True), tk.BooleanVar(value=True), tk.BooleanVar(value=True)
tk.Checkbutton(f_g_search, text="I1", variable=chk_i1_var, bg="white", fg="#FF5722", font=('Arial', 10, 'bold')).pack(side="left", padx=2)
tk.Checkbutton(f_g_search, text="I2", variable=chk_i2_var, bg="white", fg="#4CAF50", font=('Arial', 10, 'bold')).pack(side="left", padx=2)
tk.Checkbutton(f_g_search, text="I3", variable=chk_i3_var, bg="white", fg="#2196F3", font=('Arial', 10, 'bold')).pack(side="left", padx=2)

tk.Button(f_g_search, text="رسم 📊", command=plot_station_currents, bg="#FF9800", fg="white").pack(side="left", padx=5)
graph_frame = tk.Frame(t3, bg="#f5f5f5"); graph_frame.pack(fill="both", expand=True, padx=20, pady=10)

root.mainloop()
