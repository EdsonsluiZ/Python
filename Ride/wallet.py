# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from datetime import datetime, date

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


ARQUIVO_EXCEL = Path(r"C:/Python/Ride/Report de Ganhos/Relatorio_Ganhos_Uber_Driver_Sheet4.xlsx")
NOME_SHEET = "Sheet4"
TRANSFERENCIA_TEXTO = "Transferido para a conta bancária"


class WalletApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Wallet - Controle de Ganhos Uber")
        self.root.geometry("1100x700")
        self.root.minsize(1000, 650)

        self.df = pd.DataFrame()
        self.total_wallet = 0.0
        self.resumo_diario = pd.DataFrame()
        self.resumo_tipo = pd.DataFrame()

        self.criar_interface()
        self.carregar_dados()

    def criar_interface(self):
        self.frame_topo = ttk.Frame(self.root, padding=10)
        self.frame_topo.pack(fill="x")

        self.lbl_titulo = ttk.Label(
            self.frame_topo,
            text="Wallet - Controle Contábil de Ganhos",
            font=("Arial", 18, "bold")
        )
        self.lbl_titulo.pack(side="left")

        self.btn_atualizar = ttk.Button(
            self.frame_topo,
            text="Atualizar Dados",
            command=self.carregar_dados
        )
        self.btn_atualizar.pack(side="right")

        self.frame_total = ttk.LabelFrame(self.root, text="Total Wallet", padding=15)
        self.frame_total.pack(fill="x", padx=10, pady=5)

        self.var_total_wallet = tk.StringVar(value="R$ 0,00")

        self.lbl_total = ttk.Label(
            self.frame_total,
            textvariable=self.var_total_wallet,
            font=("Arial", 24, "bold")
        )
        self.lbl_total.pack(anchor="w")

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.frame_diario = ttk.Frame(self.notebook, padding=10)
        self.frame_grafico = ttk.Frame(self.notebook, padding=10)
        self.frame_lancamentos = ttk.Frame(self.notebook, padding=10)

        self.notebook.add(self.frame_diario, text="Fechamento Diário")
        self.notebook.add(self.frame_grafico, text="Gráfico por Tipo")
        self.notebook.add(self.frame_lancamentos, text="Lançamentos")

        self.criar_tabela_diaria()
        self.criar_area_grafico()
        self.criar_tabela_lancamentos()

    def criar_tabela_diaria(self):
        colunas = ("data", "ganhos", "transferencias", "saldo_dia")

        self.tree_diario = ttk.Treeview(
            self.frame_diario,
            columns=colunas,
            show="headings",
            height=18
        )

        self.tree_diario.heading("data", text="Data")
        self.tree_diario.heading("ganhos", text="Ganhos")
        self.tree_diario.heading("transferencias", text="Transferências")
        self.tree_diario.heading("saldo_dia", text="Saldo do Dia")

        self.tree_diario.column("data", width=120, anchor="center")
        self.tree_diario.column("ganhos", width=160, anchor="e")
        self.tree_diario.column("transferencias", width=160, anchor="e")
        self.tree_diario.column("saldo_dia", width=160, anchor="e")

        scroll_y = ttk.Scrollbar(self.frame_diario, orient="vertical", command=self.tree_diario.yview)
        self.tree_diario.configure(yscrollcommand=scroll_y.set)

        self.tree_diario.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")

    def criar_area_grafico(self):
        self.frame_canvas_grafico = ttk.Frame(self.frame_grafico)
        self.frame_canvas_grafico.pack(fill="both", expand=True)

    def criar_tabela_lancamentos(self):
        colunas = ("data", "tipo", "hora", "valor", "movimento")

        self.tree_lancamentos = ttk.Treeview(
            self.frame_lancamentos,
            columns=colunas,
            show="headings",
            height=18
        )

        self.tree_lancamentos.heading("data", text="Data")
        self.tree_lancamentos.heading("tipo", text="Tipo")
        self.tree_lancamentos.heading("hora", text="Hora")
        self.tree_lancamentos.heading("valor", text="Valor")
        self.tree_lancamentos.heading("movimento", text="Movimento")

        self.tree_lancamentos.column("data", width=110, anchor="center")
        self.tree_lancamentos.column("tipo", width=260, anchor="w")
        self.tree_lancamentos.column("hora", width=100, anchor="center")
        self.tree_lancamentos.column("valor", width=130, anchor="e")
        self.tree_lancamentos.column("movimento", width=130, anchor="center")

        scroll_y = ttk.Scrollbar(self.frame_lancamentos, orient="vertical", command=self.tree_lancamentos.yview)
        self.tree_lancamentos.configure(yscrollcommand=scroll_y.set)

        self.tree_lancamentos.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")

    def carregar_dados(self):
        try:
            if not ARQUIVO_EXCEL.exists():
                messagebox.showerror("Erro", f"Arquivo não encontrado:\n{ARQUIVO_EXCEL}")
                return

            df = pd.read_excel(ARQUIVO_EXCEL, sheet_name=NOME_SHEET)

            colunas_obrigatorias = {"Data", "Tipo", "Hora", "Valor"}
            colunas_arquivo = set(df.columns)

            if not colunas_obrigatorias.issubset(colunas_arquivo):
                messagebox.showerror(
                    "Erro",
                    "A Sheet4 precisa conter as colunas: Data, Tipo, Hora e Valor."
                )
                return

            df = df[["Data", "Tipo", "Hora", "Valor"]].copy()

            df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
            df["Tipo"] = df["Tipo"].astype(str).str.strip()
            df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0)

            df = df.dropna(subset=["Data"])

            df["EhTransferencia"] = df["Tipo"].str.contains(
                TRANSFERENCIA_TEXTO,
                case=False,
                na=False
            )

            # Regra contábil:
            # Ganhos entram positivos.
            # Transferências diminuem o Total Wallet.
            # Se a transferência já estiver negativa no Excel, mantém o efeito de redução.
            # Se vier positiva por algum motivo, força como saída negativa.
            df["ValorWallet"] = df.apply(self.calcular_valor_wallet, axis=1)

            df["Movimento"] = df["EhTransferencia"].apply(
                lambda x: "Saída" if x else "Entrada"
            )

            self.df = df.sort_values(by=["Data", "Hora"])

            self.calcular_resumos()
            self.atualizar_tela()

        except Exception as erro:
            messagebox.showerror("Erro ao carregar dados", str(erro))

    def calcular_valor_wallet(self, row):
        valor = float(row["Valor"])

        if row["EhTransferencia"]:
            return -abs(valor)

        return valor

    def calcular_resumos(self):
        self.total_wallet = float(self.df["ValorWallet"].sum())

        df = self.df.copy()
        df["Dia"] = df["Data"].dt.date

        ganhos = (
            df[~df["EhTransferencia"]]
            .groupby("Dia")["ValorWallet"]
            .sum()
            .rename("Ganhos")
        )

        transferencias = (
            df[df["EhTransferencia"]]
            .groupby("Dia")["ValorWallet"]
            .sum()
            .rename("Transferencias")
        )

        resumo = pd.concat([ganhos, transferencias], axis=1).fillna(0)
        resumo["SaldoDia"] = resumo["Ganhos"] + resumo["Transferencias"]
        resumo = resumo.reset_index().sort_values(by="Dia")

        self.resumo_diario = resumo

        self.resumo_tipo = (
            df[~df["EhTransferencia"]]
            .groupby("Tipo")["Valor"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )

    def atualizar_tela(self):
        self.var_total_wallet.set(self.formatar_moeda(self.total_wallet))
        self.atualizar_tabela_diaria()
        self.atualizar_tabela_lancamentos()
        self.atualizar_grafico_tipo()

    def atualizar_tabela_diaria(self):
        for item in self.tree_diario.get_children():
            self.tree_diario.delete(item)

        for _, row in self.resumo_diario.iterrows():
            self.tree_diario.insert(
                "",
                "end",
                values=(
                    self.formatar_data(row["Dia"]),
                    self.formatar_moeda(row["Ganhos"]),
                    self.formatar_moeda(row["Transferencias"]),
                    self.formatar_moeda(row["SaldoDia"]),
                )
            )

    def atualizar_tabela_lancamentos(self):
        for item in self.tree_lancamentos.get_children():
            self.tree_lancamentos.delete(item)

        for _, row in self.df.iterrows():
            self.tree_lancamentos.insert(
                "",
                "end",
                values=(
                    row["Data"].strftime("%d/%m/%Y"),
                    row["Tipo"],
                    str(row["Hora"]),
                    self.formatar_moeda(row["ValorWallet"]),
                    row["Movimento"],
                )
            )

    def atualizar_grafico_tipo(self):
        for widget in self.frame_canvas_grafico.winfo_children():
            widget.destroy()

        if self.resumo_tipo.empty:
            ttk.Label(
                self.frame_canvas_grafico,
                text="Sem dados para gerar gráfico."
            ).pack(pady=20)
            return

        fig, ax = plt.subplots(figsize=(9, 5))

        ax.bar(
            self.resumo_tipo["Tipo"],
            self.resumo_tipo["Valor"]
        )

        ax.set_title("Total de Ganhos por Tipo")
        ax.set_xlabel("Tipo")
        ax.set_ylabel("Valor Total")
        ax.tick_params(axis="x", rotation=30)

        for index, value in enumerate(self.resumo_tipo["Valor"]):
            ax.text(index, value, self.formatar_moeda(value), ha="center", va="bottom", fontsize=8)

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.frame_canvas_grafico)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    @staticmethod
    def formatar_moeda(valor):
        try:
            valor = float(valor)
            texto = f"R$ {valor:,.2f}"
            texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
            return texto
        except Exception:
            return "R$ 0,00"

    @staticmethod
    def formatar_data(valor):
        if isinstance(valor, datetime):
            return valor.strftime("%d/%m/%Y")
        if isinstance(valor, date):
            return valor.strftime("%d/%m/%Y")
        return str(valor)


if __name__ == "__main__":
    root = tk.Tk()
    app = WalletApp(root)
    root.mainloop()
