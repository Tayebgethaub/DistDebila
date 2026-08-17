import os, ssl
import pandas as pd
import flet as ft

# 💡 فكرة أحمد العبقرية: إجبار البرنامج على قراءة محرك الواجهة من مجلد بجانبه بدلاً من الإنترنت
current_dir = os.path.dirname(os.path.abspath(__file__))
cache_path = os.path.join(current_dir, "flet_cache")
os.environ["FLET_CLIENT_CACHE_DIR"] = cache_path

ssl._create_default_https_context = ssl._create_unverified_context
res_df = None

def main(page: ft.Page):
    global res_df
    
    # إعدادات الشاشة البيضاء الناصعة ومنع السواد وتفعيل مسطرة الماوس
    page.title = "نظام المحطات الكهربائية"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = ft.ScrollMode.AUTO
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.window_width, page.window_height = 600, 750

    # المكونات الرسومية الأساسية
    path_in = ft.TextField(label="أدخل مسار ملف الإكسيل بدقة أو الصقه هنا 📁", hint_text="مثال: C:/data/file.xlsx", width=450)
    search_in = ft.TextField(label="أدخل اسم المحطة بدقة", hint_text="مثال: P10", width=250)
    error_txt = ft.Text("", color="red", size=14)
    res_container = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    # دالة معالجة ودخول البيانات من ملف الإكسيل عبر المسار المكتوب أو الملصق
    def start_process(e):
        global res_df
        file_path = path_in.value.strip() if path_in.value else ""
        if file_path == "":
            error_txt.value = "⚠️ يرجى إدخال مسار ملف الإكسيل أولاً!"
            error_txt.color = "red"
            page.update(); return
        try:
            df = pd.read_excel(file_path)
            df_clean = df.dropna(subset=["POSTE", "I1", "I2", "I3"]).copy()
            df_clean["Total_I"] = df_clean["I1"] + df_clean["I2"] + df_clean["I3"]
            res_df = df_clean.loc[df_clean.groupby("POSTE")["Total_I"].idxmax()].copy()
            res_df["POSTE"] = res_df["POSTE"].replace("853P", "P", regex=True)
            
            error_txt.value = "✅ تم تحميل ومعالجة البيانات بنجاح! انتقل لتبويب البحث."
            error_txt.color = "green"
            page.update()
        except Exception:
            error_txt.value = "❌ خطأ! تأكد من مسار الملف أو صحة البيانات بداخلة."
            error_txt.color = "red"
            page.update()

    # دالة البحث والاستعلام بالجدول المنظم الأسود العريض الواضح
    def search_station(e):
        global res_df
        res_container.controls.clear()
        if not search_in.value.strip():
            res_container.controls.append(ft.Text("⚠️ يرجى كتابة اسم المحطة أولاً!", color="red"))
            page.update(); return
        if res_df is None:
            res_container.controls.append(ft.Text("❌ يرجى تحميل ومعالجة البيانات من التبويب الأول أولاً!", color="red"))
            page.update(); return
        
        match = res_df[res_df["POSTE"].astype(str).str.lower() == search_in.value.strip().lower()]
        if not match.empty:
            row = match.iloc
            v1_val = row.get("V1", "غير متوفر")
            v2_val = row.get("V2", "غير متوفر")
            v3_val = row.get("V3", "غير متوفر")
            
            result_table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("الخاصية", color="blue", weight="bold")),
                    ft.DataColumn(ft.Text("القيمة المسجلة", color="blue", weight="bold")),
                ],
                rows=[
                    ft.DataRow(cells=[ft.DataCell(ft.Text("I1", color="black")), ft.DataCell(ft.Text(str(row["I1"]), color="black", weight="bold"))]),
                    ft.DataRow(cells=[ft.DataCell(ft.Text("I2", color="black")), ft.DataCell(ft.Text(str(row["I2"]), color="black", weight="bold"))]),
                    ft.DataRow(cells=[ft.DataCell(ft.Text("I3", color="black")), ft.DataCell(ft.Text(str(row["I3"]), color="black", weight="bold"))]),
                    ft.DataRow(cells=[ft.DataCell(ft.Text("Total I", color="green")), ft.DataCell(ft.Text(str(row["Total_I"]), color="green", weight="bold"))]),
                    ft.DataRow(cells=[ft.DataCell(ft.Text("V1", color="black")), ft.DataCell(ft.Text(str(v1_val), color="black", weight="bold"))]),
                    ft.DataRow(cells=[ft.DataCell(ft.Text("V2", color="black")), ft.DataCell(ft.Text(str(v2_val), color="black", weight="bold"))]),
                    ft.DataRow(cells=[ft.DataCell(ft.Text("V3", color="black")), ft.DataCell(ft.Text(str(v3_val), color="black", weight="bold"))]),
                    ft.DataRow(cells=[ft.DataCell(ft.Text("PUISSANCE", color="purple")), ft.DataCell(ft.Text(str(row.get("PUISSANCE", "غير متوفر")), color="purple", weight="bold"))]),
                    ft.DataRow(cells=[ft.DataCell(ft.Text("DATE", color="purple")), ft.DataCell(ft.Text(str(row.get("DATE", "غير متوفر")), color="purple", weight="bold"))]),
                ]
            )
            res_container.controls.append(result_table)
        else:
            res_container.controls.append(ft.Text("❌ عذراً، لم يتم العثور على هذه المحطة!", color="red"))
        page.update()

    # دالة تصدير تقارير الإكسيل لسطح المكتب
    def export_data(e):
        global res_df
        if res_df is not None:
            try:
                desktop_path = os.path.join(os.path.expanduser("~"), "Desktop", "Highest_Current_Stations_Report.xlsx")
                res_df.to_excel(desktop_path, index=False)
                error_txt.value = "✅ تم تصدير الجدول بالكامل بنجاح إلى سطح المكتب!"
                error_txt.color = "green"
            except Exception:
                error_txt.value = "❌ فشل التصدير، تأكد من إغلاق ملف التقرير إذا كان مفتوحاً مسبقاً."
                error_txt.color = "red"
            page.update()
        else:
            error_txt.value = "❌ لا توجد بيانات لتصديرها!"
            error_txt.color = "red"
            page.update()

    # دالة التنقل الهادئ والسلس بين التبويبات
    def tabs_changed(e):
        if filter_tabs.selected_index == 0:
            view_load.visible = True
            view_search.visible = False
        else:
            view_load.visible = False
            view_search.visible = True
        page.update()

    view_load = ft.Column(
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Text("مرحباً بك في نظام إدارة المحطات", size=22, weight=ft.FontWeight.BOLD, color="black"),
            ft.Text("مشروع DistDebila", size=14, color="grey"),
            ft.Divider(),
            path_in,
            ft.Button(content=ft.Text("الدخول ونظام المعالجة"), on_click=start_process),
        ]
    )

    view_search = ft.Column(
        visible=False,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Text("استعلام عن محطة كهربائية", size=18, weight="bold", color="black"),
            ft.Row([search_in, ft.Button(content=ft.Text("ابحث"), on_click=search_station)], alignment=ft.MainAxisAlignment.CENTER),
            ft.Divider(),
            ft.Button(content=ft.Text("تصدير التقرير المفلتر كاملاً إلى إكسيل 📄"), on_click=export_data),
            ft.Divider(),
            res_container
        ]
    )

    filter_tabs = ft.Tabs(
        length=2,
        selected_index=0,
        on_change=tabs_changed,
        content=ft.TabBar(
            scrollable=False,
            tabs=[ft.Tab(label="تحميل البيانات"), ft.Tab(label="البحث والتصدير")],
        ),
    )

    page.add(filter_tabs, ft.Divider(), view_load, view_search, error_txt)
    page.update()

if __name__ == "__main__":
    ft.run(main)
