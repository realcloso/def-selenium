# scraper.py
import time
import logging
from typing import List, Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (TimeoutException, NoSuchElementException)
from selenium.webdriver.support.ui import Select as SeleniumSelect
import random

from produto import Produto
from config import SELECTORS, BASE_URL, WAIT_TIMEOUT, RETRY_ATTEMPTS
from collectors import ProductCollectors

class ZoomScraper:
    def __init__(self, headless: bool = True):
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        service = Service()
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, WAIT_TIMEOUT)
        self.collectors = ProductCollectors(BASE_URL)

    def _retry_get_page_source(self) -> Optional[str]:
        for attempt in range(RETRY_ATTEMPTS):
            try:
                self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, SELECTORS['PRODUCT_CARD_CONTAINER'])))
                logging.info(f"Products loaded. Attempt {attempt+1}/{RETRY_ATTEMPTS}.")
                return self.driver.page_source
            except TimeoutException:
                logging.warning(f"Timeout waiting for products. Retrying... (Attempt {attempt+1})")
                time.sleep(2 ** attempt + random.uniform(0, 1))
        return None

    def search_and_collect(self, query: str, filters: List[str], pages_to_scrape: int = 3) -> List[Produto]:
        all_products = []
        full_filter_list = ["Sem filtro"] + filters
        
        try:
            logging.info(f"Navigating to search page for query: '{query}'")
            self.driver.get(BASE_URL)
            
            search_box = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, SELECTORS['SEARCH_INPUT'])))
            search_box.clear()
            search_box.send_keys(query)
            search_box.submit()
            
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, SELECTORS['PRODUCT_CARD_CONTAINER'])))
            logging.info("Successfully navigated to search results page.")
            search_url = self.driver.current_url
            time.sleep(random.uniform(3, 5))

            for filter_name in full_filter_list:
                logging.info(f"Starting collection with filter: '{filter_name}'...")
                
                self.driver.get(search_url)
                time.sleep(random.uniform(5, 7))

                if filter_name != "Sem filtro":
                    if not self._apply_filter(filter_name):
                        continue

                for page_num in range(pages_to_scrape):
                    page_source = self._retry_get_page_source()
                    if not page_source:
                        logging.warning(f"Failed to get page source for '{filter_name}' on page {page_num + 1}. Skipping to next filter.")
                        break
                    
                    products_on_page = self.collectors.parse_products_from_page(page_source, filter_name)
                    self._merge_products(all_products, products_on_page)

                    if not self._go_to_next_page(page_num + 1):
                        logging.info(f"Finished scraping all available pages for filter '{filter_name}'.")
                        break
                    
                time.sleep(random.uniform(2, 4))

        except Exception as e:
            logging.critical(f"A critical error occurred during scraping: {e}", exc_info=True)
            return []
            
        return all_products

    def _merge_products(self, existing: List[Produto], new: List[Produto]):
        for p_new in new:
            # Adicionar esta linha de validação
            if "notebook" not in p_new.nome.lower():
                continue # Pula produtos que não contém a palavra "notebook" no nome
            
            found = False
            for p_existing in existing:
                if p_existing.nome.lower().strip() == p_new.nome.lower().strip():
                    if p_new.filtros_pesquisados[0] not in p_existing.filtros_pesquisados:
                        p_existing.filtros_pesquisados.append(p_new.filtros_pesquisados[0])
                    p_existing.relevancia += 1 
                    found = True
                    break
            if not found:
                p_new.relevancia = 1 
                existing.append(p_new)

    def _apply_filter(self, filter_name: str) -> bool:
        """
        Aplica o filtro/ordenação usando o <select> de ordenação (orderBy).
        Mapeia os nomes legíveis para os valores das <option> encontrados na página.
        """
        try:
            select_elem = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, SELECTORS['SORT_SELECT']))
            )

            sel = SeleniumSelect(select_elem)

            mapping = {
                "Mais Relevantes": "lowering_percentage_desc",
                "Mais relevante": "lowering_percentage_desc",
                "Menor Preço": "price_asc",
                "Menor preço": "price_asc",
                "Melhor Avaliados": "rating_desc",
                "Melhor avaliado": "rating_desc",
                "Maior Preço": "price_desc",
                "Maior preço": "price_desc",
            }

            value = mapping.get(filter_name)

            if value:
                sel.select_by_value(value)
            else:
                try:
                    sel.select_by_visible_text(filter_name)
                except Exception:
                    logging.warning(f"No mapping or visible option text for filter '{filter_name}'.")
                    return False

            self.driver.execute_script(
                "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
                select_elem
            )

            logging.info(f"Filter '{filter_name}' applied.")
            time.sleep(random.uniform(3, 5))
            return True

        except Exception as e:
            logging.error(f"Failed to apply filter '{filter_name}': {e}", exc_info=True)
            return False

    def _go_to_next_page(self, current_page_num: int) -> bool:
        try:
            next_page_num = current_page_num + 1
            next_xpath = SELECTORS['NEXT_PAGE'].format(page_num=next_page_num)
            next_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, next_xpath)))
            self.driver.execute_script("arguments[0].click();", next_button)
            time.sleep(random.uniform(2, 4))
            logging.info(f"Navigated to page {next_page_num}")
            return True
        except (NoSuchElementException, TimeoutException) as e:
            logging.info(f"Next page button not found. Assuming end of pages. Details: {e}")
            return False

    def get_product_details_batch(self, products: List[Produto]) -> None:
        logging.info("Starting batch collection of product details...")
        for product in products:
            self._get_product_details_safe(product)
            time.sleep(random.uniform(1, 2))

    def _get_product_details_safe(self, product: Produto):
        try:
            logging.info(f"Fetching details for product: {product.nome}")
            self.driver.get(product.link)
            WebDriverWait(self.driver, WAIT_TIMEOUT).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(random.uniform(5, 10))  # Increased sleep for slow loads
            
            product.detalhes = self.collectors.get_product_details(self.driver.page_source)
            
            logging.info(f"Details fetched successfully for {product.nome}.")
        except TimeoutException as e:
            logging.error(f"Timeout while getting details for {product.nome}: {e}")
            product.detalhes = {"Detalhes": {"Erro": "Timeout ao carregar os detalhes."}}
        except Exception as e:
            logging.error(f"Unexpected error for {product.nome}: {e}", exc_info=True)
            product.detalhes = {"Detalhes": {"Erro": f"Ocorreu um erro inesperado: {str(e)}"}}

    def close(self):
        logging.info("Closing the WebDriver.")
        self.driver.quit()