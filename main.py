# main.py
import logging
from scraper import ZoomScraper
from analisador import AnalisadorProdutos
from config import PAGES_TO_SCRAPE

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Deixe False para ver o navegador trabalhando. Mude para True em servidores/CI.
    scraper = ZoomScraper(headless=False)

    termo_de_busca = "notebook"
    filtros = ["Mais Relevantes", "Melhor Avaliados", "Menor Preço"]

    try:
        # 1) Busca no Zoom e coleta das 3 primeiras páginas para cada filtro
        produtos = scraper.search_and_collect(
            query=termo_de_busca,
            filters=filtros,
            pages_to_scrape=PAGES_TO_SCRAPE
        )

        if not produtos:
            logging.warning("No products were found after scraping.")
        else:
            # 2) Ranking/normalização
            analisador = AnalisadorProdutos(produtos)
            ranked_products = analisador.rankear_produtos()

            if ranked_products:
                # Mostrar um sumário no terminal
                analisador.exibir_ranking(top_n=5)

                # 3) Abrir cada um dos top 5 e capturar a Ficha Técnica
                scraper.fetch_details_for_top(ranked_products, top_n=5)

                # 4) Salvar CSV final com detalhes dos 5 melhores
                analisador.salvar_ranking_em_csv("melhores_notebooks.csv", top_n=5)
            else:
                logging.info("No products could be ranked.")
    except Exception as e:
        logging.critical(
            f"An unhandled error occurred in the main script: {e}",
            exc_info=True
        )
    finally:
        scraper.close()
