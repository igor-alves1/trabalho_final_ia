import numpy as np
import pandas as pd
from typing import List, Tuple
from bot import run_single_draft

class DraftGeneticAlgorithm:
    def __init__(self, 
                 df_draft: pd.DataFrame,
                 pop_size: int = 20, 
                 n_genes: int = 15, 
                 n_generations: int = 10,
                 mutation_rate: float = 0.2, 
                 mutation_std: float = 0.5,
                 tournament_size: int = 3,
                 k_drafts: int = 3,
                 gene_min: float = 0.0,
                 gene_max: float = 5.0):
        self.df_draft = df_draft
        self.pop_size = pop_size
        self.n_genes = n_genes
        self.n_generations = n_generations
        self.mutation_rate = mutation_rate
        self.mutation_std = mutation_std
        self.tournament_size = tournament_size
        self.k_drafts = k_drafts
        self.gene_min = gene_min
        self.gene_max = gene_max
        
        self.population = np.random.uniform(self.gene_min, self.gene_max, (self.pop_size, self.n_genes))
        self.fitness_scores = np.zeros(self.pop_size)
    
    def evaluate_fitness(self, individual: np.ndarray) -> float:
        scores = []
        dna = individual.tolist()
        
        eval_weights = dna[0:4]
        pos_priorities = dna[4:15]
        
        for _ in range(self.k_drafts):
            score = run_single_draft(
                self.df_draft, 
                weights=eval_weights, 
                position_priorities=pos_priorities,
                num_rollouts=10, 
                verbose=False
            )
            scores.append(score)
            
        return np.mean(scores)
    
    def tournament_selection(self) -> np.ndarray:
        competitors_idx = np.random.choice(self.pop_size, self.tournament_size, replace=False)
        best_idx = competitors_idx[np.argmax(self.fitness_scores[competitors_idx])]
        return self.population[best_idx]

    def crossover_uniform(self, parent1: np.ndarray, parent2: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        mask = np.random.rand(self.n_genes) > 0.5
        
        child1 = np.where(mask, parent1, parent2)
        child2 = np.where(mask, parent2, parent1)
        
        return child1, child2
    
    def mutate_gaussian(self, individual: np.ndarray) -> np.ndarray:
        for i in range(self.n_genes):
            if np.random.rand() < self.mutation_rate:
                ruido = np.random.normal(0, self.mutation_std)
                individual[i] += ruido
                
        return np.clip(individual, self.gene_min, self.gene_max)

    def run(self):
        print(f"Iniciando Algoritmo Genético: População={self.pop_size}, Gerações={self.n_generations}")
        
        best_historical_individual = None
        best_historical_fitness = -float('inf')

        for generation in range(self.n_generations):
            print(f"\n--- Avaliando Geração {generation + 1}/{self.n_generations} ---")
            
            for i in range(self.pop_size):
                self.fitness_scores[i] = self.evaluate_fitness(self.population[i])
                print(f"Indivíduo {i+1}: Fitness = {self.fitness_scores[i]:.3f} | DNA = {np.round(self.population[i], 2)}")

            best_idx = np.argmax(self.fitness_scores)
            gen_best_fitness = self.fitness_scores[best_idx]
            gen_best_individual = self.population[best_idx].copy()
            
            if gen_best_fitness > best_historical_fitness:
                best_historical_fitness = gen_best_fitness
                best_historical_individual = gen_best_individual.copy()

            print(f">>> Melhor da Geração: {gen_best_fitness:.3f} | DNA: {np.round(gen_best_individual, 2)}")

            new_population = [gen_best_individual]

            while len(new_population) < self.pop_size:
                parent1 = self.tournament_selection()
                parent2 = self.tournament_selection()
                
                child1, child2 = self.crossover_uniform(parent1, parent2)
                
                child1 = self.mutate_gaussian(child1)
                child2 = self.mutate_gaussian(child2)
                
                new_population.append(child1)
                if len(new_population) < self.pop_size:
                    new_population.append(child2)

            self.population = np.array(new_population)
            
        print("\n===========================================")
        print(" EVOLUÇÃO CONCLUÍDA! ")
        print(f" Melhor Fitness Encontrado: {best_historical_fitness:.3f}")
        print(f" Melhor DNA (Pesos): {np.round(best_historical_individual, 3)}")
        print("===========================================")
        
        return best_historical_individual