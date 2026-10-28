# PD Database Migrator v1.3.2

Aplicativo Python/Tkinter para copiar tabelas MySQL entre conexões independentes.

## Instalação

```CMD ou PowerShell
py -m pip install -r requirements.txt
py migrator.py
```

## Migração e limitações

- A origem é consultada em modo somente leitura; o destino recebe as alterações.
- O destino pode ser limpo **somente mediante confirmação explícita**; essa operação apaga tabelas e views no destino.
- As tabelas são copiadas em lotes, com validação de contagens e tentativas controladas de reconexão.
- Views, triggers, stored procedures, functions e eventos **não** são migrados.
- Uma tabela sem chave primária interrompe a migração por segurança.
- A contagem de registros não substitui auditoria de integridade e conteúdo.
- Faça backup e mantenha a origem sem gravações durante a cópia.

## Histórico

- **v1.3.2:** botão Limpar perfis, remoção do cofre local, limpeza dos campos e `.gitignore` para publicação.
- v1.3.1: correção de sintaxe `SHOW INDEX` e ordenação de chave primária composta em Python.
- v1.3: leitura paginada com cursores convencionais em lugar de `SSCursor`.
- v1.2: cofre criptografado em módulo separado.
