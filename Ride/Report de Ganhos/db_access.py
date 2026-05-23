# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'


import mysql.connector
from mysql.connector import Error


DB_CONFIG = {
    "host": "HOST",
    "port": 3306,
    "user": "USER",
    "password": "PASSWORD",
    "database": "DATABASE",
}


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def create_table():
    sql = """
    CREATE TABLE IF NOT EXISTS tbUberEarnings (
        idUberEarning INT AUTO_INCREMENT PRIMARY KEY,

        ueData DATE NOT NULL,
        ueTipo VARCHAR(100) NOT NULL,
        ueHora TIME NOT NULL,
        ueValor DECIMAL(10,2) NOT NULL,

        ueSystemUser VARCHAR(100) NULL,
        ueSystemData DATE NULL,
        ueSystemHora TIME NULL,
        ueSystemActive BOOLEAN DEFAULT TRUE,

        UNIQUE KEY uk_uber_earning (
            ueData,
            ueTipo,
            ueHora,
            ueValor
        )
    );
    """

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(sql)
    conn.commit()
    cursor.close()
    conn.close()


def insert_earning(data, tipo, hora, valor, system_user="Wallet"):
    sql = """
    INSERT IGNORE INTO tbUberEarnings (
        ueData,
        ueTipo,
        ueHora,
        ueValor,
        ueSystemUser,
        ueSystemData,
        ueSystemHora,
        ueSystemActive
    ) VALUES (
        %s, %s, %s, %s, %s, CURDATE(), CURTIME(), TRUE
    );
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(sql, (data, tipo, hora, valor, system_user))
    conn.commit()

    linhas_inseridas = cursor.rowcount

    cursor.close()
    conn.close()

    return linhas_inseridas


def fetch_all_earnings():
    sql = """
    SELECT
        idUberEarning,
        ueData,
        ueTipo,
        ueHora,
        ueValor
    FROM tbUberEarnings
    WHERE ueSystemActive = TRUE
    ORDER BY ueData ASC, ueHora ASC;
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(sql)
    dados = cursor.fetchall()

    cursor.close()
    conn.close()

    return dados
