# scraper.py (with HTTP 429 retry for product details)
import time
import logging
from typing import List, Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (TimeoutException, NoSuchElementException)
import random

from produto import Produto
from config import SELECTORS, BASE_URL, WAIT_TIMEOUT, RETRY_ATTEMPTS
from collectors import ProductCollectors


class ZoomScraper:
    def __init__(self, headless: bool = True):
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless=new')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1280,2000')
        options.add_argument('--no-sandbox')
        options.add_argument('--log-level=2')
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
        all_products: List[Produto] = []
        full_filter_list = ["Sem filtro"] + filters
        try:
            logging.info(f"Navigating to search page for query: '{query}'")
            self.driver.get(BASE_URL)

            search_box = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, SELECTORS['SEARCH_INPUT'])))
            search_box.clear()
            search_box.send_keys(query)
            search_box.submit()

            # para cada filtro (inclui 'Sem filtro')
            for idx, filtro in enumerate(full_filter_list):
                if filtro != "Sem filtro":
                    self._apply_filter(filtro)
                else:
                    logging.info("Starting collection with filter: 'Sem filtro'...")

                # paginar 3 páginas
                for page in range(1, pages_to_scrape + 1):
                    if page > 1:
                        self._go_to_page(page)
                    page_source = self._retry_get_page_source()
                    if not page_source:
                        continue
                    products = self.collectors.parse_products_from_page(page_source, filtro)
                    self._merge_products(all_products, products)
            return all_products
        except Exception as e:
            logging.error(f"Unexpected error during search: {e}", exc_info=True)
            return all_products

    def _merge_products(self, existing: List[Produto], new: List[Produto]):
        for p_new in new:
            if "notebook" not in p_new.nome.lower():
                continue
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
        try:
            select_elem = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, SELECTORS['SORT_SELECT'])))

            # mapear nomes -> valores comuns
            mapping = {
                'Mais Relevantes': ['relevance', 'relevancia', 'relevance_desc'],
                'Melhor Avaliados': ['rating_desc', 'best_rating', 'avaliacao_desc'],
                'Menor Preço': ['price_asc', 'menor_preco', 'priceasc']
            }
            value_candidates = mapping.get(filter_name, [])

            # tentar via javascript alterar select (mais robusto)
            changed = False
            for opt in select_elem.find_elements(By.TAG_NAME, 'option'):
                val = (opt.get_attribute('value') or '').lower()
                text = (opt.text or '').strip()
                if text.lower() == filter_name.lower() or any(vc in val for vc in value_candidates):
                    self.driver.execute_script(
                        "arguments[0].selected=true; arguments[0].dispatchEvent(new Event('change'));", opt
                    )
                    changed = True
                    break

            if changed:
                logging.info(f"Filter '{filter_name}' applied.")
                time.sleep(random.uniform(1.5, 3.0))
                return True

            logging.warning(f"Could not apply filter '{filter_name}'. Proceeding without it.")
            return False
        except TimeoutException:
            logging.warning(f"Filter select not found for '{filter_name}'.")
            return False

    def _go_to_page(self, page_num: int):
        try:
            xpath = SELECTORS['NEXT_PAGE'].format(page_num=page_num)
            elem = self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
            time.sleep(0.5)
            elem.click()
            logging.info(f"Navigated to page {page_num}")
            time.sleep(1.0)
        except Exception:
            logging.warning(f"Could not navigate to page {page_num}")

    # ---------- Helpers para 429 ----------
    def _is_429(self, html: str) -> bool:
        text = (html or "").lower()
        return ("http error 429" in text) or ("too many requests" in text) or (">429<" in text)

    def _retry_if_429(self, max_retries: int = 2) -> str:
        """Espera e atualiza a página se detectar 429. Retorna o HTML final."""
        backoff = 6.0
        for attempt in range(max_retries + 1):
            html = self.driver.page_source
            if not self._is_429(html):
                return html
            logging.warning(f"429 detectado ao abrir a página de produto. Esperando {backoff:.0f}s e tentando novamente... (tentativa {attempt+1}/{max_retries})")
            time.sleep(backoff + random.uniform(0.5, 1.5))
            self.driver.refresh()
            # pequeno tempo adicional para re-render
            time.sleep(2.5 + random.uniform(0, 1.0))
            backoff *= 1.5
        # retorna o último HTML, mesmo que ainda seja 429
        return self.driver.page_source

    def fetch_details_for_top(self, products: List[Produto], top_n: int = 5):
        top = products[:top_n]
        for product in top:
            try:
                logging.info(f"Fetching details for product: {product.nome}")
                self.driver.get(product.link)

                # abrir aba "Ficha técnica" se existir
                try:
                    ficha = self.wait.until(EC.element_to_be_clickable((By.XPATH, SELECTORS['SPEC_TAB_XPATH'])))
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", ficha)
                    time.sleep(0.6)
                    ficha.click()
                    time.sleep(0.8)
                except Exception:
                    pass

                # rolar para provável container de specs
                self.driver.execute_script("window.scrollBy(0, 600);")
                time.sleep(random.uniform(2.5, 4.0))

                # --- Retry específico para HTTP 429 ---
                html = self._retry_if_429(max_retries=2)

                product.detalhes = self.collectors.get_product_details(html)
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