# collectors.py
import logging
from typing import List, Dict, Union
from bs4 import BeautifulSoup

from produto import Produto
from config import SELECTORS


class ProductCollectors:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def parse_products_from_page(self, page_source: str,
                                 filtro: str) -> List[Produto]:
        products = []
        if not page_source:
            logging.warning("Fonte da página vazia, não é possível extrair produtos.")
            return products

        soup = BeautifulSoup(page_source, 'html.parser')
        cards = soup.select(SELECTORS['PRODUCT_CARD_CONTAINER'])
        if not cards:
            logging.info(f"Nenhum card de produto encontrado para o filtro: '{filtro}'.")
            return products

        for card in cards:
            try:
                link_elem = card.find("a", {"data-testid": "product-card::card"})
                name_elem = link_elem.find("h2", {"data-testid": "product-card::name"})
                price_elem = link_elem.find("p", {"data-testid": "product-card::price"})
                rating_elem = card.find("div", {"data-testid": "product-card::rating"})

                if not all([name_elem, price_elem, link_elem]):
                    logging.warning("Dados essenciais de um produto não encontrados, pulando este card.")
                    continue

                name = name_elem.text.strip()
                price_text = price_elem.text.replace("R$", "").replace(".", "").replace(",", ".").strip()
                price = float(price_text)

                if not 0 < price < 100000:
                    logging.warning(f"Invalid price {price} for {name}, skipping.")
                    continue

                link = self.base_url.rstrip('/') + link_elem["href"]

                avaliacao = 0.0
                if rating_elem:
                    try:
                        avaliacao = float(rating_elem.text.split("(")[0].strip())
                    except (ValueError, IndexError):
                        logging.warning("Erro ao extrair a avaliação, definindo como 0.0.")

                products.append(Produto(
                    nome=name,
                    preco=price,
                    avaliacao=avaliacao,
                    link=link,
                    filtros_pesquisados=[filtro]
                ))
            except (AttributeError, ValueError, IndexError) as e:
                logging.warning(f"Erro ao extrair dados de um produto. Detalhes: {e}. Pulando para o próximo.")
                continue
        logging.info(f"Página analisada. {len(products)} produtos extraídos para o filtro '{filtro}'.")
        return products

    def get_product_details(self, page_source: str) -> dict:
        soup = BeautifulSoup(page_source, 'html.parser')
        details = {}

        # Nova tentativa de encontrar a tabela de especificações
        spec_table = soup.find('table', class_='spec-table') 
        if spec_table:
            for row in spec_table.find_all('tr'):
                cols = row.find_all('td')
                if len(cols) == 2:
                    category = row.find_previous('h3').get_text(strip=True) if row.find_previous('h3') else "Geral"
                    key = cols[0].get_text(strip=True)
                    value = cols[1].get_text(strip=True)
                    
                    if category not in details:
                        details[category] = {}
                    details[category][key] = value
            if details:
                return details

        # Manter os seletores originais como fallback caso o novo não funcione
        spec_container_new = soup.select_one("section#technicalSpecifications")
        if spec_container_new:
            for group in spec_container_new.find_all("div", recursive=False):
                title_elem = group.find("h3")
                title = title_elem.get_text(strip=True) if title_elem else "Detalhes Gerais"
                details[title] = {}
                for row in group.find_all("tr"):
                    cols = row.find_all(["td", "th"])
                    if len(cols) >= 2:
                        key = cols[0].get_text(strip=True)
                        value = cols[1].get_text(strip=True)
                        if key and value:
                            details[title][key] = value
            if details:
                return details

        spec_container_old = soup.find("div", {"data-testid": "spec-container"})
        if spec_container_old:
            for spec_group in spec_container_old.find_all('div', {"data-testid": "spec-group"}):
                title_elem = spec_group.find('h3')
                title = title_elem.get_text(strip=True) if title_elem else "Detalhes Gerais"
                details[title] = {}
                for spec_item in spec_group.find_all('li', {"data-testid": "spec-item"}):
                    key_elem = spec_item.find('span', {"data-testid": "spec-item-key"})
                    value_elem = spec_item.find('span', {"data-testid": "spec-item-value"})
                    if key_elem and value_elem:
                        key = key_elem.get_text(strip=True)
                        value = value_elem.get_text(strip=True)
                        details[title][key] = value
            if details:
                return details

        logging.warning("Nenhum container de especificações encontrado. Retornando fallback.")
        return {"Detalhes": {"Erro": "Nenhum dado técnico encontrado."}}