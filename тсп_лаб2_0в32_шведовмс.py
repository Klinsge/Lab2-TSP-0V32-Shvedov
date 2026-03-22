import math
import tkinter as tk
from tkinter import ttk, messagebox


class BondLabCalculator:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Лабораторная работа: биномиальная модель и ZCB")
        self.root.geometry("1280x860")

        self.n_var = tk.IntVar(value=10)
        self.T_var = tk.DoubleVar(value=10.0)
        self.r0_var = tk.DoubleVar(value=0.05)
        self.face_var = tk.DoubleVar(value=100.0)
        self.sigma_var = tk.DoubleVar(value=0.1)

        self.exec_t_var = tk.IntVar(value=6)
        self.exec_k_var = tk.IntVar(value=8)
        self.strike_var = tk.DoubleVar(value=70.0)
        self.strike2_var = tk.DoubleVar(value=80.0)

        self.tree_rates = None
        self.tree_zcb = None
        self.tree_zcb_t = None
        self.tree_futures = None
        self.tree_option = None
        self.tree_option2 = None
        self.output_text = None

        self._build_ui()

    # ------------------------- UI -------------------------
    def _build_ui(self):
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        top = ttk.Frame(main)
        top.pack(fill="x")

        params = ttk.LabelFrame(top, text="Параметры модели", padding=10)
        params.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self._add_entry(params, "Число периодов n", self.n_var, 0)
        self._add_entry(params, "Срок T (лет)", self.T_var, 1)
        self._add_entry(params, "Начальная ставка r₀", self.r0_var, 2)
        self._add_entry(params, "Номинал облигации", self.face_var, 3)
        self._add_entry(params, "Волатильность σ", self.sigma_var, 4)

        tasks = ttk.LabelFrame(top, text="Параметры расчётов", padding=10)
        tasks.pack(side="left", fill="x", expand=True)

        self._add_entry(tasks, "Момент исполнения форварда t", self.exec_t_var, 0)
        self._add_entry(tasks, "Момент исполнения фьючерса k", self.exec_k_var, 1)
        self._add_entry(tasks, "Страйк опциона E1", self.strike_var, 2)
        self._add_entry(tasks, "Страйк опциона E2", self.strike2_var, 3)

        btns = ttk.Frame(main)
        btns.pack(fill="x", pady=10)

        ttk.Button(btns, text="Рассчитать всё", command=self.calculate_all).pack(side="left", padx=5)
        ttk.Button(btns, text="Очистить вывод", command=self.clear_output).pack(side="left", padx=5)
        ttk.Button(btns, text="Заполнить пример", command=self.fill_example).pack(side="left", padx=5)

        notebook = ttk.Notebook(main)
        notebook.pack(fill="both", expand=True)

        rates_tab = ttk.Frame(notebook, padding=10)
        zcb_tab = ttk.Frame(notebook, padding=10)
        zcb_t_tab = ttk.Frame(notebook, padding=10)
        futures_tab = ttk.Frame(notebook, padding=10)
        option_tab = ttk.Frame(notebook, padding=10)
        option2_tab = ttk.Frame(notebook, padding=10)
        summary_tab = ttk.Frame(notebook, padding=10)

        notebook.add(rates_tab, text="Матрица ставок")
        notebook.add(zcb_tab, text="Матрица ZCB₁₀")
        notebook.add(zcb_t_tab, text="Матрица ZCBt")
        notebook.add(futures_tab, text="Матрица фьючерса")
        notebook.add(option_tab, text="Опцион E1")
        notebook.add(option2_tab, text="Опцион E2")
        notebook.add(summary_tab, text="Итоги расчётов")

        self.tree_rates = self._create_tree(rates_tab)
        self.tree_zcb = self._create_tree(zcb_tab)
        self.tree_zcb_t = self._create_tree(zcb_t_tab)
        self.tree_futures = self._create_tree(futures_tab)
        self.tree_option = self._create_tree(option_tab)
        self.tree_option2 = self._create_tree(option2_tab)

        self.output_text = tk.Text(summary_tab, wrap="word", font=("Consolas", 11))
        self.output_text.pack(fill="both", expand=True)

    def _add_entry(self, parent, label, variable, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(parent, textvariable=variable, width=16).grid(row=row, column=1, sticky="ew", padx=5, pady=5)
        parent.columnconfigure(1, weight=1)

    def _create_tree(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)

        tree = ttk.Treeview(frame, show="headings")
        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        return tree

    # ------------------------- Math -------------------------
    def get_inputs(self):
        n = int(self.n_var.get())
        T = float(self.T_var.get())
        r0 = float(self.r0_var.get())
        face = float(self.face_var.get())
        sigma = float(self.sigma_var.get())
        t_exec = int(self.exec_t_var.get())
        k_exec = int(self.exec_k_var.get())
        strike1 = float(self.strike_var.get())
        strike2 = float(self.strike2_var.get())

        if n <= 0:
            raise ValueError("n должно быть положительным")
        if T <= 0:
            raise ValueError("T должно быть положительным")
        if face <= 0:
            raise ValueError("Номинал должен быть положительным")
        if sigma < 0:
            raise ValueError("σ не может быть отрицательной")
        if not (0 <= t_exec <= n):
            raise ValueError("t должно быть в диапазоне от 0 до n")
        if not (0 <= k_exec <= n):
            raise ValueError("k должно быть в диапазоне от 0 до n")
        if strike1 < 0 or strike2 < 0:
            raise ValueError("Страйк не может быть отрицательным")

        return n, T, r0, face, sigma, t_exec, k_exec, strike1, strike2

    def build_short_rate_tree(self, n, T, r0, sigma):
        dt = T / n
        u = math.exp(sigma * math.sqrt(dt))
        d = 1.0 / u
        p = (math.exp(r0 * dt) - d) / (u - d)
        q = 1.0 - p

        if not (0.0 <= p <= 1.0 and 0.0 <= q <= 1.0):
            raise ValueError(
                f"Некорректные вероятности: p={p:.6f}, q={q:.6f}. "
                "Проверьте r₀, σ, n, T."
            )

        rates = []
        for i in range(n + 1):
            level_rates = []
            for j in range(i + 1):
                r_ij = r0 * (u ** j) * (d ** (i - j))
                level_rates.append(r_ij)
            rates.append(level_rates)

        return dt, u, d, p, q, rates

    def build_zcb_tree(self, n, face, rates, p, q):
        # zcb[i][j] = стоимость в узле (i, j) бескупонной облигации со сроком погашения в момент n
        # Дисконтирование:
        # F = (p * F_u + q * F_d) / (1 + r)
        zcb = [[0.0 for _ in range(i + 1)] for i in range(n + 1)]

        for j in range(n + 1):
            zcb[n][j] = face

        for i in range(n - 1, -1, -1):
            for j in range(i + 1):
                fu = zcb[i + 1][j + 1]
                fd = zcb[i + 1][j]
                r = rates[i][j]
                zcb[i][j] = (p * fu + q * fd) / (1.0 + r)

        return zcb

    def build_generic_zcb_to_maturity(self, maturity, face, rates, p, q):
        tree = [[0.0 for _ in range(i + 1)] for i in range(maturity + 1)]

        for j in range(maturity + 1):
            tree[maturity][j] = face

        for i in range(maturity - 1, -1, -1):
            for j in range(i + 1):
                fu = tree[i + 1][j + 1]
                fd = tree[i + 1][j]
                r = rates[i][j]
                tree[i][j] = (p * fu + q * fd) / (1.0 + r)

        return tree

    def futures_price_tree(self, zcb, k, p, q):
        # Матрица расчёта фьючерса на ZCB10 до момента исполнения k.
        fut = [[0.0 for _ in range(i + 1)] for i in range(k + 1)]

        for j in range(k + 1):
            fut[k][j] = zcb[k][j]

        for i in range(k - 1, -1, -1):
            for j in range(i + 1):
                fut[i][j] = p * fut[i + 1][j + 1] + q * fut[i + 1][j]

        return fut

    def american_call_on_futures(self, futures_tree, strike, p, q):
        k = len(futures_tree) - 1
        option = [[0.0 for _ in range(i + 1)] for i in range(k + 1)]

        for j in range(k + 1):
            option[k][j] = max(futures_tree[k][j] - strike, 0.0)

        for i in range(k - 1, -1, -1):
            for j in range(i + 1):
                continuation = p * option[i + 1][j + 1] + q * option[i + 1][j]
                exercise = max(futures_tree[i][j] - strike, 0.0)
                option[i][j] = max(exercise, continuation)

        return option

    # ------------------------- Output helpers -------------------------
    def fill_tree_widget(self, tree_widget, matrix, title_prefix):
        n = len(matrix) - 1
        columns = ["row_label"] + [f"c{i}" for i in range(n + 1)]

        tree_widget.delete(*tree_widget.get_children())
        tree_widget["columns"] = columns

        tree_widget.heading("row_label", text="Период")
        tree_widget.column("row_label", width=110, anchor="center")

        for t in range(n + 1):
            tree_widget.heading(f"c{t}", text=str(t))
            tree_widget.column(f"c{t}", width=95, anchor="center")

        for state in range(n, -1, -1):
            display_row = [str(state)]

            for t in range(n + 1):
                if state <= t:
                    value = matrix[t][state]

                    if title_prefix.lower().startswith("r"):
                        display_row.append(f"{value * 100:.2f}%")
                    else:
                        display_row.append(f"{value:.2f}%")
                else:
                    display_row.append("")

            tree_widget.insert("", "end", values=display_row)

    def write_output(self, text):
        self.output_text.insert("end", text + "\n")
        self.output_text.see("end")

    def clear_output(self):
        self.output_text.delete("1.0", "end")

    def fill_example(self):
        self.n_var.set(10)
        self.T_var.set(10.0)
        self.r0_var.set(0.05)
        self.face_var.set(100.0)
        self.sigma_var.set(0.1)
        self.exec_t_var.set(6)
        self.exec_k_var.set(8)
        self.strike_var.set(70.0)
        self.strike2_var.set(80.0)

    # ------------------------- Main calculation -------------------------
    def calculate_all(self):
        try:
            self.clear_output()

            n, T, r0, face, sigma, t_exec, k_exec, strike1, strike2 = self.get_inputs()

            dt, u, d, p, q, rates = self.build_short_rate_tree(n, T, r0, sigma)
            zcb_10 = self.build_zcb_tree(n, face, rates, p, q)

            self.fill_tree_widget(self.tree_rates, rates, "r")
            self.fill_tree_widget(self.tree_zcb, zcb_10, "ZCB")

            zcb_t_tree = self.build_generic_zcb_to_maturity(t_exec, face, rates, p, q)
            self.fill_tree_widget(self.tree_zcb_t, zcb_t_tree, "ZCB")

            zcb_0_10 = zcb_10[0][0]
            zcb_0_t = zcb_t_tree[0][0]

            forward_0_t = zcb_0_10 / zcb_0_t if zcb_0_t != 0 else float("nan")

            futures_tree_k = self.futures_price_tree(zcb_10, k_exec, p, q)
            self.fill_tree_widget(self.tree_futures, futures_tree_k, "FUT")
            futures_0_k = futures_tree_k[0][0]

            option_tree1 = self.american_call_on_futures(futures_tree_k, strike1, p, q)
            option_tree2 = self.american_call_on_futures(futures_tree_k, strike2, p, q)

            self.fill_tree_widget(self.tree_option, option_tree1, "OPT")
            self.fill_tree_widget(self.tree_option2, option_tree2, "OPT")

            option_01 = option_tree1[0][0]
            option_02 = option_tree2[0][0]

            self.write_output("ЛАБОРАТОРНАЯ РАБОТА №2")
            self.write_output("Ценообразование облигаций со стохастической процентной ставкой")
            self.write_output("=" * 78)

            self.write_output("1. Параметры биномиальной модели:")
            self.write_output(f"   n = {n}")
            self.write_output(f"   T = {T}")
            self.write_output(f"   Δt = {dt:.0f}")
            self.write_output(f"   r₀ = {r0:.2f}")
            self.write_output(f"   Номинал = {face:.0f}")
            self.write_output(f"   σ = {sigma:.1f}")
            self.write_output(f"   u = {u:.6f}")
            self.write_output(f"   d = {d:.6f}")
            self.write_output(f"   p = {p:.6f}")
            self.write_output(f"   q = {q:.6f}")
            self.write_output("")

            self.write_output("2. Построена матрица стоимости 10-летней бескупонной облигации ZCB10.")
            self.write_output(f"   ZCB10(0,0) = {zcb_0_10:.6f}")
            self.write_output("")

            self.write_output(f"3. Цена форварда на бескупонную облигацию при экспирации t = {t_exec}:")
            self.write_output(
                f"   F₀({t_exec},{n}) = ZCB(0,{n}) / ZCB(0,{t_exec}) = "
                f"{zcb_0_10:.6f} / {zcb_0_t:.6f} = {forward_0_t:.6f}"
            )
            self.write_output("")

            self.write_output(f"4. Цена фьючерса на бескупонную облигацию ZCB10 при экспирации k = {k_exec}:")
            self.write_output(f"   Φ₀({k_exec}) = {futures_0_k:.6f}")
            self.write_output("")

            self.write_output("5. Цена опциона покупателя американского типа на фьючерс на ZCB10:")
            self.write_output(f"   при E = {strike1:.6f}:  C₀ = {option_01:.6f}")
            self.write_output(f"   при E = {strike2:.6f}:  C₀ = {option_02:.6f}")

        except Exception as e:
            messagebox.showerror("Ошибка расчёта", str(e))

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = BondLabCalculator()
    app.run()