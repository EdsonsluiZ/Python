# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import re

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import db_access


TRANSFERENCIA_TEXTO = "Transferido para a conta bancária"


class WalletApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Wallet - Controle de Ganhos Uber")
        self.root.geometry("1200x750")

        self.df = pd.DataFrame()

        db_access.create_table()

        self.criar_menu()
        self.criar_interface()
        self.carregar_dados_db()

    def criar_menu(self):
        menu_bar = tk.Menu(self.root)

        menu_arquivo = tk.Menu(menu_bar, tearoff=0)
        menu_arquivo.add_command(
            label="Importar Relatório Uber",
            command=self.importar_relatorio_uber
        )
        menu_arquivo.add_command(
            label="Atualizar Dados do Banco",
            command=self.carregar_dados_db
        )
        menu_arquivo.add_separator()
        menu_arquivo.add_command(
            label="Sair",
            command=self.root.quit
        )

        menu_bar.add_cascade(label="Arquivo", menu=menu_arquivo)
        self.root.config(menu=menu_bar)

    def criar_interface(self):
        frame_topo = ttk.Frame(self.root, padding=10)
        frame_topo.pack(fill="x")

        ttk.Label(
            frame_topo,
            text="Wallet - Dashboard Financeiro",
            font=("Arial", 18, "bold")
        ).pack(side="left")

        self.var_total_wallet = tk.StringVar(value="R$ 0,00")

        frame_total = ttk.LabelFrame(self.root, text="Total Wallet", padding=15)
        frame_total.pack(fill="x", padx=10, pady=5)

        ttk.Label(
            frame_total,
            textvariable=self.var_total_wallet,
            font=("Arial", 24, "bold")
        ).pack(anchor="w")

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.frame_diario = ttk.Frame(self.notebook, padding=10)
        self.frame_tipo = ttk.Frame(self.notebook, padding=10)
        self.frame_mensal = ttk.Frame(self.notebook, padding=10)
        self.frame_lancamentos = ttk.Frame(self.notebook, padding=10)

        self.notebook.add(self.frame_diario, text="Fechamento Diário")
        self.notebook.add(self.frame_tipo, text="Gráfico por Tipo")
        self.notebook.add(self.frame_mensal, text="Performance Mensal")
        self.notebook.add(self.frame_lancamentos, text="Lançamentos")

        self.criar_tabela_diaria()
        self.criar_area_grafico_tipo()
        self.criar_area_performance_mensal()
        self.criar_tabela_lancamentos()

    def criar_tabela_diaria(self):
        colunas = ("data", "ganhos", "transferencias", "saldo")

        self.tree_diario = ttk.Treeview(
            self.frame_diario,
            columns=colunas,
            show="headings"
        )

        self.tree_diario.heading("data", text="Data")
        self.tree_diario.heading("ganhos", text="Ganhos")
        self.tree_diario.heading("transferencias", text="Transferências")
        self.tree_diario.heading("saldo", text="Saldo do Dia")

        self.tree_diario.pack(fill="both", expand=True)

    def criar_area_grafico_tipo(self):
        self.frame_grafico_tipo = ttk.Frame(self.frame_tipo)
        self.frame_grafico_tipo.pack(fill="both", expand=True)

    def criar_area_performance_mensal(self):
        self.canvas_mensal = tk.Canvas(self.frame_mensal)

        self.scrollbar_mensal = ttk.Scrollbar(
            self.frame_mensal,
            orient="vertical",
            command=self.canvas_mensal.yview
        )

        self.frame_performance_mensal = ttk.Frame(self.canvas_mensal)

        self.frame_performance_mensal.bind(
            "<Configure>",
            lambda event: self.canvas_mensal.configure(
                scrollregion=self.canvas_mensal.bbox("all")
            )
        )

        self.canvas_mensal.create_window(
            (0, 0),
            window=self.frame_performance_mensal,
            anchor="nw"
        )

        self.canvas_mensal.configure(yscrollcommand=self.scrollbar_mensal.set)

        self.canvas_mensal.pack(side="left", fill="both", expand=True)
        self.scrollbar_mensal.pack(side="right", fill="y")


    def criar_tabela_lancamentos(self):
        colunas = ("data", "tipo", "hora", "valor")

        self.tree_lancamentos = ttk.Treeview(
            self.frame_lancamentos,
            columns=colunas,
            show="headings"
        )

        self.tree_lancamentos.heading("data", text="Data")
        self.tree_lancamentos.heading("tipo", text="Tipo")
        self.tree_lancamentos.heading("hora", text="Hora")
        self.tree_lancamentos.heading("valor", text="Valor")

        self.tree_lancamentos.column("tipo", width=280)

        self.tree_lancamentos.pack(fill="both", expand=True)

    def importar_relatorio_uber(self):
        arquivo = filedialog.askopenfilename(
            title="Selecione o relatório da Uber",
            filetypes=[("Arquivos Excel", "*.xlsx")]
        )

        if not arquivo:
            return

        try:
            registros = self.processar_excel_uber(arquivo)

            inseridos = 0

            for item in registros:
                inseridos += db_access.insert_earning(
                    item["data"],
                    item["tipo"],
                    item["hora"],
                    item["valor"]
                )

            messagebox.showinfo(
                "Importação concluída",
                f"Registros lidos: {len(registros)}\n"
                f"Novos registros inseridos: {inseridos}"
            )

            self.carregar_dados_db()

        except Exception as erro:
            messagebox.showerror("Erro na importação", str(erro))

    def processar_excel_uber(self, arquivo):
        xls = pd.ExcelFile(arquivo)

        if "Ganhos" in xls.sheet_names:
            df_raw = pd.read_excel(arquivo, sheet_name="Ganhos", header=None)
        else:
            df_raw = pd.read_excel(arquivo, sheet_name=2, header=None)

        valores = []

        for _, row in df_raw.iterrows():
            for valor in row:
                if pd.notna(valor) and str(valor).strip():
                    valores.append(str(valor).strip())

        meses = {
            "jan": 1, "jan.": 1, "janeiro": 1,
            "fev": 2, "fev.": 2, "fevereiro": 2,
            "mar": 3, "mar.": 3, "março": 3, "marco": 3,
            "abr": 4, "abr.": 4, "abril": 4,
            "mai": 5, "mai.": 5, "maio": 5,
            "jun": 6, "jun.": 6, "junho": 6,
            "jul": 7, "jul.": 7, "julho": 7,
            "ago": 8, "ago.": 8, "agosto": 8,
            "set": 9, "set.": 9, "setembro": 9,
            "out": 10, "out.": 10, "outubro": 10,
            "nov": 11, "nov.": 11, "novembro": 11,
            "dez": 12, "dez.": 12, "dezembro": 12,
        }

        ano_padrao = 2026

        padrao_data = re.compile(
            r"^(\d{1,2})\s+de\s+([a-zçã.]+)$",
            re.IGNORECASE
        )
        padrao_hora = re.compile(r"^\d{1,2}:\d{2}:\d{2}$")
        padrao_valor = re.compile(r"^-?\d+(?:\.\d+)?$")

        data_atual = None
        tipo_atual = None
        hora_atual = None

        registros = []

        for texto in valores:
            texto = texto.strip()

            m_data = padrao_data.match(texto.lower())

            if m_data:
                dia = int(m_data.group(1))
                mes_txt = m_data.group(2).lower()

                if mes_txt in meses:
                    data_atual = datetime(
                        ano_padrao,
                        meses[mes_txt],
                        dia
                    ).date()

                tipo_atual = None
                hora_atual = None
                continue

            if (
                data_atual is not None
                and not padrao_hora.match(texto)
                and not padrao_valor.match(texto)
            ):
                tipo_atual = texto
                hora_atual = None
                continue

            if (
                data_atual is not None
                and tipo_atual is not None
                and padrao_hora.match(texto)
            ):
                hora_atual = texto
                continue

            if (
                data_atual is not None
                and tipo_atual is not None
                and hora_atual is not None
                and padrao_valor.match(texto)
            ):
                registros.append({
                    "data": data_atual,
                    "tipo": tipo_atual,
                    "hora": hora_atual,
                    "valor": float(texto)
                })

                tipo_atual = None
                hora_atual = None

        registros.sort(key=lambda x: (x["data"], x["hora"]))

        return registros

    def carregar_dados_db(self):
        try:
            dados = db_access.fetch_all_earnings()

            self.df = pd.DataFrame(dados)

            if self.df.empty:
                self.var_total_wallet.set("R$ 0,00")
                return

            self.df.rename(columns={
                "ueData": "Data",
                "ueTipo": "Tipo",
                "ueHora": "Hora",
                "ueValor": "Valor"
            }, inplace=True)

            self.df["Data"] = pd.to_datetime(self.df["Data"])
            self.df["Valor"] = pd.to_numeric(self.df["Valor"])

            self.df["EhTransferencia"] = self.df["Tipo"].str.contains(
                TRANSFERENCIA_TEXTO,
                case=False,
                na=False
            )

            self.df["ValorWallet"] = self.df.apply(
                lambda row: -abs(row["Valor"]) if row["EhTransferencia"] else row["Valor"],
                axis=1
            )

            self.atualizar_dashboard()

        except Exception as erro:
            messagebox.showerror("Erro ao carregar dados do banco", str(erro))

    def atualizar_dashboard(self):
        total_wallet = self.df["ValorWallet"].sum()
        self.var_total_wallet.set(self.formatar_moeda(total_wallet))

        self.atualizar_fechamento_diario()
        self.atualizar_lancamentos()
        self.atualizar_grafico_tipo()
        self.atualizar_performance_mensal()

    def atualizar_performance_mensal(self):
        for widget in self.frame_performance_mensal.winfo_children():
            widget.destroy()

        df_ganhos = self.df[~self.df["EhTransferencia"]].copy()

        if df_ganhos.empty:
            ttk.Label(
                self.frame_performance_mensal,
                text="Sem dados para gerar a performance mensal."
            ).pack(pady=20)
            return

        df_ganhos["MesAno"] = df_ganhos["Data"].dt.to_period("M")
        df_ganhos["MesLabel"] = df_ganhos["Data"].dt.strftime("%m/%Y")

        resumo = (
            df_ganhos
            .groupby(["MesAno", "MesLabel", "Tipo"])["Valor"]
            .sum()
            .reset_index()
            .sort_values(by=["MesAno", "Valor"], ascending=[True, True])
        )

        meses = list(resumo["MesAno"].drop_duplicates())

        for mes in meses:
            dados_mes = resumo[resumo["MesAno"] == mes].copy()
            dados_mes = dados_mes[dados_mes["Valor"] > 0]

            if dados_mes.empty:
                continue

            dados_mes = dados_mes.sort_values(by="Valor", ascending=True)

            mes_label = dados_mes["MesLabel"].iloc[0]
            total_mes = dados_mes["Valor"].sum()

            frame_mes = ttk.LabelFrame(
                self.frame_performance_mensal,
                text=f"{mes_label} - Total {self.formatar_moeda(total_mes)}",
                padding=10
            )
            frame_mes.pack(fill="x", expand=True, padx=10, pady=10)

            fig, ax = plt.subplots(figsize=(9, 4))

            barras = ax.barh(
                dados_mes["Tipo"],
                dados_mes["Valor"]
            )

            ax.set_title(f"Performance por Tipo - {mes_label}")
            ax.set_xlabel("Valor Total")
            ax.set_ylabel("Tipo")

            limite_x = dados_mes["Valor"].max() * 1.20
            ax.set_xlim(0, limite_x)

            for barra in barras:
                largura = barra.get_width()
                y = barra.get_y() + barra.get_height() / 2

                ax.text(
                    largura,
                    y,
                    f"  {self.formatar_moeda(largura)}",
                    va="center",
                    fontsize=9
                )

            ax.grid(axis="x", linestyle="--", alpha=0.35)

            fig.tight_layout()

            canvas = FigureCanvasTkAgg(fig, master=frame_mes)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)

    def atualizar_fechamento_diario(self):
        for item in self.tree_diario.get_children():
            self.tree_diario.delete(item)

        df = self.df.copy()
        df["Dia"] = df["Data"].dt.date

        ganhos = (
            df[~df["EhTransferencia"]]
            .groupby("Dia")["ValorWallet"]
            .sum()
        )

        transferencias = (
            df[df["EhTransferencia"]]
            .groupby("Dia")["ValorWallet"]
            .sum()
        )

        resumo = pd.concat([ganhos, transferencias], axis=1).fillna(0)
        resumo.columns = ["Ganhos", "Transferencias"]
        resumo["Saldo"] = resumo["Ganhos"] + resumo["Transferencias"]
        resumo = resumo.reset_index().sort_values("Dia")

        for _, row in resumo.iterrows():
            self.tree_diario.insert(
                "",
                "end",
                values=(
                    row["Dia"].strftime("%d/%m/%Y"),
                    self.formatar_moeda(row["Ganhos"]),
                    self.formatar_moeda(row["Transferencias"]),
                    self.formatar_moeda(row["Saldo"]),
                )
            )

    def atualizar_lancamentos(self):
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
                    self.formatar_moeda(row["ValorWallet"])
                )
            )

    def atualizar_grafico_tipo(self):
        for widget in self.frame_grafico_tipo.winfo_children():
            widget.destroy()

        df_ganhos = self.df[~self.df["EhTransferencia"]].copy()

        if df_ganhos.empty:
            return

        resumo = (
            df_ganhos
            .groupby("Tipo")["Valor"]
            .sum()
            .sort_values(ascending=True)
        )

        fig, ax = plt.subplots(figsize=(9, 5))

        barras = ax.barh(resumo.index, resumo.values)

        ax.set_title("Performance por Tipo")
        ax.set_xlabel("Valor Total")

        for barra in barras:
            largura = barra.get_width()
            ax.text(
                largura,
                barra.get_y() + barra.get_height() / 2,
                f" {self.formatar_moeda(largura)}",
                va="center"
            )

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.frame_grafico_tipo)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    @staticmethod
    def formatar_moeda(valor):
        texto = f"R$ {float(valor):,.2f}"
        return texto.replace(",", "X").replace(".", ",").replace("X", ".")


if __name__ == "__main__":
    root = tk.Tk()
    app = WalletApp(root)
    root.mainloop()