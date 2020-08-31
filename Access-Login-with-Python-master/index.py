# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'

# Importar as bibliotecas
from tkinter import *
from tkinter import messagebox
from tkinter import ttk #arrumar a fonte gráfica
from tkinter import PhotoImage
import DataBaser

# Criar nossa Janela
root = Tk()
root.title("Projetos Design - Login Page")
root.geometry("600x400")
root.configure(background="white")
root.resizable(width=False, height=False)
root.attributes("-alpha", 0.9)
root.iconbitmap(default="\icons\WebZoom.ico")


# ---- Widget ----
LeftFrame = Frame(root, width=180, height=400, bg= "MIDNIGHTBLUE", relief="raise")
LeftFrame.pack(side=LEFT)
 
RightFrame = Frame(root, width=418, height=400, bg= "MIDNIGHTBLUE", relief="raise")
RightFrame.pack(side=RIGHT)

# ---- Carregar Imagens ----
Logo = PhotoImage(file="\icons\penguin.png")
LogoLabel = Label(LeftFrame, image=Logo, bg= "MIDNIGHTBLUE")
LogoLabel.place(x=50, y=100)

def Login():
    User = UserEntry.get()
    Pass = PassEntry.get()

    DataBaser.cursor.execute("""
    SELECT * FROM Users
    WHERE (User = ? and Password = ?)
    """, (User, Pass))
    print("Access Granted!")

    VerifyLogin = DataBaser.cursor.fetchone()

    if VerifyLogin is not None:
            messagebox.showinfo(title="Login Info", message="Acess Granted! Welcome!")
    else:
        messagebox.showerror(title="Login Info", message="Access Denied! Please, Verify your register in System!")


# ---- Botoões ----
LoginButon = ttk.Button(RightFrame, text="Login", width=30, command=Login)
LoginButon.place(x=100, y=225)

def Register():
    #Remove Widgets de Login
    LoginButon.place(x=5000)
    RegisterButton.place(x=5000)

    #Inserindo Widgets de Cadatro
    NomeLabel = Label(RightFrame, text="Name", font=("Century Gotic", 18), bg= "MIDNIGHTBLUE", fg="White")
    NomeLabel.place(x=5, y=5)

    NomeEntry = ttk.Entry(RightFrame, width=30)
    NomeEntry.place(x=130, y=16)

    EmailLabel = Label(RightFrame, text="E-Mail", font=("Century Gotic", 18), bg= "MIDNIGHTBLUE", fg="White")
    EmailLabel.place(x=5, y=55)

    EmailEntry = ttk.Entry(RightFrame, width=30)
    EmailEntry.place(x=130, y=66)
    
    def RegisterToDataBase():
        Name = NomeEntry.get()
        Email = EmailEntry.get()
        User = UserEntry.get()
        Pass = PassEntry.get()
        if (Name == "" or Email == "" or User == "" or Pass == ""):
            messagebox.showerror(title="ERROR", message="Preencha todas os campos!")
        else:
            DataBaser.cursor.execute("""
            INSERT INTO Users(Name, Email, User, Password) VALUES (?, ?, ?, ?)
            """, (Name, Email, User, Pass))
            DataBaser.conn.commit()
            messagebox.showinfo(title="Register Info", message="Sucessful Account Created")

    Register = ttk.Button(RightFrame, text="Register", width=30, command=RegisterToDataBase)
    Register.place(x=100, y=225)
    
    def BackToLogin():
        #Romovendo Widgets de Cadastro
        NomeLabel.place(x=5000)
        NomeEntry.place(x=5000)
        EmailLabel.place(x=5000)
        EmailEntry.place(x=5000)
        Register.place(x=5000)
        Back.place(x=5000)
        # Retornando com os Widgets de Cadastro
        LoginButon.place(x=100)
        RegisterButton.place(x=125)

    Back = ttk.Button(RightFrame, text="Back", width=20, command=BackToLogin)
    Back.place(x=125, y=260)


RegisterButton = ttk.Button(RightFrame, text="Register", width=20, command=Register)
RegisterButton.place(x=125, y=260)

# Entrada de Dados Usuario
UserLabel = Label(RightFrame, text="Username: ", font=("Century Gotic", 18), bg= "MIDNIGHTBLUE", fg= "WHITE")
UserLabel.place(x=5, y=100)

UserEntry = ttk.Entry(RightFrame, width=30)
UserEntry.place(x=130, y=110)

# Entrada de Dados Password
PassLabel = Label(RightFrame, text="Password: ", font=("Century Gotic", 18), bg= "MIDNIGHTBLUE", fg= "WHITE")
PassLabel.place(x=5, y=150)

PassEntry = ttk.Entry(RightFrame, width=30, show="•")
PassEntry.place(x=130, y=160)


root.mainloop()
