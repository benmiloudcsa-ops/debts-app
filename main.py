import sqlite3
import flet as ft
from datetime import datetime

# ---- تهيئة قاعدة البيانات المحلية على الهاتف ----
def init_db():
    conn = sqlite3.connect("debts_store.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            type TEXT CHECK(type IN ('DEBT', 'PAYMENT')),
            amount REAL NOT NULL,
            note TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()

def main(page: ft.Page):
    init_db()
    
    page.title = "تسيير ديون المحل"
    page.rtl = True
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 15

    # عناصر التحكم والبحث
    search_input = ft.TextField(label="بحث باسم الزبون أو الهاتف...", expand=True, on_change=lambda e: refresh_customers(e.data))
    name_input = ft.TextField(label="اسم الزبون الجديد", expand=True)
    phone_input = ft.TextField(label="رقم الهاتف", expand=True)
    
    customers_list = ft.ListView(expand=True, spacing=10)

    # جلب الزبائن مع البحث
    def get_customers(query=""):
        conn = sqlite3.connect("debts_store.db")
        cursor = conn.cursor()
        if query:
            cursor.execute("SELECT id, name, phone FROM customers WHERE name LIKE ? OR phone LIKE ?", (f"%{query}%", f"%{query}%"))
        else:
            cursor.execute("SELECT id, name, phone FROM customers")
        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_customer_balance(customer_id):
        conn = sqlite3.connect("debts_store.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN type = 'DEBT' THEN amount ELSE 0 END) -
                SUM(CASE WHEN type = 'PAYMENT' THEN amount ELSE 0 END)
            FROM transactions WHERE customer_id = ?
        """, (customer_id,))
        bal = cursor.fetchone()[0]
        conn.close()
        return bal if bal else 0.0

    def refresh_customers(query=""):
        customers_list.controls.clear()
        for c_id, name, phone in get_customers(query):
            balance = get_customer_balance(c_id)
            color = "red" if balance > 0 else "green"
            
            card = ft.Card(
                content=ft.Container(
                    padding=12,
                    content=ft.Column([
                        ft.Row([
                            ft.Text(name, size=16, weight=ft.FontWeight.BOLD, expand=True),
                            ft.Text(f"{balance:.2f} د.ج", color=color, size=15, weight=ft.FontWeight.BOLD)
                        ]),
                        ft.Row([
                            ft.Text(f"الهاتف: {phone if phone else 'غير محدد'}", size=12, color=ft.Colors.GREY_700, expand=True),
                            ft.ElevatedButton("إضافة عملية", scale=0.8, on_click=lambda e, cid=c_id, cname=name: open_trans_dialog(cid, cname))
                        ])
                    ])
                )
            )
            customers_list.controls.append(card)
        page.update()

    def handle_add_customer(e):
        if name_input.value:
            conn = sqlite3.connect("debts_store.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO customers (name, phone) VALUES (?, ?)", (name_input.value, phone_input.value))
            conn.commit()
            conn.close()
            name_input.value = ""
            phone_input.value = ""
            refresh_customers()

    # حوار إضافة معاملة (دين / تسديد)
    selected_customer = [None, ""]
    trans_amount = ft.TextField(label="المبلغ", keyboard_type=ft.KeyboardType.NUMBER)
    trans_note = ft.TextField(label="ملاحظة / السلعة")
    trans_type = ft.Dropdown(
        label="نوع العملية",
        options=[
            ft.dropdown.Option("DEBT", "دين جديد (+)"),
            ft.dropdown.Option("PAYMENT", "تسديد (-)"),
        ],
        value="DEBT"
    )

    def save_transaction(e):
        if selected_customer[0] and trans_amount.value:
            try:
                amt = float(trans_amount.value)
                conn = sqlite3.connect("debts_store.db")
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO transactions (customer_id, type, amount, note) VALUES (?, ?, ?, ?)",
                    (selected_customer[0], trans_type.value, amt, trans_note.value)
                )
                conn.commit()
                conn.close()
                trans_dialog.open = False
                trans_amount.value = ""
                trans_note.value = ""
                refresh_customers()
                page.update()
            except ValueError:
                pass

    trans_dialog = ft.AlertDialog(
        title=ft.Text("عملية جديدة"),
        content=ft.Column([
            trans_type,
            trans_amount,
            trans_note
        ], tight=True),
        actions=[
            ft.TextButton("إلغاء", on_click=lambda e: setattr(trans_dialog, 'open', False) or page.update()),
            ft.ElevatedButton("حفظ", on_click=save_transaction)
        ]
    )

    def open_trans_dialog(cid, cname):
        selected_customer[0] = cid
        selected_customer[1] = cname
        page.overlay.append(trans_dialog)
        trans_dialog.open = True
        page.update()

    # تصميم الواجهة الرئيسية للهاتف
    page.add(
        ft.Text("🛒 تسيير ديون المحل", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800),
        ft.Divider(),
        ft.Row([name_input, phone_input]),
        ft.ElevatedButton("إضافة زبون جديد", on_click=handle_add_customer, bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE),
        ft.Divider(),
        search_input,
        ft.Text("قائمة الزبائن:", size=16, weight=ft.FontWeight.BOLD),
        customers_list
    )

    refresh_customers()

ft.app(target=main)