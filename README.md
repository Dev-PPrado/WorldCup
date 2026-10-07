# ⚽ Dashboard da Copa do Mundo FIFA (1930–2014)

Dashboard interativo construído com **Streamlit**, **pandas** e **Plotly** para explorar 84 anos de história da Copa do Mundo: 20 edições, 836 partidas e 2.379 gols.

O projeto cobre o ciclo completo de um produto de dados: ingestão de CSVs brutos, diagnóstico de qualidade, limpeza e modelagem com pandas, e entrega em um dashboard com KPIs, filtros e gráficos interativos.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-2.x-150458?logo=pandas&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-5.x-3F4F75?logo=plotly&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.40%2B-FF4B4B?logo=streamlit&logoColor=white)

---

## Sumário

- [Funcionalidades](#funcionalidades)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Como executar](#como-executar)
- [Dados](#dados)
- [Tratamento de dados](#tratamento-de-dados)
- [Decisões e regras de negócio](#decisões-e-regras-de-negócio)
- [Validação](#validação)
- [Limitações conhecidas](#limitações-conhecidas)
- [Próximos passos](#próximos-passos)

---

## Funcionalidades

### Filtros globais (barra lateral)
- **Intervalo de edições** (1930 a 2014)
- **Fases do torneio**: fase preliminar, primeira fase, fase de grupos, oitavas, quartas, semifinal, disputa de 3º lugar e final

Todos os KPIs, gráficos e tabelas reagem aos filtros.

### KPIs principais
| KPI | Descrição |
|---|---|
| Edições | Quantidade de Copas no período |
| Partidas | Jogos disputados |
| Gols | Total de gols marcados |
| Média de gols/jogo | Gols ÷ partidas |
| Público total | Soma do público nos estádios |
| Maior campeão | Seleção com mais títulos no período |

### Abas

**📊 Visão geral**
- Gols por edição
- Evolução da média de gols por partida
- Títulos por seleção
- Público médio por partida em cada edição
- Pódios das 10 seleções com mais aparições (campeão, vice, 3º lugar)
- Média de gols por fase do torneio
- Tabela das 10 maiores goleadas

**🏳️ Seleções**
- Ranking das 15 seleções com mais vitórias e com mais gols
- Análise individual da seleção escolhida: Copas disputadas, jogos, vitórias, gols, saldo e aproveitamento
- Distribuição de vitórias, empates e derrotas, e resultados por edição
- Tabela completa de todas as seleções com barra de aproveitamento

**👟 Jogadores**
- KPIs de gols registrados, gols de pênalti, cartões amarelos e expulsões
- Top 15 artilheiros
- Distribuição dos gols por faixa de minuto de jogo

**🗂️ Dados**
- Tabelas tratadas de edições e partidas
- Download em CSV das partidas filtradas

---

## Estrutura do projeto

```
WorldCup/
├── data/
│   ├── WorldCups.csv          # Resumo por edição (sede, pódio, gols, público)
│   ├── WorldCupMatches.csv    # Uma linha por partida
│   └── WorldCupPlayers.csv    # Escalações e eventos por jogador
├── dashboard.py               # Aplicação Streamlit (ETL + visualizações)
├── requirements.txt           # Dependências
└── README.md
```

O `dashboard.py` está organizado em camadas:

1. **Carga e limpeza** (`load_cups`, `load_matches`, `load_events`), com cache via `@st.cache_data`
2. **Transformação** (`team_view`): passa as partidas para o formato longo, com uma linha por seleção por jogo
3. **Apresentação**: filtros, KPIs e gráficos Plotly organizados em abas

---

## Como executar

**Pré-requisitos:** Python 3.10 ou superior.

```bash
# 1. Clonar o repositório
git clone https://github.com/<seu-usuario>/world-cup-dashboard.git
cd world-cup-dashboard

# 2. Criar e ativar o ambiente virtual
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# 3. Instalar as dependências
pip install -r requirements.txt

# 4. Executar o dashboard
streamlit run dashboard.py
```

O dashboard abre em **http://localhost:8501**.

---

## Dados

Base pública *FIFA World Cup* (Kaggle), com dados oficiais da FIFA de 1930 a 2014.

| Arquivo | Linhas (bruto) | Linhas (tratado) | Granularidade |
|---|---:|---:|---|
| `WorldCups.csv` | 20 | 20 | Edição |
| `WorldCupMatches.csv` | 4.572 | 836 | Partida |
| `WorldCupPlayers.csv` | 37.784 | 37.048 | Jogador × partida |

---

## Tratamento de dados

Problemas de qualidade encontrados na análise exploratória e como cada um foi tratado:

| Problema | Exemplo | Tratamento |
|---|---|---|
| Linhas totalmente vazias | ~3.700 linhas em `WorldCupMatches.csv` | `dropna(how="all")` |
| Partidas duplicadas | 16 jogos repetidos (2014 aparecia com 80 jogos em vez de 64) | `drop_duplicates(subset="MatchID")` |
| Registros de jogadores duplicados | 736 linhas | `drop_duplicates()` |
| Resíduo de HTML nos nomes | `rn">Republic of Ireland` | Remoção por regex |
| Erro de encoding | `C�te d'Ivoire` | Mapeado para `Côte d'Ivoire` |
| Mesma seleção com dois nomes | `IR Iran` e `Iran` | Unificado como `Iran` |
| Ponto como separador de milhar | `1.045.246` | Convertido para inteiro |
| Espaços sobrando | `"Montevideo "` | `str.strip()` |
| Data e hora em texto | `"13 Jul 1930 - 15:00 "` | `pd.to_datetime` com formato explícito |
| Nomes de fase heterogêneos | `Group A`, `Group 1`, `Third place`, `Play-off for third place` | Padronizados em 8 fases em português |
| Eventos codificados em texto | `"Y1' O86'"`, `"G40'"` | Extraídos com `str.extractall` para uma linha por evento (código + minuto) |

### Códigos de evento dos jogadores

| Código | Significado |
|---|---|
| `G` | Gol |
| `P` | Gol de pênalti |
| `MP` | Pênalti perdido |
| `Y` | Cartão amarelo |
| `R` | Cartão vermelho direto |
| `RSY` | Vermelho pelo segundo amarelo |
| `I` / `O` | Entrou / saiu (substituição) |
| `IH` / `OH` | Entrou / saiu no intervalo |

---

## Decisões e regras de negócio

- **Alemanha:** os registros de `Germany FR` (Alemanha Ocidental) contam como `Germany`, seguindo o critério da FIFA. A Alemanha Oriental (`German DR`) continua separada.
- **Vencedor da partida:** definido pelo placar. Em empate, a vitória nos pênaltis é extraída do campo `Win conditions`.
- **Estatísticas das seleções:** jogos decididos nos pênaltis contam como **empate**, como nas estatísticas oficiais.
- **Aproveitamento:** `(3 × vitórias + empates) ÷ (3 × jogos)`.
- **Artilharia:** soma gols normais (`G`) e de pênalti (`P`).

---

## Validação

Os números do dashboard foram conferidos com fontes independentes:

| Verificação | Resultado |
|---|---|
| Soma dos gols das partidas tratadas × `GoalsScored` em `WorldCups.csv` | 2.379 = 2.379 ✅ |
| Partidas por edição após remover duplicatas | 2014: 64 jogos ✅ |
| Brasil 1930–2014 (histórico oficial FIFA) | 20 Copas, 104 jogos, 70 vitórias, 221 gols ✅ |

---

## Limitações conhecidas

- **Nomes acentuados em `WorldCupPlayers.csv`:** chegaram com `?` no lugar da letra (ex.: `PEL?`, `M?LLER`). A informação se perdeu na origem e não pode ser recuperada pelo arquivo.
- **Gols por jogador:** somam 2.338, contra 2.379 nas partidas. A diferença vem principalmente de 41 eventos com código `W`, provavelmente gols contra (sem documentação que confirme), que ficam fora da artilharia.
- **Cobertura:** a base vai até 2014. As Copas de 2018 e 2022 não estão incluídas.

---

## Próximos passos

- [ ] Incluir as Copas de 2018 e 2022
- [ ] Separar o ETL em um módulo próprio e salvar os dados tratados em Parquet
- [ ] Adicionar testes automatizados das regras de limpeza
- [ ] Mapa coroplético de participações e títulos por país
- [ ] Publicar no Streamlit Community Cloud

---

## Autor

**Pedro Prado**: estudos em Engenharia de Dados.
