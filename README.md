# 🤖 EA FC 26 Draft AI Bot

Este repositório contém a implementação de um agente de Inteligência Artificial desenhado para jogar o modo Draft do **EA Sports FC 26**. O bot utiliza um algoritmo de **Expectimax** otimizado com amostragem de **Monte Carlo (Rollouts)** e heurísticas fracionadas para maximizar simultaneamente a Qualidade (Overall) e o Entrosamento (Chemistry) do elenco.

---

## 🎮 Como funciona o Draft no EA FC 26?

O modo Draft é um desafio de construção de elencos (Squad Building) onde o jogador deve montar um time carta por carta, escolhendo entre opções aleatórias fornecidas pelo jogo. O objetivo é criar o time mais forte e entrosado possível para disputar partidas.

A dinâmica funciona da seguinte maneira:
* **Formação e Posições:** O jogador escolhe uma formação tática (ex: 4-3-3) e deve preencher os 11 titulares.
* **A Escolha do Capitão (Rodada 1):** A primeira escolha do Draft sempre oferece superestrelas (Ídolos, Heróis ou jogadores com Overall $\ge$ 88) para ser o pilar do time.
* **Sorteios Subsequentes:** Para cada uma das posições restantes, o jogo sorteia **5 cartas aleatórias** de jogadores que atuam naquela posição. O "peso" do sorteio favorece cartas mais comuns, tornando cartas raras mais difíceis de aparecer.
* **O Dilema (OVR vs. Química):** A grande dificuldade do Draft é equilibrar a qualidade individual do jogador (Overall ou OVR) com o Entrosamento (Chemistry). O entrosamento é gerado quando jogadores do mesmo time compartilham a mesma **Liga**, **Nacionalidade** ou **Clube**. Um time de estrelas sem química terá um desempenho ruim em campo.

---

## 🧠 Arquitetura da Inteligência Artificial

Para resolver o desafio estocástico do Draft, este projeto utiliza algoritmos clássicos de busca em árvores de jogos com elementos de incerteza, otimizados para performance em tempo real.

### 1. Expectimax
O problema do Draft pode ser modelado como uma árvore de decisão onde o jogador humano/bot alterna escolhas com o "acaso" (o jogo sorteando os pacotes).
* **Nós de Max (O Bot):** Avalia as 5 cartas disponíveis na tela e escolhe a que maximiza a utilidade esperada.
* **Nós de Chance (O Jogo):** Representa o sorteio desconhecido dos próximos pacotes.

### 2. O Problema da Explosão Combinatória e a Solução via Monte Carlo
Em um Expectimax clássico, o nó de chance calcularia a probabilidade exata de todas as combinações futuras possíveis. No EA FC, com um banco de milhares de jogadores, calcular o ramo futuro exato para pacotes de 5 cartas em 11 posições resulta em bilhões de permutações, tornando a busca exata impossível.

Para contornar isso, implementamos **Monte Carlo Rollouts**. Em vez de calcular todos os futuros possíveis, o algoritmo aproxima a "Esperança Matemática" simulando o futuro aleatoriamente $K$ vezes.

$$E = \frac{1}{K} \sum_{i=1}^{K} f(S_i)$$

Onde $K$ é o número de rollouts (simulações futuras até preencher os 11 jogadores) e $f(S_i)$ é a nota final do time naquela simulação específica. No nosso cenário base, utilizamos 100 rollouts por opção, garantindo alta confiança estatística nas decisões tomadas.

### 3. Função Objetivo e Heurística Fracionada
A mecânica de Entrosamento do EA FC funciona por "platôs". Por exemplo, você só ganha 1 ponto de química de liga ao juntar 3 jogadores da mesma liga. Ter 1 ou 2 jogadores não muda nada no jogo real. 

Se a IA avaliasse o time usando apenas as regras estritas do jogo, ela sofreria do problema de "cegueira de platô" (falta de gradiente), sendo incapaz de priorizar cartas que estão *quase* completando um ponto de química. 

Para resolver isso, criamos a heurística `chemistry_fractional`, que transforma os platôs do jogo em "rampas". A função avalia times parciais durante a árvore de busca atribuindo pontuações decimais (ex: 0.6 pontos por ter 2 jogadores de uma liga que exige 3 para pontuar). A equação final que dita o quão bom é um time $S$ é dada por:

$$f(S) = \text{OVR}_{mean} + \left( \frac{\text{Chem}_{total} \times 1.2}{11} \right)$$

Isso força o bot a valorizar o entrosamento sem sacrificar demasiadamente a qualidade técnica individual (Overall médio).

---

## 🚀 Como Executar o Projeto

**Pré-requisitos:**
* Python 3.9+
* Pandas
* NumPy

**Passo a passo:**
1. Clone este repositório:
   `git clone https://github.com/igor-alves1/trabalho_final_ia.git`
2. Instale as dependências:
   `pip install -r requirements.txt`
3. Execute o script principal:
   `python main.ipynb` (ou abra no Jupyter Notebook/VS Code).

O bot imprimirá no console, rodada a rodada, as opções lidas da base de dados, a escolha avaliada pelo algoritmo de Expectimax e, ao final, o resumo do time montado e sua nota final.

---

## 🖥️ Interface Web (React)

Em `web/` há uma interface web onde você monta seu próprio time de Draft (formação
fixa **4-3-3**) e vê a IA jogando o **mesmo draft** para comparar as notas
(OVR, Química e Nota Final).

**Arquitetura:**
* **Backend** (`web/backend/server.py`): servidor HTTP leve (stdlib, sem novas
  dependências) que importa `bot.py` / `eafc_utils.py` e expõe uma API JSON
  (`/api/draft/new`, `/evaluate`, `/ai`). As imagens dos jogadores vêm da coluna
  `player_face_url` do CSV (CDN sofifa) e são baixadas/cacheadas em
  `web/backend/static/faces/` — sob demanda pelo servidor ou em lote com
  `web/backend/download_faces.py`.
* **Frontend** (`web/frontend/`): React + Vite (cartas estilo FUT, campo 4-3-3,
  painel de comparação Humano × IA).

**Como rodar:**
```bash
# tudo de uma vez (sobe backend na 8000 e frontend na 5173)
bash web/run.sh
# depois abra http://localhost:5173

# (opcional) baixar todas as imagens do pool antes:
conda run -n venv python web/backend/download_faces.py
```

Veja `STEPS.md` para o detalhamento das decisões e passos.

---
*Projeto desenvolvido para fins de pesquisa em Inteligência Artificial e Algoritmos de Busca.*
