"""Gera dados sintéticos de e-commerce, propositalmente "sujos".

Por que isso existe? Em projetos reais os dados chegam imperfeitos. Em vez de
usar um dataset limpo, injetamos problemas comuns (duplicatas, espaços,
caixa alta/baixa, nulos, quantidades inválidas) para que as camadas de
transformação e os testes tenham trabalho de verdade a fazer.
"""
from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
SEED = 42

STATES = ["SP", "RJ", "MG", "RS", "PR", "BA", "SC", "PE"]
CATEGORIES = {
    "Eletrônicos": (150, 3000),
    "Casa": (30, 600),
    "Moda": (40, 400),
    "Esporte": (50, 800),
    "Livros": (20, 120),
}
FIRST = ["Ana", "Bruno", "Carla", "Diego", "Eduarda", "Felipe", "Gabriela", "Hugo", "Isabela", "João"]
LAST = ["Silva", "Souza", "Oliveira", "Santos", "Lima", "Costa", "Pereira", "Almeida", "Ribeiro", "Gomes"]


def write_csv(name: str, header: list[str], rows: list[list]) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with open(RAW_DIR / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def generate(n_customers: int = 500, n_products: int = 40, n_orders: int = 3000) -> None:
    rnd = random.Random(SEED)  # semente fixa => dados reproduzíveis
    start = date(2025, 1, 1)

    # --- customers (sujeira: e-mail em caixa mista, estado vazio/minúsculo, duplicatas)
    customers = []
    for cid in range(1, n_customers + 1):
        name = f"{rnd.choice(FIRST)} {rnd.choice(LAST)}"
        email = f"{name.lower().replace(' ', '.')}{cid}@exemplo.com"
        if rnd.random() < 0.15:
            email = email.upper()
        state = rnd.choice(STATES)
        if rnd.random() < 0.08:
            state = ""
        elif rnd.random() < 0.10:
            state = state.lower()
        created = start + timedelta(days=rnd.randint(0, 300))
        customers.append([cid, f" {name} ", email, state, created.isoformat()])
    customers += rnd.sample(customers, 15)  # linhas duplicadas
    write_csv("customers", ["customer_id", "name", "email", "state", "created_at"], customers)

    # --- products
    products = []
    for pid in range(1, n_products + 1):
        cat = rnd.choice(list(CATEGORIES))
        lo, hi = CATEGORIES[cat]
        products.append([pid, f"Produto {pid:03d}", cat, round(rnd.uniform(lo, hi), 2)])
    write_csv("products", ["product_id", "name", "category", "price"], products)
    price = {p[0]: p[3] for p in products}

    # --- orders e order_items
    statuses = (["delivered"] * 70 + ["shipped"] * 10 + ["canceled"] * 6
                + ["cancelled"] * 4 + ["Delivered "] * 5 + ["CANCELED"] * 5)
    orders, items = [], []
    for oid in range(1, n_orders + 1):
        cid = rnd.randint(1, n_customers)
        odate = start + timedelta(days=rnd.randint(30, 420))
        orders.append([oid, cid, odate.isoformat(), rnd.choice(statuses)])
        for _ in range(rnd.randint(1, 4)):
            pid = rnd.randint(1, n_products)
            qty = rnd.randint(1, 5)
            if rnd.random() < 0.01:
                qty = rnd.choice([0, -1])  # quantidade inválida
            items.append([oid, pid, qty, price[pid]])
    orders += rnd.sample(orders, 25)  # pedidos duplicados
    write_csv("orders", ["order_id", "customer_id", "order_date", "status"], orders)
    write_csv("order_items", ["order_id", "product_id", "quantity", "unit_price"], items)

    print(f"✔ Dados brutos gerados em {RAW_DIR}")


if __name__ == "__main__":
    generate()
