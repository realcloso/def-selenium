# main.py
import logging
from scraper import ZoomScraper
from analisador import AnalisadorProdutos
from config import PAGES_TO_SCRAPE

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Recomenda-se usar headless=True para execução em produção ou em ambientes sem interface gráfica
    scraper = ZoomScraper(headless=True)
    
    termo_de_busca = "notebook"
    filtros = ["Mais Relevantes", "Melhor Avaliados", "Menor Preço"]

    try:
        logging.info(f"Starting scraping for: {termo_de_busca}")
        todos_produtos = scraper.search_and_collect(termo_de_busca, filtros, PAGES_TO_SCRAPE)

        if todos_produtos:
            analisador = AnalisadorProdutos(todos_produtos)
            
            # Rankear os produtos
            ranked_products = analisador.rankear_produtos()
            
            if ranked_products:
                # Exibir o ranking dos top 5 produtos
                analisador.exibir_ranking(top_n=5)

                # Coletar detalhes para os top 5 produtos
                top_5 = ranked_products[:5]
                scraper.get_product_details_batch(top_5)

                # Salvar o ranking em um arquivo CSV
                analisador.salvar_ranking_em_csv("melhores_notebooks.csv", top_n=5)
            else:
                logging.info("No products could be ranked.")
        else:
            logging.warning("No products were found after scraping.")
    except Exception as e:
        logging.critical(f"An unhandled error occurred in the main script: {e}", exc_info=True)
    finally:
        scraper.close()