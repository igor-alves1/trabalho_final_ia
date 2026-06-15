# Implementação dos Algoritmos

## 1. Greedy com fast_f
- Adicionar modo `"greedy_f"` na classe `Bot`
- No `choose`, calcular `fast_f(current_squad + candidate)` para cada carta e retornar o índice da maior

## 2. Random
- Adicionar modo `"random"` na classe `Bot`
- No `choose`, retornar um índice aleatório entre 0 e 4

## 3. Simulated Annealing
- Criar classe `SimulatedAnnealingBot`
- Opera diferente: recebe o time completo e otimiza trocando cartas iterativamente
- Definir função de temperatura, critério de aceitação e critério de parada
