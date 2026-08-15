import ssl
import os
import pandas as pd
import flet as ft

ssl._create_default_https_context = ssl._create_unverified_context

res_df = None

def main(page: ft.Page):
    global res_df
    page.title = "نظام إدارة وبحث المحطات الكهربائية"
    page.window_width = 600
    page.window_height = 750

    send_input = ft.TextField(
        label="مسار ملف الإكسيل المختار",
        hint_text="سيظهر مسار الملف هنا تلقائياً بعد اختياره",
        width=450,
        read_only=True
    )

    error_text = ft.Text("", color="red", size=14)
    export_status_text = ft.Text("", color="green", size=14, weight="bold")

    def pick_file_result(e):
        if e.files:
            send_input.value = e.files[0].path if isinstance(e.files, list) else e.files.path
            error_text.value = ""
            page.update()

    file_picker = ft.FilePicker(on_result=pick_file_result)
    page.overlay.append(file_picker)

    def process_and_login(e):
        global res_df
        file_path = send_input.value.strip() if send_input.value else ""

        if file_path == "":
            error_text.value = "⚠️ يرجى اختيار ملف الإكسيل أولاً!"
            page.update()
            return

        try:
            df = pd.read_excel(file_path)
            df_clean = df.dropna(subset=["POSTE", "I1", "I2", "I3"]).copy()
            df_clean["Total_I"] = df_clean["I1"] + df_clean["I2"] + df_clean["I3"]

            idx = df_clean.groupby(["POSTE"])["Total_I"].idxmax()
            res_df = df_clean.loc[idx].copy()
            res_df["POSTE"] = res_df["POSTE"].replace("853P", "P", regex=True)

            error_text.value = ""
            show_search_page()

        except Exception:
            error_text.value = "❌ خطأ! تأكد من صحة بيانات ملف الإكسيل المختار."
            page.update()

    def export_data_clicked(e):
        global res_df
        if res_df is not None:
            try:
                desktop_path = os.path.join(os.path.expanduser("~"), "Desktop", "Highest_Current_Stations_Report.xlsx")
                res_df.to_excel(desktop_path, index=False)
                export_status_text.value = "✅ تم تصدير الجدول بالكامل بنجاح إلى سطح المكتب!"
                export_status_text.color = "green"
            except Exception:
                export_status_text.value = "❌ فشل التصدير، تأكد من إغلاق ملف التقرير إذا كان مفتوحاً مسبقاً."
                export_status_text.color = "red"
        else:
            export_status_text.value = "❌ لا توجد بيانات لتصديرها!"
            export_status_text.color = "red"
        page.update()

    def show_home(e=None):
        page.views.clear()
        page.views.append(
            ft.View(
                route="/",
                controls=[
                    ft.AppBar(title=ft.Text("الصفحة الرئيسية"), bgcolor="blue"),
                    ft.Text("مرحباً بك في نظام إدارة المحطات", size=22, weight=ft.FontWeight.BOLD),
                    ft.Text("مشروع DistDebila", size=14, color="grey"),
                    ft.Divider(),
                    send_input,
                    ft.ElevatedButton(
                        text="اختر ملف الإكسيل من جهازك 📁",
                        on_click=lambda _: file_picker.pick_files(allow_multiple=False, allowed_extensions=["xlsx", "xls"])
                    ),
                    error_text,
                    ft.Divider(),
                    ft.ElevatedButton(
                        text="الدخول إلى نظام البحث والاستعلام",
                        on_click=process_and_login,
                    ),
                ],
                vertical_alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
        page.update()

    def show_search_page(e=None):
        global res_df
        search_input = ft.TextField(label="أدخل اسم المحطة بدقة", hint_text="مثال: P10", width=250)
        result_container = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        export_status_text.value = ""

        def search_clicked(ev):
            target_poste = search_input.value.strip()
            result_container.controls.clear()

            if target_poste == "":
                result_container.controls.append(ft.Text("⚠️ يرجى كتابة اسم المحطة أولاً!", color="red"))
            elif res_df is None:
                result_container.controls.append(ft.Text("❌ البيانات غير محملة بشكل صحيح!", color="red"))
            else:
                match = res_df[res_df["POSTE"].astype(str).str.lower() == target_poste.lower()]
                if not match.empty:
                    row = match.iloc[0]
                    date_str = str(row.get("DATE", "غير متوفر"))
                    puissance_val = row.get("PUISSANCE", "غير متوفر")
                    v1_val = row.get("V1", "غير متوفر")
                    v2_val = row.get("V2", "غير متوفر")
                    v3_val = row.get("V3", "غير متوفر")

                    result_table = ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text("الخاصية")),
                            ft.DataColumn(ft.Text("القيمة")),
                        ],
                        rows=[
                            ft.DataRow(cells=[ft.DataCell(ft.Text("I1")), ft.DataCell(ft.Text(str(row["I1"])))]),
                            ft.DataRow(cells=[ft.DataCell(ft.Text("I2")), ft.DataCell(ft.Text(str(row["I2"])))]),
                            ft.DataRow(cells=[ft.DataCell(ft.Text("I3")), ft.DataCell(ft.Text(str(row["I3"])))]),
                            ft.DataRow(cells=[ft.DataCell(ft.Text("Total I")), ft.DataCell(ft.Text(str(row["Total_I"])))]),
                            ft.DataRow(cells=[ft.DataCell(ft.Text("V1")), ft.DataCell(ft.Text(str(v1_val)))]),
                            ft.DataRow(cells=[ft.DataCell(ft.Text("V2")), ft.DataCell(ft.Text(str(v2_val)))]),
                            ft.DataRow(cells=[ft.DataCell(ft.Text("V3")), ft.DataCell(ft.Text(str(v3_val)))]),
                            ft.DataRow(cells=[ft.DataCell(ft.Text("PUISSANCE")), ft.DataCell(ft.Text(str(puissance_val)))]),
                            ft.DataRow(cells=[ft.DataCell(ft.Text("DATE")), ft.DataCell(ft.Text(date_str))]),
                        ]
                    )
                    result_container.controls.append(result_table)
                else:
                    result_container.controls.append(ft.Text("❌ عذراً، لم يتم العثور على هذه المحطة!", color="red"))
            page.update()

        page.views.clear()
        page.views.append(
            ft.View(
                route="/search",
                controls=[
                    ft.AppBar(title=ft.Text("نافذة البحث والاستعلام"), bgcolor="green"),
                    ft.Text("استعلام عن محطة كهربائية", size=18, weight="bold"),
                    ft.Row([search_input, ft.ElevatedButton(text="ابحث", on_click=search_clicked)], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Divider(),
                    ft.ElevatedButton(
                        text="تصدير التقرير المفلتر كاملاً إلى إكسيل 📄",
                        color=ft.colors.WHITE,
                        bgcolor=ft.colors.BLUE_700,
                        on_click=export_data_clicked
                    ),
                    export_status_text,
                    ft.Divider(),
                    result_container,
                    ft.Divider(),
                    ft.ElevatedButton(text="الرجوع للرئيسية", on_click=show_home),
                ],
                vertical_alignment=ft.MainAxisAlignment.START,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
        page.update()

    show_home()

ft.run(main)
