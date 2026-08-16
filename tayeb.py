import os, ssl
import pandas as pd
import flet as ft

ssl._create_default_https_context = ssl._create_unverified_context
res_df = None

@ft.control
class PosteApp(ft.Column):
    def init(self):
        self.path_in = ft.TextField(label="أدخل مسار ملف الإكسيل بدقة", hint_text="مثال: C:/data/file.xlsx", width=450)
        self.search_in = ft.TextField(label="أدخل اسم المحطة بدقة", hint_text="مثال: P10", width=250)
        self.error_txt = ft.Text("", color="red", size=14)
        self.res_container = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER)

        self.filter = ft.TabBar(
            scrollable=False,
            tabs=[
                ft.Tab(label="تحميل البيانات"),
                ft.Tab(label="البحث والتصدير"),
            ],
        )

        self.filter_tabs = ft.Tabs(
            length=2,
            selected_index=0,
            on_change=self.tabs_changed,
            content=self.filter,
        )

        self.view_load = ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text("مرحباً بك في نظام إدارة المحطات", size=22, weight=ft.FontWeight.BOLD),
                ft.Text("مشروع DistDebila", size=14, color="grey"),
                ft.Divider(),
                self.path_in,
                ft.Button(content=ft.Text("الدخول ونظام المعالجة"), on_click=self.start_process),
            ]
        )

        self.view_search = ft.Column(
            visible=False,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text("استعلام عن محطة كهربائية", size=18, weight="bold"),
                ft.Row([self.search_in, ft.Button(content=ft.Text("ابحث"), on_click=self.search_station)], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(),
                ft.Button(content=ft.Text("تصدير التقرير المفلتر كاملاً إلى إكسيل 📄"), on_click=self.export_data),
                ft.Divider(),
                self.res_container
            ]
        )

        self.width = 600
        self.controls = [
            self.filter_tabs,
            ft.Divider(),
            self.view_load,
            self.view_search,
            self.error_txt
        ]

    def start_process(self, e):
        global res_df
        if not self.path_in.value.strip():
            self.error_txt.value = "⚠️ يرجى إدخل مسار ملف الإكسيل أولاً!"
            self.error_txt.color = "red"
            self.update(); return
        try:
            df = pd.read_excel(self.path_in.value.strip())
            df_clean = df.dropna(subset=["POSTE", "I1", "I2", "I3"]).copy()
            df_clean["Total_I"] = df_clean["I1"] + df_clean["I2"] + df_clean["I3"]
            res_df = df_clean.loc[df_clean.groupby("POSTE")["Total_I"].idxmax()].copy()
            res_df["POSTE"] = res_df["POSTE"].replace("853P", "P", regex=True)
            
            self.error_txt.value = "✅ تم تحميل ومعالجة البيانات بنجاح! انتقل لتبويب البحث."
            self.error_txt.color = "green"
            self.update()
        except Exception:
            self.error_txt.value = "❌ خطأ في مسار الملف أو صحة البيانات بداخلة!"
            self.error_txt.color = "red"
            self.update()

    def search_station(self, e):
        global res_df
        self.res_container.controls.clear()
        if not self.search_in.value.strip():
            self.res_container.controls.append(ft.Text("⚠️ يرجى كتابة اسم المحطة أولاً!", color="red"))
            self.update(); return
        if res_df is None:
            self.res_container.controls.append(ft.Text("❌ يرجى تحميل ومعالجة البيانات من التبويب الأول أولاً!", color="red"))
            self.update(); return
        
        match = res_df[res_df["POSTE"].astype(str).str.lower() == self.search_in.value.strip().lower()]
        if not match.empty:
            row = match.iloc[0]
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
            self.res_container.controls.append(result_table)
        else:
            self.res_container.controls.append(ft.Text("❌ عذراً، لم يتم العثور على هذه المحطة!", color="red"))
        self.update()

    def export_data(self, e):
        global res_df
        if res_df is not None:
            try:
                desktop_path = os.path.join(os.path.expanduser("~"), "Desktop", "Highest_Current_Stations_Report.xlsx")
                res_df.to_excel(desktop_path, index=False)
                self.error_txt.value = "✅ تم تصدير الجدول بالكامل بنجاح إلى سطح المكتب!"
                self.error_txt.color = "green"
            except Exception:
                self.error_txt.value = "❌ فشل التصدير، تأكد من إغلاق ملف التقرير إذا كان مفتوحاً مسبقاً."
                self.error_txt.color = "red"
        else:
            self.error_txt.value = "❌ لا توجد بيانات لتصديرها!"
            self.error_txt.color = "red"
        self.update()

    def tabs_changed(self, e):
        if self.filter_tabs.selected_index == 0:
            self.view_load.visible = True
            self.view_search.visible = False
        else:
            self.view_load.visible = False
            self.view_search.visible = True
        self.update()


def main(page: ft.Page):
    page.title = "نظام المحطات الكهربائية"
    
    # 💡 التعديل الوحيد: إجبار واجهة برنامجك على اللون الأبيض لضرب سواد الوضع الليلي في الويندوز
    page.theme_mode = ft.ThemeMode.LIGHT
    
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.window_width = 600
    page.window_height = 750
    
    app = PosteApp()
    page.add(app)
    page.update()

if __name__ == "__main__":
    ft.run(main)
