# analisador.py
import pandas as pd
from typing import List
from produto import Produto
from config import PAGES_TO_SCRAPE  # For normalization

class AnalisadorProdutos:
    def __init__(self, produtos: List[Produto]):
        self.produtos = produtos

    def rankear_produtos(self) -> List[Produto]:
        if not self.produtos:
            return []

        df = pd.DataFrame([p.__dict__ for p in self.produtos])
        df['nome_normalized'] = df['nome'].str.lower().str.strip()  # For better grouping

        # Frequência de aparição do produto nos resultados
        frequencia = df.groupby('nome_normalized').size().reset_index(name='frequencia')
        df = df.merge(frequencia, on='nome_normalized')

        # Normalização dos dados para cálculo do score
        max_freq = df['frequencia'].max() if not df['frequencia'].empty else 1
        min_price, max_price = df['preco'].min(), df['preco'].max()
        price_range = max_price - min_price if max_price > min_price else 1
        
        df['score'] = (0.5 * df['frequencia'] / max_freq) + \
                      (0.3 * (1 - (df['preco'] - min_price) / price_range)) + \
                      (0.2 * df['avaliacao'] / 5.0) # Assume avaliação máxima de 5.0

        # Atribuir o score calculado de volta aos objetos Produto
        score_map = df.set_index('nome_normalized')['score'].to_dict()
        for p in self.produtos:
            normalized_name = p.nome.lower().strip()
            if normalized_name in score_map:
                p.ranking = score_map[normalized_name]
        
        # Filtrar duplicatas e ordenar, mantendo o produto com o maior ranking
        unique_products = {p.nome.lower().strip(): p for p in self.produtos}
        return sorted(list(unique_products.values()), key=lambda p: p.ranking or 0, reverse=True)

    def salvar_ranking_em_csv(self, nome_arquivo: str, top_n: int = 5):
        ranked_products = self.rankear_produtos()[:top_n]
        if not ranked_products:
            print("No products to save.")
            return

        # Prepare data for CSV
        data_for_csv = []
        for p in ranked_products:
            row = {
                'Nome': p.nome,
                'Preco': p.preco,
                'Avaliacao': p.avaliacao,
                'Relevancia': p.relevancia,
                'Ranking_Final': p.ranking,
                'Link': p.link,
                'Filtros_Pesquisados': ", ".join(p.filtros_pesquisados)
            }
            # Add details as columns
            for group, details in p.detalhes.items():
                for key, value in details.items():
                    row[f'{group} - {key}'] = value
            data_for_csv.append(row)

        df = pd.DataFrame(data_for_csv)
        df.to_csv(nome_arquivo, index=False, encoding='utf-8')
        print(f"Ranking salvo em {nome_arquivo}")

    def exibir_ranking(self, top_n: int = 5):
        ranked_products = self.rankear_produtos()[:top_n]
        if not ranked_products:
            print("No products found.")
            return
            
        print("\n--- Top Produtos ---")
        for i, produto in enumerate(ranked_products):
            print(f"#{i+1}: {produto.nome}")
            print(f"  Preço: R$ {produto.preco:,.2f}")
            print(f"  Avaliação: {produto.avaliacao}")
            print(f"  Relevância (frequência): {produto.relevancia}")
            print(f"  Score de Ranking: {produto.ranking:.4f}")
            print(f"  Link: {produto.link}")
            print(f"  Detalhes: {produto.detalhes.get('Geral', {})}")
            print("-" * 20)