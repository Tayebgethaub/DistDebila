import os
import sys
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# الشفرة السرية لربط الأيقونة بالشريط السفلي للويندوز
if sys.platform == "win32":
    import ctypes
    my_app_id = "distdebila.stationmanager.tayeb.1.0"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(my_app_id)

# تحديد المجلد الرئيسي للتطبيق بأمان
if getattr(sys, 'frozen', False):
    current_dir = os.path.dirname(os.path.abspath(sys.executable))
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))

res_df = None

# دالة اختيار ملف الإكسيل بالماوس
def handle_pick_files():
    file_path = filedialog.askopenfilename(
        title="اختر ملف الإكسيل للمحطات",
        filetypes=[("Excel files", "*.xlsx *.xls")]
    )
    if file_path:
        path_in_var.set(file_path)
        error_lbl.config(text="")

# دالة معالجة البيانات الخارقة والخفيفة جداً تنتهي في لمح البصر
def start_process():
    global res_df
    if not path_in_var.get():
        error_lbl.config(text="⚠️ يرجى اختيار ملف الإكسيل أولاً!", fg="red")
        return
    try:
        df = pd.read_excel(path_in_var.get())
        df_clean = df.dropna(subset=["POSTE", "I1", "I2", "I3"]).copy()
        df_clean["Total_I"] = df_clean["I1"] + df_clean["I2"] + df_clean["I3"]
        
        df_sorted = df_clean.sort_values("Total_I", ascending=False)
        res_df = df_sorted.drop_duplicates(subset=["POSTE"]).copy()
        res_df["POSTE"] = res_df["POSTE"].astype(str).str.replace("853P", "P", regex=True)
        
        error_lbl.config(text="✅ تم تحميل ومعالجة البيانات بنجاح! انتقل لتبويب البحث.", fg="green")
    except Exception:
        error_lbl.config(text="❌ خطأ في مسار الملف أو صحة البيانات بداخلة!", fg="red")

# 🚀 دالة البحث المعدّلة والمضمونة 100% بعد إصلاح ثغرة iloc[0]
def search_station():
    global res_df
    for item in tree.get_children():
        tree.delete(item)
        
    query = search_in_var.get().strip()
    if not query:
        messagebox.showwarning("تنبيه", "⚠️ يرجى كتابة اسم المحطة أولاً!")
        return
    if res_df is None:
        messagebox.showerror("خطأ", "❌ يرجى تحميل ومعالجة البيانات من التبويب الأول أولاً!")
        return
    
    match = res_df[res_df["POSTE"].astype(str).str.lower() == query.lower()]
    if not match.empty:
        # 💡 الإصلاح المنقذ: أضفنا [0] لتقرأ بايثون السطر المختار بسلام وبدون تجمّد
        row = match.iloc[0]
        v1_val = row.get("V1", "غير متوفر")
        v2_val = row.get("V2", "غير متوفر")
        v3_val = row.get("V3", "غير متوفر")
        
        # حسبة التكلفة السريعة بناءً على الاستطاعة
        puissance_val = row.get("PUISSANCE", 0)
        try:
            cost_calc = round(float(puissance_val) * 4.5, 2) if str(puissance_val).replace('.','',1).isdigit() else "غير متوفر للتحليل"
        except Exception:
            cost_calc = "خطأ في الحساب"

        properties = [
            ("I1", row.get("I1", "غير متوفر")),
            ("I2", row.get("I2", "غير متوفر")),
            ("I3", row.get("I3", "غير متوفر")),
            ("Total I", row.get("Total_I", "غير متوفر")),
            ("V1", v1_val),
            ("V2", v2_val),
            ("V3", v3_val),
            ("PUISSANCE (الاستطاعة)", puissance_val),
            ("COST (التكلفة التقديرية)", cost_calc),
            ("DATE", row.get("DATE", "غير متوفر"))
        ]
        for prop, val in properties:
            tree.insert("", "end", values=(prop, val))
    else:
        messagebox.showinfo("نتيجة", "❌ عذراً، لم يتم العثور على هذه المحطة!")

# دالة التصدير الفورية
def export_data():
    global res_df
    if res_df is not None:
        try:
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop", "Highest_Current_Stations_Report.xlsx")
            res_df.to_excel(desktop_path, index=False)
            error_lbl.config(text="✅ تم تصدير الجدول بالكامل بنجاح إلى سطح المكتب!", fg="green")
        except Exception:
            error_lbl.config(text="❌ فشل التصدير، تأكد من إغلاق ملف التقرير إذا كان مفتوحاً مسبقاً.", fg="red")
    else:
        error_lbl.config(text="❌ لا توجد بيانات لتصديرها!", fg="red")

def on_tab_change(event):
    if notebook.index(notebook.select()) == 0:
        error_lbl.config(text="")

# --- بناء الواجهة الرسومية الناصعة (Tkinter) ---
root = tk.Tk()
root.title("نظام المحطات الكهربائية - مشروع DistDebila")
root.geometry("600x700")
root.configure(bg="#f5f5f5")

icon_path = os.path.join(current_dir, "icon.ico")
if os.path.exists(icon_path):
    root.iconbitmap(icon_path)

notebook = ttk.Notebook(root)
notebook.pack(pady=10, fill="both", expand=True)
notebook.bind("<<NotebookTabChanged>>", on_tab_change)

# --- التبويب الأول: تحميل البيانات ---
tab1 = tk.Frame(notebook, bg="#ffffff")
notebook.add(tab1, text=" تحميل البيانات ")

tk.Label(tab1, text="مرحباً بك في نظام إدارة المحطات", font=("Arial", 16, "bold"), bg="#ffffff", fg="black").pack(pady=15)
tk.Label(tab1, text="مشروع DistDebila", font=("Arial", 11), bg="#ffffff", fg="grey").pack()

frame_file = tk.Frame(tab1, bg="#ffffff")
frame_file.pack(pady=30)

path_in_var = tk.StringVar()
path_entry = tk.Entry(frame_file, textvariable=path_in_var, width=40, font=("Arial", 10), state="readonly")
path_entry.pack(side="left", padx=5)

btn_pick = tk.Button(frame_file, text="اختر الملف 📁", command=handle_pick_files, font=("Arial", 10), bg="#e0e0e0")
btn_pick.pack(side="left")

btn_process = tk.Button(tab1, text="الدخول ونظام المعالجة", command=start_process, font=("Arial", 12, "bold"), bg="#2196F3", fg="white", bd=0, padx=15, pady=8)
btn_process.pack(pady=20)

error_lbl = tk.Label(tab1, text="", font=("Arial", 11), bg="#ffffff")
error_lbl.pack(pady=10)

# --- التبويب الثاني: البحث والتصدير ---
tab2 = tk.Frame(notebook, bg="#ffffff")
notebook.add(tab2, text=" البحث والتصدير ")

tk.Label(tab2, text="استعلام عن محطة كهربائية", font=("Arial", 14, "bold"), bg="#ffffff", fg="black").pack(pady=15)

frame_search = tk.Frame(tab2, bg="#ffffff")
frame_search.pack(pady=10)

search_in_var = tk.StringVar()
search_entry = tk.Entry(frame_search, textvariable=search_in_var, width=25, font=("Arial", 12))
search_entry.pack(side="left", padx=5)

btn_search = tk.Button(frame_search, text="ابحث", command=search_station, font=("Arial", 10, "bold"), bg="#4CAF50", fg="white", bd=0, padx=10, pady=4)
btn_search.pack(side="left")

# جدول عرض البيانات الاحترافي (DataTable)
tree_frame = tk.Frame(tab2)
tree_frame.pack(pady=15, fill="both", expand=True, padx=20)

tree = ttk.Treeview(tree_frame, columns=("الخاصية", "القيمة المسجلة"), show="headings", height=11)
tree.heading("الخاصية", text="الخاصية")
tree.heading("القيمة المسجلة", text="القيمة المسجلة")
tree.column("الخاصية", anchor="center", width=150)
tree.column("القيمة المسجلة", anchor="center", width=150)
tree.pack(fill="both", expand=True)

btn_export = tk.Button(tab2, text="تصدير التقرير المفلتر كاملاً إلى إكسيل 📄", command=export_data, font=("Arial", 11, "bold"), bg="#9C27B0", fg="white", bd=0, padx=15, pady=8)
btn_export.pack(pady=20)

if __name__ == "__main__":
    root.mainloop()




if __name__ == "__main__":
    root.mainloop()
