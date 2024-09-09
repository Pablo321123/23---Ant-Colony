import pandas as pd
import numpy as np
import random

t = lambda d: 1 / d
calc_evaporacao = lambda coef_evaporacao, n: (1 - coef_evaporacao) * n
fer_depositado = lambda Q, dt: Q / dt
n_ant = 0

best_ant = [0, 9999999999999]
best_path = pd.DataFrame()


def read_csv():
    global n_ant

    city_df = pd.read_csv("data/Colonia.csv", sep=";")
    n_ant = len(city_df)
    return city_df


def create_prob_table():
    city_df = read_csv()
    n_ant = len(city_df)

    for i, city in enumerate(city_df["Cidade"]):
        city_df[i + 1] = 0

    for i in range(len(city_df)):
        for j in range(1, len(city_df) + 1):

            city_df[j] = city_df[j].astype(
                float
            )  # Nescessary to fix incorrect column data type error!

            x_source = city_df.loc[i, "X"]
            x_dest = city_df.loc[j - 1, "X"]

            y_source = city_df.loc[i, "Y"]
            y_dest = city_df.loc[j - 1, "Y"]

            city_df.loc[i, j] = np.round(
                np.sqrt(np.pow(x_dest - x_source, 2) + np.pow(y_dest - y_source, 2)), 4
            )

            _n = [[0.1 for i in range(len(city_df))] for j in range(len(city_df))]

    df_probs = pd.DataFrame(
        columns=["Source", "Dest", "distance", "t", "n", "t_n", "sum_t_n", "prob", "%"]
    )

    for i in range(1, len(city_df) + 1):
        for j in range(1, len(city_df) + 1):
            if i == j:
                continue

            d = city_df.loc[i - 1, j]
            n = _n[i - 1][j - 1]

            new_route = pd.DataFrame(
                {
                    "Source": [i],
                    "Dest": [j],
                    "distance": [d],
                    "t": [t(d)],
                    "n": [n],
                    "t_n": [t(d) * n],
                    "sum_t_n": [0],
                    "prob": [0],
                    "%": [0],
                }
            )

            df_probs = pd.concat([df_probs, new_route])

    df_probs = df_probs.reset_index()  # Update dataFrame index after concat
    df_probs.drop("index", axis=1, inplace=True)  # drop old index column

    return df_probs


def calc_sum(df):
    result = df.groupby("Source")["t_n"].sum()
    df_new = pd.DataFrame()
    for i in range(1, len(result) + 1):
        df_sub = df[df["Source"] == i]
        df_sub["sum_t_n"] = result[i]
        df_new = pd.concat([df_new, df_sub])
    df = df_new

    df["prob"] = df["t_n"] / df["sum_t_n"]
    df["%"] = round(df["prob"] * 100, 1)
    return df


def choose_city(df):
    df_route = pd.DataFrame()
    df_choose = df.copy()
    df_choose["prob_cum"] = df_choose[
        "prob"
    ].cumsum()  # Acumular a soma das probabilidades para fazer a roleta de decisão
    # print(df_choose)
    p = random.uniform(0, 1)
    line = 0

    for l, value in enumerate(df_choose["prob_cum"]):
        if p < value:
            line = l
            break
    # print(f"linha selecionada: {line}\n")
    df_route = pd.concat([df_route, df_choose.iloc[line].to_frame().T])
    return df_route


def choose_route(df: pd.DataFrame, source, i):
    df_copy = df.copy()
    df_route = choose_city(df[df["Source"] == source])

    # Filtrando para retirar todos os destinos referentes a origem
    df_copy = df_copy[df_copy["Dest"] != source]
    # Filtrando para retirar todas as rotas da origem, uma vez que ja escolhemos qual seguir
    df_copy = df_copy[df_copy["Source"] != source]

    # print(df_copy)

    if i == n_ant - 1:
        return df_route
    else:
        new_source = df_route["Dest"].iloc[0]
        df_route = pd.concat([df_route, choose_route(df_copy, new_source, i + 1)])
        return df_route


def remove_duplicate_routes(df):
    # Crie colunas temporárias com os valores de Source e Dest sempre em ordem crescente
    df["Source_min"] = df[["Source", "Dest"]].min(axis=1)
    df["Dest_min"] = df[["Source", "Dest"]].max(axis=1)

    # Agora remova as duplicatas com base nas colunas temporárias
    df_unique = df.drop_duplicates(subset=["Source_min", "Dest_min"])

    # Remova as colunas temporárias, pois não são mais necessárias
    df_unique = df_unique.drop(columns=["Source_min", "Dest_min"])

    # Resultado final sem as rotas duplicadas "inversas"
    return df_unique


def atualizar_feromonio(dicRoutes):
    global best_path
    df_feromonio = pd.DataFrame()
    coef_evaporacao = 0.01
    Q = 10

    for key, value in dicRoutes.items():
        df_feromonio = pd.concat([df_feromonio, value])

    df_feromonio = df_feromonio[["Source", "Dest"]]
    df_feromonio.sort_values(by="Source", inplace=True)
    df_feromonio = df_feromonio.drop_duplicates(subset=["Source", "Dest"])

    df_feromonio = remove_duplicate_routes(df_feromonio)

    # # # key = ant
    for key, value in dicRoutes.items():
        dt = value["distance"].sum()
        
        if not best_ant or best_ant[1] > dt:            
            best_ant[0] = key
            best_ant[1] = dt
            best_path = value

        for i in range(len(value)):
            # df_feromonio[key] = fer_depositado(Q, dt)
            new_source = value["Source"].iloc[i]
            new_dest = value["Dest"].iloc[i]
            filter = (df_feromonio["Source"] == new_source) & (
                df_feromonio["Dest"] == new_dest
            )

            if df_feromonio[filter].empty:
                filter = (df_feromonio["Source"] == new_dest) & (
                    df_feromonio["Dest"] == new_source
                )

            df_feromonio.loc[filter, "Evaporado"] = calc_evaporacao(
                coef_evaporacao, value["n"].iloc[i]
            )
            df_feromonio.loc[filter, key] = fer_depositado(Q, dt)

    df_feromonio["Total"] = df_feromonio.iloc[:, 2:].sum(axis=1, skipna=True)

    df_feromonio.to_html("tabela_custo_rotas.html")

    return df_feromonio


def start(max_it):
    df_probs = create_prob_table()

    it = 0
    while it < max_it:
        df_probs = calc_sum(df_probs)

        dfChoosedRoutes = pd.DataFrame()
        source = 1
        dfChoosedRoutes = choose_route(df_probs, source, 1)
        last_dest = dfChoosedRoutes["Dest"].iloc[-1]

        # Adicionando a rota final que retorna a origem
        dfChoosedRoutes = pd.concat(
            [
                dfChoosedRoutes,
                df_probs[
                    (df_probs["Source"] == last_dest) & (df_probs["Dest"] == source)
                ],
            ]
        )

        dfChoosedRoutes = pd.DataFrame()
        dicRoutes = {}

        for i in range(1, n_ant + 1):
            source = i
            dfChoosedRoutes = choose_route(df_probs, source, 1)
            last_dest = dfChoosedRoutes["Dest"].iloc[-1]

            # Adicionando a rota final que retorna a origem
            dfChoosedRoutes = pd.concat(
                [
                    dfChoosedRoutes,
                    df_probs[
                        (df_probs["Source"] == last_dest) & (df_probs["Dest"] == source)
                    ],
                ]
            )
            dicRoutes[i] = dfChoosedRoutes

        df_feromonio = atualizar_feromonio(dicRoutes)

        for i in range(len(df_feromonio)):
            new_source = df_feromonio["Source"].iloc[i]
            new_dest = df_feromonio["Dest"].iloc[i]

            filter1 = (df_probs["Source"] == new_source) & (
                df_probs["Dest"] == new_dest
            )
            filter2 = (df_probs["Source"] == new_dest) & (
                df_probs["Dest"] == new_source
            )

            df_probs.loc[filter1, "n"] = df_feromonio["Total"].iloc[i]
            df_probs.loc[filter2, "n"] = df_feromonio["Total"].iloc[i]

            df_probs["t_n"] = df_probs["t"] * df_probs["n"]

        df_probs.to_html("prob_table_atualizada.html")
        it = it + 1
    print(best_ant)
    return best_path
    
