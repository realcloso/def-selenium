# collectors.py
import logging
from typing import List, Dict, Union
from bs4 import BeautifulSoup

from produto import Produto
from config import SELECTORS, SPEC_SELECTORS


class ProductCollectors:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def parse_products_from_page(self, page_source: str, filtro: str) -> List[Produto]:
        products: List[Produto] = []
        soup = BeautifulSoup(page_source, 'html.parser')

        cards = soup.select(SELECTORS['PRODUCT_CARD_CONTAINER'])
        for card in cards:
            try:
                name_elem = card.select_one("h2, h3, [data-testid='product-card::name']")
                price_elem = card.select_one("[data-testid='product-card::price'], span[data-testid='product-card::price'], .product-card__price, [class*='price']")
                link_elem = card.select_one("a[href*='/notebook/']") or card.select_one('a')

                if not (name_elem and price_elem and link_elem):
                    continue

                name = name_elem.get_text(strip=True)

                price_text = price_elem.get_text().replace('R$', '').replace('.', '').replace(',', '.').strip()
                price = float(price_text)
                if not 0 < price < 100000:
                    logging.warning(f"Invalid price {price} for {name}, skipping.")
                    continue

                link = link_elem.get('href')
                if link and link.startswith('/'):
                    link = self.base_url.rstrip('/') + link

                # avaliação pode não existir
                rating = 0.0
                rating_elem = card.select_one("[data-testid='product-card::rating'], .rating, [aria-label*='avalia']")
                if rating_elem:
                    try:
                        rating = float(rating_elem.get_text().split('(')[0].strip().replace(',', '.'))
                    except Exception:
                        pass

                products.append(Produto(
                    nome=name,
                    preco=price,
                    avaliacao=rating,
                    link=link,
                    filtros_pesquisados=[filtro]
                ))
            except Exception as e:
                logging.warning(f"Erro ao extrair dados de um produto: {e}")
                continue

        logging.info(f"Página analisada. {len(products)} produtos extraídos para o filtro '{filtro}'.")
        return products

    def get_product_details(self, page_source: str) -> Dict[str, Dict[str, str]]:
        """Extrai ficha técnica de diferentes formatos (tabela, lista, dl/dt)."""
        soup = BeautifulSoup(page_source, 'html.parser')

        # 1) tentar containers conhecidos
        for sel in SPEC_SELECTORS:
            container = soup.select_one(sel)
            if container:
                details = self._extract_from_container(container)
                if details:
                    return details

        # 2) fallback: procurar qualquer bloco com palavras de especificação
        candidates = soup.select("section, div, article")
        for cand in candidates:
            text = (cand.get_text(" ", strip=True) or '').lower()
            if any(k in text for k in ['ficha técnica', 'especificações', 'técnic']):
                details = self._extract_from_container(cand)
                if details:
                    return details

        logging.warning("Nenhum container de especificações encontrado. Retornando fallback.")
        return {"Detalhes": {"Erro": "Nenhum dado técnico encontrado."}}

    def _extract_from_container(self, container) -> Dict[str, Dict[str, str]]:
        details: Dict[str, Dict[str, str]] = {}

        # A) tabelas <table>
        for tbl in container.select('table'):
            title = tbl.get('aria-label') or tbl.get('summary') or 'Ficha técnica'
            group = {}
            for tr in tbl.select('tr'):
                cols = tr.find_all(['th', 'td'])
                if len(cols) >= 2:
                    key = cols[0].get_text(strip=True)
                    val = cols[1].get_text(strip=True)
                    if key and val:
                        group[key] = val
            if group:
                details[title] = group

        # B) listas de definição <dl>
        for dl in container.select('dl'):
            title = dl.get('aria-label') or 'Especificações'
            group = {}
            dts = dl.find_all('dt')
            dds = dl.find_all('dd')
            for dt, dd in zip(dts, dds):
                key = dt.get_text(strip=True)
                val = dd.get_text(strip=True)
                if key and val:
                    group[key] = val
            if group:
                details[title] = group

        # C) itens <li> com padrão "chave: valor"
        for li in container.select('li'):
            txt = li.get_text(" ", strip=True)
            if ':' in txt and len(txt) < 120:
                key, val = [p.strip() for p in txt.split(':', 1)]
                if key and val:
                    details.setdefault('Especificações', {})[key] = val

        return details
