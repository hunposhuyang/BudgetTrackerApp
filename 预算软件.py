import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
from tkcalendar import DateEntry
from babel.numbers import format_currency
import sqlite3
import matplotlib
import matplotlib.pyplot as plt
import sys
import os

matplotlib.rcParams['font.family'] = 'SimSun'  # 指定宋体为中文字体

# 设置数据库连接
# 获取可执行文件所在的目录
executable_dir = os.path.dirname(sys.argv[0])
db_path = os.path.join(executable_dir, 'my_budget.db')

# 连接到SQLite数据库
conn = sqlite3.connect(db_path)
c = conn.cursor()

# 更新数据库表结构
c.execute('''CREATE TABLE IF NOT EXISTS budget (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                amount REAL NOT NULL
            )''')

c.execute('''CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                expense REAL NOT NULL,
                note TEXT,
                date TEXT NOT NULL
            )''')

# 检查 initial_budget 表是否存在
c.execute('''SELECT count(name) FROM sqlite_master WHERE type='table' AND name='initial_budget' ''')
if c.fetchone()[0] == 0:
    # 如果不存在，创建 initial_budget 表并添加 amount 列
    c.execute('''CREATE TABLE initial_budget (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount REAL NOT NULL
                )''')
    conn.commit()

    # 插入初始预算金额
    c.execute('''INSERT INTO initial_budget (amount) VALUES (0.0)''')
    conn.commit()
else:
    # 如果存在 initial_budget 表，检查是否已经有 amount 列
    c.execute('''PRAGMA table_info(initial_budget)''')
    columns = c.fetchall()
    has_amount_column = any(column[1] == 'amount' for column in columns)
    if not has_amount_column:
        # 如果没有 amount 列，添加该列
        c.execute('''ALTER TABLE initial_budget ADD COLUMN amount REAL NOT NULL''')
        conn.commit()
        
class BudgetTracker:
    def __init__(self, root):
        self.root = root
        self.root.title("预算跟踪器")
        self.initial_budget = 0.0
        self.conn = sqlite3.connect(db_path)
        self.c = self.conn.cursor()
        self.load_budget_data()
        self.create_widgets()

    def load_budget_data(self):
        # 从数据库加载预算数据
        c.execute('SELECT * FROM budget')
        budget_data = c.fetchall()
        self.budgets = {row[1]: row[2] for row in budget_data}
        
        # 从 initial_budget 表中加载初始预算金额
        c.execute('SELECT amount FROM initial_budget')
        initial_budget_data = c.fetchone()
        if initial_budget_data:
            self.initial_budget = initial_budget_data[0]
        else:
            self.initial_budget = 0.0

        # 计算总预算
        self.total_budget = sum(self.budgets.values())
        
    def save_budget_data(self):
        # 保存预算数据到数据库
        c.execute('DELETE FROM budget')
        for category, amount in self.budgets.items():
            c.execute('INSERT INTO budget (category, amount) VALUES (?, ?)', (category, amount))
        
        # 更新总预算金额
        self.total_budget = sum(self.budgets.values())
        c.execute('UPDATE initial_budget SET amount = ?', (self.total_budget,))
        conn.commit()

    def create_widgets(self):
        # 创建界面组件
        self.create_display_widgets()
        self.create_input_widgets()
        self.create_restart_button()

    
    def create_input_widgets(self):
        # 创建输入部件
        input_frame = ttk.Frame(self.root)
        input_frame.grid(row=0, column=0, pady=10)

        ttk.Label(input_frame, text="支出金额(元):").grid(row=0, column=0, padx=5, pady=5)
        self.expense_entry = ttk.Entry(input_frame)
        self.expense_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(input_frame, text="支出类别:").grid(row=1, column=0, padx=5, pady=5)
        default_category = list(self.budgets.keys())[0] if self.budgets else "默认类别"
        self.category_var = tk.StringVar()
        self.category_var.set(default_category)
        self.category_dropdown = ttk.OptionMenu(input_frame, self.category_var, default_category, *list(self.budgets.keys()))
        self.category_dropdown.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(input_frame, text="备注:").grid(row=0, column=2, padx=5, pady=5)
        self.note_entry = ttk.Entry(input_frame)
        self.note_entry.grid(row=0, column=3, padx=5, pady=5)

        ttk.Button(input_frame, text="提交", command=self.update_budget_and_balance).grid(row=0, column=4, columnspan=1, padx=5)

        # 添加按钮来执行创建和删除预算、预算类别、支出类别的操作
        ttk.Button(input_frame, text="创建预算", command=self.create_budget).grid(row=1, column=2, pady=5)
        ttk.Button(input_frame, text="删除预算", command=self.delete_budget).grid(row=1, column=3, pady=5)

    def create_display_widgets(self):
        # 创建显示部件
        display_frame = ttk.Frame(self.root)
        display_frame.grid(row=3, column=0, pady=5)

        self.budget_label = ttk.Label(display_frame, text="")
        self.budget_label.grid(row=1, column=0, pady=(5, 0))


        ttk.Label(display_frame, text="图表类型:").grid(row=0, column=1, padx=5, pady=(5, 0))
        self.chart_type_combobox = ttk.Combobox(display_frame, values=["饼图", "柱状图"], state="readonly")
        self.chart_type_combobox.set("饼图")
        self.chart_type_combobox.grid(row=0, column=2, padx=5, pady=(5, 0))
        ttk.Button(display_frame, text="数据分析", command=self.analyze_data).grid(row=0, column=3, pady=(5, 0))

        filter_frame = ttk.Frame(self.root)
        filter_frame.grid(row=1, column=0, pady=(5, 0))

        ttk.Label(filter_frame, text="开始日期:").grid(row=0, column=0, padx=5, pady=5)
        self.start_date_entry = DateEntry(filter_frame, width=12, background='darkblue', foreground='white', borderwidth=2)
        self.start_date_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(filter_frame, text="结束日期:").grid(row=0, column=2, padx=5, pady=5)
        self.end_date_entry = DateEntry(filter_frame, width=12, background='darkblue', foreground='white', borderwidth=2)
        self.end_date_entry.grid(row=0, column=3, padx=5, pady=5)

        ttk.Button(filter_frame, text="搜索", command=self.search_expenses).grid(row=0, column=4, padx=5, pady=5)

        # Display expenses list
        expenses_frame = ttk.Frame(self.root)
        expenses_frame.grid(row=2, column=0, pady=(0, 10))
        self.expenses_list = ttk.Treeview(expenses_frame, columns=("category", "expense", "note", "date"), show="headings")
        self.expenses_list.heading("category", text="类别")
        self.expenses_list.heading("expense", text="金额")
        self.expenses_list.heading("note", text="备注")
        self.expenses_list.heading("date", text="日期")
        self.expenses_list.column("category", width=60)
        self.expenses_list.column("expense", width=80)
        self.expenses_list.column("note", width=60)
        self.expenses_list.column("date", width=160)
        self.expenses_list.grid(row=0, column=0, sticky="nsew")
        ttk.Button(filter_frame, text="撤销支出", command=self.undo_selected_expense).grid(row=0, column=5, padx=5, pady=5)
        # 添加垂直滚动条
        expenses_scrollbar = ttk.Scrollbar(expenses_frame, orient="vertical", command=self.expenses_list.yview)
        expenses_scrollbar.grid(row=0, column=1, sticky="ns")
        self.expenses_list.configure(yscrollcommand=expenses_scrollbar.set)
        # Load expenses list initially
        self.load_expenses_list()
        
        # 创建预算表显示部件
        budget_frame = ttk.Frame(expenses_frame) 
        budget_frame.grid(row=0, column=2, pady=0)

        # 创建表格来显示预算信息
        self.budget_tree = ttk.Treeview(budget_frame, columns=("Category", "Amount"), show="headings")
        self.budget_tree.heading("Category", text="类别")
        self.budget_tree.heading("Amount", text="金额")
        self.budget_tree.column("Category", width=100)
        self.budget_tree.column("Amount", width=100)
        self.budget_tree.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")

        # 添加滚动条
        budget_scrollbar = ttk.Scrollbar(budget_frame, orient="vertical", command=self.budget_tree.yview)
        budget_scrollbar.grid(row=0, column=1, sticky="ns")
        self.budget_tree.configure(yscrollcommand=budget_scrollbar.set)
        #水平滚动条
        #budget_scrollbar = ttk.Scrollbar(budget_frame, orient="horizontal", command=self.budget_tree.xview)
        #budget_scrollbar.grid(row=1, column=0, sticky="ew")
        #self.budget_tree.configure(xscrollcommand=budget_scrollbar.set)

        # 加载预算信息到表格
        self.load_budget_to_tree()
    def update_budget_and_balance(self):
        # 更新预算和余额
        expense_str = self.expense_entry.get().strip()
        note = self.note_entry.get().strip()

        if not expense_str:
            messagebox.showerror("错误", "请输入支出金额。")
            return

        try:
            expense = float(expense_str)
            if expense <= 0:
                messagebox.showerror("错误", "支出金额必须大于零。")
                return
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数值。")
            return

        category = self.category_var.get()

        if category not in self.budgets:
            messagebox.showerror("错误", f"无效的支出类别 '{category}'。")
            return

        if expense > self.budgets[category]:
            messagebox.showerror("错误", f"超出 '{category}' 预算。")
            return

        self.budgets[category] -= expense
        self.initial_budget -= expense

        expense_record = {
            "category": category,
            "expense": expense,
            "note": note,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        c.execute('INSERT INTO expenses (category, expense, note, date) VALUES (?, ?, ?, ?)', (category, expense, note, expense_record["date"]))
        self.save_budget_data()
        self.create_display_widgets()
        self.check_reminder(category)
        self.expense_entry.delete(0, 'end')
        self.note_entry.delete(0, 'end')

    def load_budget_to_tree(self):
        # 清除表格中的内容
        for record in self.budget_tree.get_children():
            self.budget_tree.delete(record)
        
        # 将预算信息加载到表格中
        for category, amount in self.budgets.items():
            self.budget_tree.insert("", "end", values=(category, format_currency(amount, 'CNY', locale='zh_CN')))
        
        # 添加总预算行
        self.budget_tree.insert("", "end", values=("总预算", format_currency(self.total_budget, 'CNY', locale='zh_CN')))


    def create_restart_button(self):
        # 创建重启按钮
        restart_frame = ttk.Frame(self.root)
        restart_frame.grid(row=4, column=0, pady=10)

        ttk.Button(restart_frame, text="重启", command=self.restart_program).pack()

    def restart_program(self):
        # 重启程序
        python = sys.executable
        # 调整命令行参数，确保路径被正确处理
        args = ['"{}"'.format(arg) for arg in sys.argv]
        os.execl(python, python, *args)

    def load_expenses_list(self, expenses=None):
        # 清除之前的记录
        self.expenses_list.delete(*self.expenses_list.get_children())

        if not expenses:
            # 如果未提供支出记录，则从数据库中获取
            self.c.execute('SELECT category, expense, note, date FROM expenses ORDER BY date DESC')
            expenses = self.c.fetchall()

        # 填充支出记录列表
        for category, expense, note, date in expenses:
            self.expenses_list.insert("", tk.END, values=(category, expense, note, date))
    
    def check_reminder(self, category):
        # 检查预算提醒
        if self.budgets[category] < 50:
            messagebox.showwarning("提醒", f"{category}预算即将用尽！")

    def analyze_data(self):
        # 分析数据
        c.execute('SELECT * FROM expenses')
        self.expenses = c.fetchall()
        
        if not self.expenses:
            messagebox.showinfo("信息", "没有足够的数据进行分析。")
            return

        category_expenses = {category: 0 for category in self.budgets.keys()}
        for expense_record in self.expenses:
            category_expenses[expense_record[1]] += expense_record[2]

        if self.chart_type_combobox.get() == "饼图":
            plt.figure(figsize=(8, 6))
            plt.pie(category_expenses.values(), labels=category_expenses.keys(), autopct='%1.1f%%', startangle=140)
            plt.title("支出类别分布")
            plt.axis('equal')
            plt.show()
        elif self.chart_type_combobox.get() == "柱状图":
            plt.figure(figsize=(10, 6))
            plt.bar(category_expenses.keys(), category_expenses.values(), color='skyblue')
            plt.xlabel("支出类别")
            plt.ylabel("支出金额")
            plt.title("支出类别分布")
            plt.xticks(rotation=45)
            plt.show()
        return

    def search_expenses(self):
        start_date = self.start_date_entry.get_date()
        end_date = self.end_date_entry.get_date()

        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        self.c.execute('SELECT category, expense, note, date FROM expenses WHERE date BETWEEN ? AND ?', 
                    (start_datetime.strftime("%Y-%m-%d %H:%M:%S"), end_datetime.strftime("%Y-%m-%d %H:%M:%S")))
        filtered_expenses = self.c.fetchall()

        self.load_expenses_list(filtered_expenses)

    def undo_selected_expense(self):
        # 获取选中的支出记录的ID列表
        selected_ids = self.expenses_list.selection()
        
        # 如果没有选择任何记录，显示提示信息
        if not selected_ids:
            messagebox.showinfo("信息", "请先选择一条支出记录。")
            return
        
        # 假设每次只撤销一条记录，取selection中的第一个ID
        selected_id = selected_ids[0]
        
        # 获取选中行的数据
        selected_expense = self.expenses_list.item(selected_id)
        if not selected_expense:  # 确保获取的数据不为空
            messagebox.showerror("错误", "所选项目无效。")
            return
        
        # 提取支出记录的详细信息
        category = selected_expense['values'][0]
        expense_amount = selected_expense['values'][1]
        note = selected_expense['values'][2]
        expense_date = selected_expense['values'][-1]  # 假设日期字段是values的最后一个元素

        # 确认是否撤销
        confirm = messagebox.askyesno("确认撤销", f"您确定要撤销以下支出吗？\n\n类别: {category}, 金额: {format_currency(expense_amount, 'CNY', locale='zh_CN')}元, 备注: {note}, 日期: {expense_date}")
        if not confirm:
            return

        # 从数据库中删除这条记录
        try:
            c.execute('DELETE FROM expenses WHERE category = ? AND expense = ? AND note = ? AND date = ?', (category, expense_amount, note, expense_date))
            conn.commit()
            messagebox.showinfo("成功", "支出记录已撤销。")
        except sqlite3.Error as e:
            messagebox.showerror("错误", f"撤销失败: {e}")
            return
        
        #增加相应预算
        expense_amount_float = float(expense_amount)
        self.budgets[category] += expense_amount_float
        c.execute('UPDATE budget SET amount = amount + ? WHERE category = ?', (expense_amount_float, category))
        conn.commit()

        # 更新预算和显示信息
        self.load_budget_data()
        self.create_display_widgets()
        self.load_expenses_list()  # 重新加载支出记录列表

    def create_budget(self):
        category = simpledialog.askstring("创建预算", "请输入预算类别:", parent=self.root)
        if category:
            amount = simpledialog.askfloat("创建预算", f"请输入 '{category}' 的预算金额:", parent=self.root)
            if amount is not None:
                self.budgets[category] = amount
                c.execute('INSERT INTO budget (category, amount) VALUES (?, ?)', (category, amount))
                conn.commit()
                messagebox.showinfo("成功", "预算创建成功。")
                self.display_budget()

    def delete_budget(self):
        if not self.budgets:
            messagebox.showinfo("提示", "没有预算可供删除。")
            return

        category = simpledialog.askstring("删除预算", "请选择要删除的预算类别:", initialvalue=list(self.budgets.keys())[0])
        if category and category in self.budgets:
            confirm = messagebox.askyesno("确认删除", f"您确定要删除 '{category}' 的预算吗？")
            if confirm:
                del self.budgets[category]
                c.execute('DELETE FROM budget WHERE category = ?', (category,))
                conn.commit()
                messagebox.showinfo("成功", "预算删除成功。")
                self.display_budget()

    def create_budget_category(self):
        category = simpledialog.askstring("创建预算类别", "请输入新的预算类别:")
        if category:
            c.execute('INSERT INTO budget (category, amount) VALUES (?, 0.0)', (category,))
            conn.commit()
            messagebox.showinfo("成功", "预算类别创建成功。")
            self.load_budget_data()
            self.display_budget()

    def delete_budget_category(self):
        categories = list(self.budgets.keys())
        if not categories:
            messagebox.showinfo("提示", "没有预算类别可供删除。")
            return

        category = simpledialog.askstring("删除预算类别", "请选择要删除的预算类别:", initialvalue=categories[0])
        if category and category in categories:
            confirm = messagebox.askyesno("确认删除", f"您确定要删除 '{category}' 的预算类别吗？\n（注意：将同时删除该类别下的所有预算记录）")
            if confirm:
                del self.budgets[category]
                c.execute('DELETE FROM budget WHERE category = ?', (category,))
                conn.commit()
                messagebox.showinfo("成功", "预算类别删除成功。")
                self.load_budget_data()
                self.display_budget()

    def create_expense_category(self):
        category = simpledialog.askstring("创建支出类别", "请输入新的支出类别:")
        if category:
            c.execute('INSERT INTO expenses (category, expense, note, date) VALUES (?, 0.0, "", ?)', (category, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            messagebox.showinfo("成功", "支出类别创建成功。")

    def delete_expense_category(self):
        c.execute('SELECT DISTINCT category FROM expenses')
        categories = [row[0] for row in c.fetchall()]

        if not categories:
            messagebox.showinfo("提示", "没有支出类别可供删除。")
            return

        category = simpledialog.askstring("删除支出类别", "请选择要删除的支出类别:", initialvalue=categories[0])
        if category and category in categories:
            confirm = messagebox.askyesno("确认删除", f"您确定要删除 '{category}' 的支出类别吗？\n（注意：将同时删除该类别下的所有支出记录）")
            if confirm:
                c.execute('DELETE FROM expenses WHERE category = ?', (category,))
                conn.commit()
                messagebox.showinfo("成功", "支出类别删除成功。")

root = tk.Tk()
app = BudgetTracker(root)
root.mainloop()

# 关闭数据库连接
conn.close()
