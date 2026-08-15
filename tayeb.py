import ssl
import os
import pandas as pd
import flet as ft

ssl._create_default_https_context = ssl._create_unverified_context

res_df = None


def main(page: ft.Page):
    global res_df
    page.title = "نظام إدارة وبحث المحطات الكهربائية"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    page.window_width = 520
    page.window_height = 700

    send_input = ft.TextField(
        label="أدخل مسار أو عنوان الملف",
        hint_text="اكتب مسار ملف الإكسيل هنا (مثال: C:/data/file.xlsx)",
        width=400,
    )

    error_text = ft.Text("", color="red", size=14)

    def process_and_login(e):
        global res_df
        file_path = send_input.value.strip()

        if file_path == "":
            error_text.value = "⚠️ يرجى إدخال مسار الملف أولاً!"
            page.update()
            return

        try:
            df = pd.read_excel(file_path)
            df_clean = df.dropna(subset=["POSTE", "I1", "I2", "I3"]).copy()
            df_clean["Total_I"] = (
                df_clean["I1"] + df_clean["I2"] + df_clean["I3"]
            )

            idx = df_clean.groupby(["POSTE"])["Total_I"].idxmax()
            res_df = df_clean.loc[idx].copy()
            res_df["POSTE"] = res_df["POSTE"].replace("853P", "P", regex=True)

            error_text.value = ""
            show_search_page()

        except Exception as ex:
            error_text.value = (
                f"❌ خطأ! تأكد من مسار الملف أو صحة البيانات بداخلة."
            )
            page.update()

    def show_home(e=None):
        page.views.clear()
        page.views.append(
            ft.View(
                route="/",
                controls=[
                    ft.AppBar(
                        title=ft.Text("الصفحة الرئيسية"), bgcolor="blue"
                    ),
                    ft.Text(
                        "مرحباً بك في نظام إدارة المحطات",
                        size=22,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Text("مشروع DistDebila", size=14, color="grey"),
                    ft.Divider(),
                    send_input,
                    error_text,
                    ft.Button(
                        content=ft.Text("الدخول إلى نظام البحث والاستعلام"),
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
        search_input = ft.TextField(
            label="أدخل اسم المحطة بدقة", hint_text="مثال: P10", width=250
        )
        result_container = ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )

        def search_clicked(ev):
            target_poste = search_input.value.strip()
            result_container.controls.clear()

            if target_poste == "":
                result_container.controls.append(
                    ft.Text("⚠️ يرجى كتابة اسم المحطة أولاً!", color="red")
                )
            elif res_df is None:
                result_container.controls.append(
                    ft.Text("❌ البيانات غير محملة بشكل صحيح!", color="red")
                )
            else:
                match = res_df[
                    res_df["POSTE"].astype(str).str.lower() == target_poste.lower()
                ]

                if not match.empty:
                    row = match.iloc[0]
                    date_str = str(row["DATE"])
                    puissance_val = row.get("PUISSANCE", "غير متوفر")

                    result_container.controls.append(
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(
                                        f"📊 بيانات واستطاعة المحطة المكتشفة: {row['POSTE']}",
                                        size=18,
                                        weight="bold",
                                        color="blue",
                                    ),
                                    ft.Divider(),
                                    ft.Text(
                                        "⚡ قراءات التيار (A):",
                                        size=14,
                                        weight="bold",
                                        color="blue",
                                    ),
                                    ft.Text(f"  ▪️ I1: {row['I1']}"),
                                    ft.Text(f"  ▪️ I2: {row['I2']}"),
                                    ft.Text(f"  ▪️ I3: {row['I3']}"),
                                    ft.Text(
                                        f"  📈 Total I: {row['Total_I']}",
                                        weight="bold",
                                        color="green",
                                    ),
                                    ft.Divider(),
                                    ft.Text(
                                        "🔌 قراءات الجهد (V):",
                                        size=14,
                                        weight="bold",
                                        color="orange",
                                    ),
                                    ft.Text(f"  ▪️ V1: {row['V1']}"),
                                    ft.Text(f"  ▪️ V2: {row['V2']}"),
                                    ft.Text(f"  ▪️ V3: {row['V3']}"),
                                    ft.Divider(),
                                    ft.Text(
                                        "📈 الاستطاعة الكلية:",
                                        size=14,
                                        weight="bold",
                                        color="purple",
                                    ),
                                    ft.Text(
                                        f"  ▪️ PUISSANCE: {puissance_val}",
                                        size=16,
                                        weight="bold",
                                        color="purple_700",
                                    ),
                                    ft.Divider(),
                                    ft.Text(
                                        f"📅 تاريخ قياس المحطة: {date_str}",
                                        size=14,
                                        weight="bold",
                                        color="purple",
                                    ),
                                ],
                                spacing=6,
                            ),
                            padding=15,
                            border=ft.Border.all(width=1, color="blue_grey"),
                            border_radius=10,
                            bgcolor="#f5f5f5",
                            width=450,
                        )
                    )
                else:
                    result_container.controls.append(
                        ft.Text(
                            "❌ عذراً، لم يتم العثور على هذه المحطة!",
                            color="red",
                        )
                    )
            page.update()

        page.views.clear()
        page.views.append(
            ft.View(
                route="/search",
                controls=[
                    ft.AppBar(
                        title=ft.Text("نافذة البحث والاستعلام"),
                        bgcolor="green",
                    ),
                    ft.Text("استعلام عن محطة كهربائية", size=18, weight="bold"),
                    ft.Row(
                        [
                            search_input,
                            ft.Button(
                                content=ft.Text("ابحث"), on_click=search_clicked
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    ft.Divider(),
                    result_container,
                    ft.Divider(),
                    ft.Button(
                        content=ft.Text("الرجوع للرئيسية"), on_click=show_home
                    ),
                ],
                vertical_alignment=ft.MainAxisAlignment.START,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
        page.update()

    show_home()


ft.run(main)
