"""Dashboard interativo da Copa do Mundo FIFA (1930-2014).

Executar com:  streamlit run dashboard.py
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"

# Paleta (categórica em ordem fixa + polos divergentes com cinza neutro no meio)
BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
RED = "#e34948"
GRAY = "#a3a29c"
RESULT_COLORS = {"Vitória": BLUE, "Empate": GRAY, "Derrota": RED}

# Correções de nomes de seleções: sujeira de HTML/encoding e nomes históricos
TEAM_FIXES = {
    "C�te d'Ivoire": "Côte d'Ivoire",
    "IR Iran": "Iran",
    # A FIFA considera o histórico da Alemanha Ocidental como da Alemanha
    "Germany FR": "Germany",
}

STAGE_MAP = {
    "Final": "Final",
    "Semi-finals": "Semifinal",
    "Quarter-finals": "Quartas de final",
    "Round of 16": "Oitavas de final",
    "Match for third place": "Disputa de 3º lugar",
    "Third place": "Disputa de 3º lugar",
    "Play-off for third place": "Disputa de 3º lugar",
    "Preliminary round": "Fase preliminar",
    "First round": "Primeira fase",
}
STAGE_ORDER = [
    "Fase preliminar", "Primeira fase", "Fase de grupos", "Oitavas de final",
    "Quartas de final", "Semifinal", "Disputa de 3º lugar", "Final",
]

EVENT_PATTERN = r"(?P<code>[A-Z]+)(?P<minute>\d+)'"


def clean_team(name: pd.Series) -> pd.Series:
    name = name.str.strip().str.replace(r'^rn">', "", regex=True)
    return name.replace(TEAM_FIXES)


@st.cache_data
def load_cups() -> pd.DataFrame:
    cups = pd.read_csv(DATA_DIR / "WorldCups.csv")
    # Público vem com ponto como separador de milhar: "1.045.246"
    cups["Attendance"] = cups["Attendance"].str.replace(".", "", regex=False).astype(int)
    for col in ["Winner", "Runners-Up", "Third", "Fourth"]:
        cups[col] = clean_team(cups[col])
    cups["AvgGoals"] = cups["GoalsScored"] / cups["MatchesPlayed"]
    cups["AvgAttendance"] = cups["Attendance"] / cups["MatchesPlayed"]
    return cups


@st.cache_data
def load_matches() -> pd.DataFrame:
    matches = pd.read_csv(DATA_DIR / "WorldCupMatches.csv")
    matches = matches.dropna(how="all").drop_duplicates(subset="MatchID")

    matches["Year"] = matches["Year"].astype(int)
    matches["Datetime"] = pd.to_datetime(
        matches["Datetime"].str.strip(), format="%d %b %Y - %H:%M", errors="coerce"
    )
    for col in ["Stadium", "City", "Win conditions", "Referee"]:
        matches[col] = matches[col].str.strip()
    matches["Home Team Name"] = clean_team(matches["Home Team Name"])
    matches["Away Team Name"] = clean_team(matches["Away Team Name"])
    for col in ["Home Team Goals", "Away Team Goals", "Half-time Home Goals", "Half-time Away Goals"]:
        matches[col] = matches[col].astype(int)

    matches["Stage"] = matches["Stage"].str.strip()
    matches["Phase"] = matches["Stage"].map(STAGE_MAP).fillna(
        matches["Stage"].where(~matches["Stage"].str.startswith("Group"), "Fase de grupos")
    )

    matches["TotalGoals"] = matches["Home Team Goals"] + matches["Away Team Goals"]
    matches["Match"] = (
        matches["Home Team Name"] + " " + matches["Home Team Goals"].astype(str)
        + " x " + matches["Away Team Goals"].astype(str) + " " + matches["Away Team Name"]
    )

    # Vencedor: placar; em empate decidido nos pênaltis, "(casa - fora)" no texto
    pens = matches["Win conditions"].str.extract(r"penalties \((\d+) - (\d+)\)").astype(float)
    home_diff = (matches["Home Team Goals"] - matches["Away Team Goals"]).astype(float)
    home_diff = home_diff.where(home_diff != 0, pens[0] - pens[1]).fillna(0)
    matches["Winner"] = None
    matches.loc[home_diff > 0, "Winner"] = matches["Home Team Name"]
    matches.loc[home_diff < 0, "Winner"] = matches["Away Team Name"]
    matches["Penalties"] = pens[0].notna()
    return matches


@st.cache_data
def load_events() -> pd.DataFrame:
    """Uma linha por evento (gol, cartão, substituição) de cada jogador."""
    players = pd.read_csv(DATA_DIR / "WorldCupPlayers.csv").drop_duplicates()
    players["Player Name"] = players["Player Name"].str.strip()
    events = players.dropna(subset=["Event"])
    parsed = events["Event"].str.extractall(EVENT_PATTERN).reset_index(level=1, drop=True)
    events = events.drop(columns="Event").join(parsed)
    events["minute"] = events["minute"].astype(int)
    return events


def team_view(matches: pd.DataFrame) -> pd.DataFrame:
    """Reorganiza os jogos para uma linha por seleção por partida."""
    cols = ["MatchID", "Year", "Phase", "Winner", "Penalties"]
    home = matches[cols + ["Home Team Name", "Home Team Goals", "Away Team Goals", "Away Team Name"]]
    away = matches[cols + ["Away Team Name", "Away Team Goals", "Home Team Goals", "Home Team Name"]]
    names = cols + ["Team", "GoalsFor", "GoalsAgainst", "Opponent"]
    home.columns = names
    away.columns = names
    teams = pd.concat([home, away], ignore_index=True)
    teams["Result"] = "Empate"
    teams.loc[teams["Winner"] == teams["Team"], "Result"] = "Vitória"
    teams.loc[teams["Winner"] == teams["Opponent"], "Result"] = "Derrota"
    # Decisão por pênaltis conta como empate nas estatísticas oficiais
    teams.loc[teams["Penalties"], "Result"] = "Empate"
    return teams


def fmt_int(value: float) -> str:
    return f"{value:,.0f}".replace(",", ".")


def style(fig: go.Figure, height: int = 380) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=40, b=10),
        hoverlabel=dict(font_size=13),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title_text=""),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridwidth=0.5)
    return fig


def bar_rank(df: pd.DataFrame, x: str, y: str, title: str, hover: str, height: int = 420) -> go.Figure:
    fig = px.bar(df, x=x, y=y, orientation="h", title=title, text=x)
    fig.update_traces(
        marker_color=BLUE, hovertemplate=hover, textposition="outside", cliponaxis=False
    )
    fig.update_yaxes(categoryorder="total ascending", title=None)
    fig.update_xaxes(title=None, showticklabels=False)
    return style(fig, height)


# ---------------------------------------------------------------------------
st.set_page_config(page_title="Copa do Mundo FIFA", page_icon="⚽", layout="wide")

cups = load_cups()
matches = load_matches()
events = load_events()

# Filtros ---------------------------------------------------------------------
st.sidebar.header("Filtros")
years = sorted(cups["Year"])
year_min, year_max = st.sidebar.select_slider(
    "Edições", options=years, value=(years[0], years[-1])
)
phases = st.sidebar.multiselect(
    "Fases", options=[p for p in STAGE_ORDER if p in set(matches["Phase"])],
    placeholder="Todas as fases",
)

cups_f = cups[cups["Year"].between(year_min, year_max)]
matches_f = matches[matches["Year"].between(year_min, year_max)]
if phases:
    matches_f = matches_f[matches_f["Phase"].isin(phases)]
events_f = events[events["MatchID"].isin(matches_f["MatchID"])]
teams_f = team_view(matches_f)

st.sidebar.caption(
    "Fonte: FIFA World Cup (Kaggle), 1930-2014. Alemanha Ocidental (Germany FR) "
    "contabilizada como Germany."
)

# Cabeçalho e KPIs ------------------------------------------------------------
st.title("⚽ Copa do Mundo FIFA")
st.caption(f"Edições de {year_min} a {year_max}" + (f" · Fases: {', '.join(phases)}" if phases else ""))

if matches_f.empty:
    st.warning("Nenhuma partida para os filtros selecionados.")
    st.stop()

total_goals = matches_f["TotalGoals"].sum()
attendance = matches_f["Attendance"].sum()
top_champion = cups_f["Winner"].value_counts()

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Edições", cups_f["Year"].nunique())
k2.metric("Partidas", fmt_int(len(matches_f)))
k3.metric("Gols", fmt_int(total_goals))
k4.metric("Média de gols/jogo", f"{total_goals / len(matches_f):.2f}".replace(".", ","))
k5.metric("Público total", f"{attendance / 1e6:.1f} mi".replace(".", ","))
k6.metric(
    "Maior campeão",
    top_champion.index[0] if not top_champion.empty else "-",
    f"{top_champion.iloc[0]} títulos" if not top_champion.empty else None,
    delta_color="off",
)

tab_overview, tab_teams, tab_players, tab_data = st.tabs(
    ["Visão geral", "Seleções", "Jogadores", "Dados"]
)

# Visão geral -----------------------------------------------------------------
with tab_overview:
    per_year = (
        matches_f.groupby("Year")
        .agg(Gols=("TotalGoals", "sum"), Partidas=("MatchID", "count"), Publico=("Attendance", "sum"))
        .reset_index()
    )
    per_year["Media"] = per_year["Gols"] / per_year["Partidas"]
    per_year["PublicoMedio"] = per_year["Publico"] / per_year["Partidas"]
    per_year = per_year.merge(cups[["Year", "Country", "Winner"]], on="Year")
    per_year["Edicao"] = per_year["Year"].astype(str)

    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(per_year, x="Edicao", y="Gols", title="Gols por edição",
                     custom_data=["Country", "Partidas"])
        fig.update_traces(
            marker_color=BLUE,
            hovertemplate="<b>%{x}</b> · %{customdata[0]}<br>%{y} gols em %{customdata[1]} jogos<extra></extra>",
        )
        fig.update_xaxes(title=None, type="category")
        fig.update_yaxes(title=None)
        st.plotly_chart(style(fig), width="stretch")
    with c2:
        fig = px.line(per_year, x="Year", y="Media", title="Média de gols por partida", markers=True,
                      custom_data=["Country"])
        fig.update_traces(
            line=dict(color=BLUE, width=2), marker=dict(size=8),
            hovertemplate="<b>%{x}</b> · %{customdata[0]}<br>%{y:.2f} gols/jogo<extra></extra>",
        )
        fig.update_xaxes(title=None)
        fig.update_yaxes(title=None, rangemode="tozero")
        fig.update_layout(hovermode="x")
        st.plotly_chart(style(fig), width="stretch")

    c3, c4 = st.columns(2)
    with c3:
        titles = cups_f["Winner"].value_counts().rename_axis("Seleção").reset_index(name="Títulos")
        fig = bar_rank(titles, "Títulos", "Seleção", "Títulos por seleção",
                       "<b>%{y}</b><br>%{x} título(s)<extra></extra>")
        st.plotly_chart(fig, width="stretch")
    with c4:
        fig = px.bar(per_year, x="Edicao", y="PublicoMedio", title="Público médio por partida",
                     custom_data=["Country", "Publico"])
        fig.update_traces(
            marker_color=BLUE,
            hovertemplate="<b>%{x}</b> · %{customdata[0]}<br>Média: %{y:,.0f}"
                          "<br>Total: %{customdata[1]:,.0f}<extra></extra>",
        )
        fig.update_xaxes(title=None, type="category")
        fig.update_yaxes(title=None)
        st.plotly_chart(style(fig, 420), width="stretch")

    c5, c6 = st.columns(2)
    with c5:
        podium = cups_f.melt(
            id_vars="Year", value_vars=["Winner", "Runners-Up", "Third"],
            var_name="Posição", value_name="Seleção",
        )
        podium["Posição"] = podium["Posição"].map(
            {"Winner": "Campeão", "Runners-Up": "Vice", "Third": "3º lugar"}
        )
        top = podium["Seleção"].value_counts().head(10).index
        podium = podium[podium["Seleção"].isin(top)]
        fig = px.histogram(
            podium, y="Seleção", color="Posição", orientation="h",
            title="Pódios (top 10 seleções)",
            category_orders={"Posição": ["Campeão", "Vice", "3º lugar"], "Seleção": list(top)},
            color_discrete_map={"Campeão": BLUE, "Vice": ORANGE, "3º lugar": AQUA},
        )
        fig.update_traces(marker_line_width=0,
                          hovertemplate="<b>%{y}</b><br>%{x}<extra>%{fullData.name}</extra>")
        fig.update_layout(bargap=0.3)
        fig.update_xaxes(title=None, dtick=1)
        fig.update_yaxes(title=None)
        st.plotly_chart(style(fig, 420), width="stretch")
    with c6:
        by_phase = (
            matches_f.groupby("Phase")
            .agg(Partidas=("MatchID", "count"), Gols=("TotalGoals", "sum"))
            .reindex(STAGE_ORDER).dropna().reset_index()
        )
        by_phase["Media"] = by_phase["Gols"] / by_phase["Partidas"]
        fig = px.bar(by_phase, x="Media", y="Phase", orientation="h",
                     title="Média de gols por fase", custom_data=["Partidas"],
                     text=by_phase["Media"].map(lambda v: f"{v:.2f}"))
        fig.update_traces(
            marker_color=BLUE, textposition="outside", cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>%{x:.2f} gols/jogo em %{customdata[0]} jogos<extra></extra>",
        )
        fig.update_yaxes(title=None, autorange="reversed")
        fig.update_xaxes(title=None, showticklabels=False)
        st.plotly_chart(style(fig, 420), width="stretch")

    st.subheader("Maiores goleadas")
    blowouts = matches_f.assign(
        Diferenca=(matches_f["Home Team Goals"] - matches_f["Away Team Goals"]).abs()
    ).sort_values(["Diferenca", "TotalGoals"], ascending=False).head(10)
    st.dataframe(
        blowouts[["Year", "Phase", "Match", "City", "Diferenca"]].rename(columns={
            "Year": "Ano", "Phase": "Fase", "Match": "Partida", "City": "Cidade",
            "Diferenca": "Saldo",
        }),
        hide_index=True, width="stretch",
    )

# Seleções --------------------------------------------------------------------
with tab_teams:
    table = (
        teams_f.groupby("Team")
        .agg(
            Jogos=("MatchID", "count"),
            Vitórias=("Result", lambda r: (r == "Vitória").sum()),
            Empates=("Result", lambda r: (r == "Empate").sum()),
            Derrotas=("Result", lambda r: (r == "Derrota").sum()),
            GolsPro=("GoalsFor", "sum"),
            GolsContra=("GoalsAgainst", "sum"),
            Copas=("Year", "nunique"),
        )
        .assign(Saldo=lambda d: d["GolsPro"] - d["GolsContra"],
                Aproveitamento=lambda d: (3 * d["Vitórias"] + d["Empates"]) / (3 * d["Jogos"]))
        .sort_values(["Vitórias", "Saldo"], ascending=False)
    )

    c1, c2 = st.columns(2)
    with c1:
        top_wins = table.head(15).reset_index()
        fig = bar_rank(top_wins, "Vitórias", "Team", "Seleções com mais vitórias",
                       "<b>%{y}</b><br>%{x} vitórias<extra></extra>", height=480)
        st.plotly_chart(fig, width="stretch")
    with c2:
        top_goals = table.sort_values("GolsPro", ascending=False).head(15).reset_index()
        fig = bar_rank(top_goals, "GolsPro", "Team", "Seleções com mais gols marcados",
                       "<b>%{y}</b><br>%{x} gols<extra></extra>", height=480)
        st.plotly_chart(fig, width="stretch")

    st.divider()
    team_list = table.index.tolist()
    default = team_list.index("Brazil") if "Brazil" in team_list else 0
    team = st.selectbox("Analisar seleção", team_list, index=default)
    row = table.loc[team]

    t1, t2, t3, t4, t5, t6 = st.columns(6)
    t1.metric("Copas disputadas", int(row["Copas"]))
    t2.metric("Jogos", int(row["Jogos"]))
    t3.metric("Vitórias", int(row["Vitórias"]))
    t4.metric("Gols marcados", int(row["GolsPro"]))
    t5.metric("Saldo de gols", f"{int(row['Saldo']):+d}")
    t6.metric("Aproveitamento", f"{row['Aproveitamento']:.0%}")

    team_matches = teams_f[teams_f["Team"] == team]
    c3, c4 = st.columns([1, 2])
    with c3:
        results = team_matches["Result"].value_counts().reindex(RESULT_COLORS).fillna(0).reset_index()
        fig = px.pie(results, names="Result", values="count", hole=0.6, title="Resultados",
                     color="Result", color_discrete_map=RESULT_COLORS)
        fig.update_traces(
            sort=False, textinfo="label+value", marker_line=dict(width=2, color="white"),
            hovertemplate="<b>%{label}</b><br>%{value} jogos (%{percent})<extra></extra>",
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(style(fig), width="stretch")
    with c4:
        team_years = (
            team_matches.groupby(["Year", "Result"]).size().reset_index(name="Jogos")
        )
        team_years["Edicao"] = team_years["Year"].astype(str)
        fig = px.bar(team_years, x="Edicao", y="Jogos", color="Result",
                     title="Resultados por edição",
                     category_orders={"Result": list(RESULT_COLORS)},
                     color_discrete_map=RESULT_COLORS)
        fig.update_traces(marker_line=dict(width=1, color="white"),
                          hovertemplate="<b>%{x}</b><br>%{y} jogo(s)<extra>%{fullData.name}</extra>")
        fig.update_xaxes(title=None, type="category")
        fig.update_yaxes(title=None, dtick=1)
        st.plotly_chart(style(fig), width="stretch")

    st.dataframe(
        table.reset_index().rename(columns={"Team": "Seleção", "GolsPro": "Gols pró",
                                            "GolsContra": "Gols contra"}),
        hide_index=True, width="stretch",
        column_config={"Aproveitamento": st.column_config.ProgressColumn(
            "Aproveitamento", format="percent", min_value=0, max_value=1)},
    )

# Jogadores -------------------------------------------------------------------
with tab_players:
    goals = events_f[events_f["code"].isin(["G", "P"])]
    cards = events_f[events_f["code"].isin(["Y", "R", "RSY"])]

    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Gols registrados", fmt_int(len(goals)))
    p2.metric("Gols de pênalti", fmt_int((goals["code"] == "P").sum()))
    p3.metric("Cartões amarelos", fmt_int((cards["code"] == "Y").sum()))
    p4.metric("Expulsões", fmt_int(cards["code"].isin(["R", "RSY"]).sum()))

    c1, c2 = st.columns(2)
    with c1:
        scorers = (
            goals.groupby(["Player Name", "Team Initials"]).size()
            .reset_index(name="Gols").sort_values("Gols", ascending=False).head(15)
        )
        scorers["Jogador"] = scorers["Player Name"] + " (" + scorers["Team Initials"] + ")"
        fig = bar_rank(scorers, "Gols", "Jogador", "Artilheiros",
                       "<b>%{y}</b><br>%{x} gols<extra></extra>", height=520)
        st.plotly_chart(fig, width="stretch")
    with c2:
        bins = list(range(0, 121, 15))
        labels = [f"{a + 1}-{b}'" for a, b in zip(bins[:-1], bins[1:])]
        minutes = pd.cut(goals["minute"], bins=[0] + bins[1:-1] + [200], labels=labels, include_lowest=True)
        by_minute = minutes.value_counts().reindex(labels).reset_index()
        by_minute.columns = ["Intervalo", "Gols"]
        fig = px.bar(by_minute, x="Intervalo", y="Gols", title="Gols por minuto de jogo")
        fig.update_traces(marker_color=BLUE, hovertemplate="<b>%{x}</b><br>%{y} gols<extra></extra>")
        fig.update_xaxes(title=None)
        fig.update_yaxes(title=None)
        st.plotly_chart(style(fig, 520), width="stretch")
    st.caption("Gols por jogador consideram gols normais e de pênalti; acréscimos contam no último intervalo do tempo.")

# Dados -----------------------------------------------------------------------
with tab_data:
    st.subheader("Edições")
    st.dataframe(cups_f, hide_index=True, width="stretch")
    st.subheader("Partidas")
    st.dataframe(
        matches_f[["Year", "Datetime", "Phase", "Stadium", "City", "Match", "Win conditions", "Attendance", "Referee"]],
        hide_index=True, width="stretch",
    )
    st.download_button(
        "Baixar partidas filtradas (CSV)",
        matches_f.to_csv(index=False).encode("utf-8"),
        file_name="partidas_copa.csv", mime="text/csv",
    )
