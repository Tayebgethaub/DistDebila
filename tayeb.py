"""
برنامج تحليل بيانات المحطات الكهربائية - DistDebilaTf
الإصدار المحسّن V2.0
"""

import os
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from datetime import datetime


class CustomToolbar(NavigationToolbar2Tk):
    """شريط أدوات مخصص للرسم البياني"""
    def __init__(self, canvas, window):
        self.toolitems = (
            ('Back', '', 'back', 'back'),
            ('Forward', '', 'forward', 'forward'),
            (None, None, None, None),
            ('Zoom', '', 'zoom_to_rect', 'zoom')
        )
        super().__init__(canvas, window, pack_toolbar=False)


class DataAnalyzer:
    """الفئة الرئيسية لتحليل البيانات وإدارة الواجهة"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("DistDebilaTf V2.0")
        self.root.geometry("750x800")
        
        # متغيرات البيانات
        self.raw_data = None
        self.processed_data = None
        self.filtered_data = None
        
        # متغيرات الواجهة
        self.path_var = tk.StringVar()
        self.search_var = tk.StringVar()
        self.graph_search_var = tk.StringVar()
        
        # متغيرات الرسم البياني
        self.chk_i1 = tk.BooleanVar(value=True)
        self.chk_i2 = tk.BooleanVar(value=True)
        self.chk_i3 = tk.BooleanVar(value=True)
        
        # تهيئة الواجهة
        self._setup_ui()
        
    def _setup_ui(self):
        """تهيئة واجهة المستخدم"""
        # دفتر التبويبات
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        # إنشاء التبويبات
        self._create_tab_load()
        self._create_tab_search()
        self._create_tab_graph()
        self._create_tab_stats()
        
    def _create_tab_load(self):
        """تبويب تحميل ومعالجة البيانات"""
        tab = tk.Frame(self.notebook, bg="#f8f9fa")
        self.notebook.add(tab, text="  تحميل البيانات 📂  ")
        
        # إطار اختيار الملف
        file_frame = tk.LabelFrame(tab, text=" مسار ملف الإكسيل ", bg="white", fg="#7f8c8d")
        file_frame.pack(pady=20, padx=20, fill="x")
        
        entry = tk.Entry(file_frame, textvariable=self.path_var, font=("Arial", 11), bg="#f1f2f6", bd=0)
        entry.pack(side="left", padx=10, pady=10, fill="x", expand=True)
        
        btn_browse = tk.Button(file_frame, text="اختر الملف 📁", command=self._pick_file, 
                              bg="#7f8c8d", fg="white", bd=0)
        btn_browse.pack(side="right", padx=10, pady=10)
        
        # أزرار المعالجة
        btn_process = tk.Button(tab, text="بدء معالجة البيانات ⚙️", command=self._process_data,
                               font=("Arial", 12, "bold"), bg="#2980b9", fg="white", bd=0)
        btn_process.pack(pady=10, padx=20, fill="x")
        
        # أزرار التصدير
        btn_export_all = tk.Button(tab, text="📄 تصدير التقرير الكامل", command=self._export_all,
                                  font=("Arial", 11, "bold"), bg="#8e44ad", fg="white", bd=0)
        btn_export_all.pack(pady=10, padx=20, fill="x")
        
        btn_export_taux = tk.Button(tab, text="🎯 تصدير حسب taux de charge", command=self._export_by_column,
                                   font=("Arial", 11, "bold"), bg="#d35400", fg="white", bd=0)
        btn_export_taux.pack(pady=10, padx=20, fill="x")
        
        btn_export_deseq = tk.Button(tab, text="⚖️ تصدير حسب DESEQUILlibre", command=self._export_by_deseq,
                                    font=("Arial", 11, "bold"), bg="#e67e22", fg="white", bd=0)
        btn_export_deseq.pack(pady=10, padx=20, fill="x")
        
        # ملصق الحالة
        self.status_label = tk.Label(tab, font=("Arial", 11, "bold"), bg="#f8f9fa")
        self.status_label.pack(pady=10)
        
    def _create_tab_search(self):
        """تبويب البحث والاستعلام"""
        tab = tk.Frame(self.notebook, bg="#f8f9fa")
        self.notebook.add(tab, text="  الاستعلام 🔍  ")
        
        # إطار البحث
        search_frame = tk.Frame(tab, bg="#f8f9fa")
        search_frame.pack(pady=10, padx=20, fill="x")
        
        entry = tk.Entry(search_frame, textvariable=self.search_var, font=("Arial", 12), width=25)
        entry.pack(side="left", padx=5)
        
        btn_search = tk.Button(search_frame, text="بحث سريع 🔍", command=self._search_station,
                              bg="#27ae60", fg="white", bd=0)
        btn_search.pack(side="left", padx=5)
        
        # شجرة النتائج
        self.tree = ttk.Treeview(tab, columns=("الخاصية", "القيمة"), show="headings", height=15)
        self.tree.heading("الخاصية", text="الخاصية")
        self.tree.heading("القيمة", text="القيمة")
        self.tree.pack(pady=10, fill="both", expand=True, padx=20)
        self.tree.tag_configure('danger', foreground='#e74c3c', font=('Arial', 11, 'bold'))
        self.tree.tag_configure('warning', foreground='#f39c12', font=('Arial', 10, 'bold'))
        
    def _create_tab_graph(self):
        """تبويب الرسم البياني"""
        tab = tk.Frame(self.notebook, bg="#f8f9fa")
        self.notebook.add(tab, text="  المنحنى البياني 📈  ")
        
        # إطار التحكم
        control_frame = tk.Frame(tab, bg="#f8f9fa")
        control_frame.pack(pady=10, padx=20, fill="x")
        
        entry = tk.Entry(control_frame, textvariable=self.graph_search_var, font=("Arial", 11), width=15)
        entry.pack(side="left", padx=5)
        
        # خيارات التيارات
        for name, var, col in [("I1", self.chk_i1, "#FF5722"), 
                              ("I2", self.chk_i2, "#2ecc71"), 
                              ("I3", self.chk_i3, "#3498db")]:
            cb = tk.Checkbutton(control_frame, text=name, variable=var, bg="#f8f9fa", 
                               fg=col, font=('Arial', 11, 'bold'))
            cb.pack(side="left", padx=5)
        
        btn_plot = tk.Button(control_frame, text="رسم المخطط 📊", command=self._plot_currents,
                            bg="#d35400", fg="white", bd=0)
        btn_plot.pack(side="right", padx=5)
        
        # إطار الرسم
        self.graph_frame = tk.Frame(tab, bg="#ffffff", bd=1, relief="solid")
        self.graph_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
    def _create_tab_stats(self):
        """تبويب الإحصائيات"""
        tab = tk.Frame(self.notebook, bg="#f8f9fa")
        self.notebook.add(tab, text="  إحصائيات 📊  ")
        
        # زر عرض الإحصائيات
        btn_stats = tk.Button(tab, text="عرض الإحصائيات 📈", command=self._show_statistics,
                             font=("Arial", 12, "bold"), bg="#16a085", fg="white", bd=0)
        btn_stats.pack(pady=20, padx=20, fill="x")
        
        # إطار عرض الإحصائيات
        self.stats_frame = tk.Frame(tab, bg="#ffffff", bd=1, relief="solid")
        self.stats_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
    def _pick_file(self):
        """اختيار ملف الإكسيل"""
        path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if path:
            self.path_var.set(path)
            self._update_status("✅ تم اختيار الملف", "green")
            
    def _update_status(self, message, color="green"):
        """تحديث رسالة الحالة"""
        self.status_label.config(text=message, fg=color)
        
    def _process_data(self):
        """معالجة البيانات الأساسية"""
        path = self.path_var.get().strip()
        
        if not os.path.exists(path):
            self._update_status("❌ المسار خاطئ!", "red")
            return
            
        try:
            # تحميل البيانات
            df = pd.read_excel(path)
            
            # التحقق من وجود الأعمدة المطلوبة
            required_cols = ["POSTE", "I1", "I2", "I3"]
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                self._update_status(f"❌ أعمدة مفقودة: {', '.join(missing_cols)}", "red")
                return
            
            # تنظيف البيانات
            df_clean = df.dropna(subset=required_cols).copy()
            
            # معالجة أسماء المحطات
            df_clean["POSTE"] = df_clean["POSTE"].astype(str).str.replace("853P", "P", regex=True)
            
            # حساب التيار الكلي
            df_clean["Total_I"] = df_clean["I1"] + df_clean["I2"] + df_clean["I3"]
            
            # استخراج أعلى حمل لكل محطة
            self.processed_data = df_clean.loc[df_clean.groupby("POSTE")["Total_I"].idxmax()].copy()
            
            # إضافة عمود التاريخ والوقت للرسوم البيانية
            if "DATE" in df_clean.columns and "HEURE" in df_clean.columns:
                try:
                    df_clean['datetime_comb'] = pd.to_datetime(
                        df_clean['DATE'].astype(str) + ' ' + df_clean['HEURE'].astype(str).str.strip().str[:5],
                        errors='coerce'
                    )
                except:
                    pass
            
            self.raw_data = df_clean
            self._update_status(f"✅ تم معالجة {len(self.processed_data)} محطة بنجاح!", "green")
            
        except Exception as e:
            self._update_status(f"❌ خطأ: {str(e)}", "red")
            
    def _search_station(self):
        """البحث عن محطة محددة"""
        # تنظيف الشجرة
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        query = self.search_var.get().strip().lower()
        if not query or self.processed_data is None:
            messagebox.showerror("خطأ", "تأكد من كتابة المحطة ومعالجة الملف!")
            return
            
        # بحث دقيق
        match = self.processed_data[self.processed_data["POSTE"].astype(str).str.lower() == query]
        
        # بحث جزئي إذا لم يتم العثور على تطابق تام
        if match.empty:
            match = self.processed_data[self.processed_data["POSTE"].astype(str).str.lower().str.contains(query, na=False)]
            
        if match.empty:
            messagebox.showinfo("نتيجة", "❌ لم يتم العثور على المحطة!")
            return
            
        # عرض النتائج
        row = match.iloc[0]
        self._display_station_data(row)
        
    def _display_station_data(self, row):
        """عرض بيانات المحطة في الشجرة"""
        # تعريف الخصائص
        props = [
            ("المحطة", row.get('POSTE', '')),
            ("التيار I1", f"{int(row.get('I1', 0))} A"),
            ("التيار I2", f"{int(row.get('I2', 0))} A"),
            ("التيار I3", f"{int(row.get('I3', 0))} A"),
            ("التيار الكلي", f"{int(row.get('Total_I', 0))} A"),
        ]
        
        # إضافة الفولتية إذا وجدت
        for i in range(1, 4):
            if f'V{i}' in row:
                props.append((f"الفولتية V{i}", f"{int(row.get(f'V{i}', 0))} V"))
        
        # إضافة القدرة إذا وجدت
        if 'PUISSANCE' in row:
            props.append(("القدرة", f"{int(row.get('PUISSANCE', 0))} KVA"))
        
        # إضافة التاريخ والوقت
        if 'HEURE' in row:
            props.append(("الوقت", str(row.get('HEURE', ''))[:5]))
        if 'DATE' in row and pd.notna(row.get('DATE')):
            try:
                date_str = pd.to_datetime(row.get('DATE')).strftime('%d-%m-%Y')
                props.append(("التاريخ", date_str))
            except:
                pass
        
        # إضافة نسب التحميل
        taux_keys = ['taux de charge\n(%)', 'taux de charge']
        for key in taux_keys:
            if key in row and pd.notna(row.get(key)):
                taux = row.get(key)
                try:
                    taux_val = float(str(taux).replace('%', '').strip())
                    tag = 'danger' if taux_val > 80 else ('warning' if taux_val > 60 else '')
                    props.append((f"نسبة التحميل", f"{taux_val:.1f} %", tag))
                except:
                    props.append((f"نسبة التحميل", str(taux)))
                break
        
        # إضافة عدم التوازن
        deseq_keys = ['DESEQUILlibre\n(%)', 'DESEQUILlibre']
        for key in deseq_keys:
            if key in row and pd.notna(row.get(key)):
                deseq = row.get(key)
                try:
                    deseq_val = float(str(deseq).replace('%', '').strip())
                    tag = 'danger' if deseq_val > 10 else ('warning' if deseq_val > 5 else '')
                    props.append((f"عدم التوازن", f"{deseq_val:.1f} %", tag))
                except:
                    props.append((f"عدم التوازن", str(deseq)))
                break
        
        # إضافة البيانات إلى الشجرة مع الألوان
        for prop in props:
            if len(prop) == 3:
                self.tree.insert("", "end", values=(prop[0], prop[1]), tags=(prop[2],))
            else:
                self.tree.insert("", "end", values=(prop[0], prop[1]))
                
    def _export_all(self):
        """تصدير جميع البيانات"""
        self._export_data(self.processed_data, "تقرير_كامل")
        
    def _export_by_column(self):
        """تصدير حسب نسبة التحميل"""
        self._export_filtered('taux de charge\n(%)', 'taux de charge', "نسبة التحميل", "التحميل")
        
    def _export_by_deseq(self):
        """تصدير حسب عدم التوازن"""
        self._export_filtered('DESEQUILlibre\n(%)', 'DESEQUILlibre', "عدم التوازن", "عدم_التوازن")
        
    def _export_data(self, data, base_name, suffix=""):
        """تصدير البيانات إلى ملف Excel"""
        if data is None or data.empty:
            messagebox.showwarning("تنبيه", "⚠️ لا توجد بيانات للتصدير!")
            return
            
        try:
            # إنشاء اسم الملف
            original_name = os.path.splitext(os.path.basename(self.path_var.get().strip()))[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            file_name = f"{original_name}_{base_name}{suffix}_{timestamp}.xlsx"
            file_path = os.path.join(os.path.expanduser("~"), "Desktop", file_name)
            
            # تصدير
            data.to_excel(file_path, index=False)
            self._update_status(f"✅ تم التصدير: {file_name}", "green")
            
        except Exception as e:
            self._update_status(f"❌ فشل التصدير: {str(e)}", "red")
            
    def _export_filtered(self, col_name, col_alt, display_name, file_prefix):
        """تصدير البيانات المصفاة حسب عمود معين"""
        if self.processed_data is None:
            messagebox.showwarning("تنبيه", "⚠️ يرجى معالجة البيانات أولاً!")
            return
            
        # تحديد العمود الصحيح
        col = col_name if col_name in self.processed_data.columns else col_alt
        if col not in self.processed_data.columns:
            messagebox.showerror("خطأ", f"❌ العمود {col} غير موجود!")
            return
            
        # الحصول على القيمة من المستخدم
        threshold = simpledialog.askinteger(
            "تصفية البيانات",
            f"أدخل الحد الأدنى لنسبة ({display_name}) المُراد تصديرها:",
            minvalue=0,
            maxvalue=200
        )
        
        if threshold is None:
            return
            
        try:
            # تحويل القيم إلى أرقام
            temp_df = self.processed_data.copy()
            temp_df['numeric_val'] = pd.to_numeric(
                temp_df[col].astype(str).str.replace('%', '').str.strip(),
                errors='coerce'
            ).fillna(0)
            
            # تصفية البيانات
            filtered = temp_df[temp_df['numeric_val'] >= threshold].drop(columns=['numeric_val'])
            
            if filtered.empty:
                messagebox.showinfo("نتيجة", f"ℹ️ لا توجد محطات بنسبة {display_name} أكبر من أو تساوي {threshold}%!")
                return
                
            # تصدير
            self._export_data(filtered, file_prefix, f"_أعلى_من_{threshold}")
            self._update_status(f"✅ تم تصدير {len(filtered)} محطة", "green")
            
        except Exception as e:
            self._update_status(f"❌ فشل التصفية: {str(e)}", "red")
            
    def _plot_currents(self):
        """رسم التيارات لمحطة محددة"""
        # تنظيف إطار الرسم السابق
        for widget in self.graph_frame.winfo_children():
            widget.destroy()
            
        station = self.graph_search_var.get().strip().upper()
        if not station or self.raw_data is None:
            messagebox.showinfo("تنبيه", "⚠️ يرجى معالجة الملف أولاً!")
            return
            
        # تحديد التيارات المختارة
        selected_currents = []
        if self.chk_i1.get():
            selected_currents.append(('I1', '#FF5722'))
        if self.chk_i2.get():
            selected_currents.append(('I2', '#2ecc71'))
        if self.chk_i3.get():
            selected_currents.append(('I3', '#3498db'))
            
        if not selected_currents:
            messagebox.showinfo("تنبيه", "⚠️ اختر تياراً واحداً على الأقل!")
            return
            
        # فلترة بيانات المحطة
        station_data = self.raw_data[self.raw_data['POSTE'].astype(str).str.upper() == station].copy()
        
        if station_data.empty:
            # بحث جزئي
            station_data = self.raw_data[self.raw_data['POSTE'].astype(str).str.upper().str.contains(station, na=False)].copy()
            
        if station_data.empty:
            messagebox.showinfo("نتيجة", f"❌ لم يتم العثور على المحطة: {station}")
            return
            
        # فلتر القيم الصفرية والسالبة مع تحذير
        invalid_mask = (station_data['I1'] <= 0) | (station_data['I2'] <= 0) | (station_data['I3'] <= 0)
        invalid_count = invalid_mask.sum()
        
        if invalid_count > 0:
            # تحذير للمستخدم
            response = messagebox.askyesno(
                "تنبيه",
                f"⚠️ توجد {invalid_count} قراءة بقيم صفرية أو سالبة.\n"
                f"هل تريد تجاهلها والاستمرار؟"
            )
            if not response:
                return
            station_data = station_data[~invalid_mask].copy()
            
        if station_data.empty:
            messagebox.showinfo("نتيجة", "❌ لا توجد بيانات صالحة للرسم!")
            return
            
        try:
            # ترتيب البيانات زمنياً
            if 'datetime_comb' in station_data.columns and not station_data['datetime_comb'].isna().all():
                station_data = station_data.sort_values('datetime_comb')
                x_values = station_data['datetime_comb'].dt.strftime('%d/%m %H:%M')
                title_suffix = ""
            else:
                station_data = station_data.sort_values('HEURE')
                x_values = station_data['HEURE'].astype(str).str.strip().str[:5]
                title_suffix = " (حسب الوقت)"
            
            # إنشاء الرسم البياني
            fig, ax = plt.subplots(figsize=(6, 3.5), dpi=100)
            
            for col, color in selected_currents:
                # فلتر القيم الصالحة لكل تيار على حدة
                valid_data = station_data[station_data[col] > 0]
                if not valid_data.empty:
                    ax.plot(
                        x_values[valid_data.index],
                        valid_data[col],
                        label=col,
                        marker='o',
                        markersize=3,
                        linewidth=1.5,
                        color=color
                    )
            
            # تنسيق الرسم
            ax.set_title(f"المحطة: {station}{title_suffix}", fontsize=10, fontweight='bold')
            ax.set_xlabel('الوقت', fontsize=9)
            ax.set_ylabel('التيار (A)', fontsize=9)
            ax.legend(fontsize=8)
            ax.grid(True, linestyle='--', alpha=0.5)
            plt.xticks(rotation=45, ha='right', fontsize=8)
            fig.tight_layout()
            
            # عرض الرسم في الواجهة
            canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
            canvas.draw()
            
            # إضافة شريط الأدوات
            toolbar = CustomToolbar(canvas, self.graph_frame)
            toolbar.update()
            toolbar.pack(side=tk.TOP, fill=tk.X)
            canvas.get_tk_widget().pack(side=tk.TOP, fill="both", expand=True)
            
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل الرسم البياني: {str(e)}")
            
    def _show_statistics(self):
        """عرض الإحصائيات"""
        # تنظيف الإطار السابق
        for widget in self.stats_frame.winfo_children():
            widget.destroy()
            
        if self.processed_data is None or self.processed_data.empty:
            messagebox.showinfo("تنبيه", "⚠️ يرجى معالجة البيانات أولاً!")
            return
            
        # حساب الإحصائيات
        stats_text = tk.Text(self.stats_frame, font=("Arial", 11), bg="#f8f9fa", wrap=tk.WORD)
        stats_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # إعداد بيانات الإحصائيات
        total_stations = len(self.processed_data)
        avg_i1 = self.processed_data['I1'].mean()
        avg_i2 = self.processed_data['I2'].mean() 
        avg_i3 = self.processed_data['I3'].mean()
        max_current = self.processed_data['Total_I'].max() if 'Total_I' in self.processed_data.columns else 0
        max_station = self.processed_data[self.processed_data['Total_I'] == max_current]['POSTE'].iloc[0] if max_current > 0 else "غير معروف"
        
        # عرض الإحصائيات
        stats = f"""
        📊 **إحصائيات المحطات الكهربائية**
        {'='*50}
        
        📌 عدد المحطات الكلي: {total_stations}
        
        ⚡ **متوسط التيارات:**
        • I1: {avg_i1:.2f} A
        • I2: {avg_i2:.2f} A  
        • I3: {avg_i3:.2f} A
        
        🏆 **أعلى حمل كلي:**
        • القيمة: {max_current:.2f} A
        • المحطة: {max_station}
        
        📈 **نسب التحميل:**
        """
        
        # إضافة إحصائيات نسبة التحميل إن وجدت
        taux_cols = ['taux de charge\n(%)', 'taux de charge']
        for col in taux_cols:
            if col in self.processed_data.columns:
                try:
                    taux_values = pd.to_numeric(
                        self.processed_data[col].astype(str).str.replace('%', '').str.strip(),
                        errors='coerce'
                    ).dropna()
                    if not taux_values.empty:
                        stats += f"""
        • المتوسط: {taux_values.mean():.1f} %
        • الأعلى: {taux_values.max():.1f} %
        • الأدنى: {taux_values.min():.1f} %
        • المحطات > 80%: {len(taux_values[taux_values > 80])} محطة
                        """
                except:
                    pass
                break
                
        # إضافة إحصائيات عدم التوازن إن وجدت
        deseq_cols = ['DESEQUILlibre\n(%)', 'DESEQUILlibre']
        for col in deseq_cols:
            if col in self.processed_data.columns:
                try:
                    deseq_values = pd.to_numeric(
                        self.processed_data[col].astype(str).str.replace('%', '').str.strip(),
                        errors='coerce'
                    ).dropna()
                    if not deseq_values.empty:
                        stats += f"""
        
        ⚖️ **إحصائيات عدم التوازن:**
        • المتوسط: {deseq_values.mean():.1f} %
        • الأعلى: {deseq_values.max():.1f} %
        • الأدنى: {deseq_values.min():.1f} %
        • المحطات > 10%: {len(deseq_values[deseq_values > 10])} محطة
                        """
                except:
                    pass
                break
        
        stats_text.insert(tk.END, stats)
        stats_text.config(state=tk.DISABLED)  # جعل النص للقراءة فقط


def main():
    """الدالة الرئيسية لتشغيل البرنامج"""
    root = tk.Tk()
    app = DataAnalyzer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
