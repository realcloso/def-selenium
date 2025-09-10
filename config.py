# config.py
SELECTORS = {
    'SEARCH_INPUT': "input#searchInput",
    'PRODUCT_CARD_CONTAINER': "div[data-testid='product-card']",
    # seletor do <select> de ordenação
    'SORT_SELECT': "select[data-testid='select-order-by'], select#orderBy",
    # paginação (usamos .format para substituir {page_num})
    'NEXT_PAGE': "//a[@aria-label='Página {page_num}']",
    # guia/aba de ficha técnica
    'SPEC_TAB_XPATH': "//button[contains(translate(normalize-space(.), 'FICHA TÉCNICA', 'ficha técnica'), 'ficha técnica')]"
}

# lista de seletores alternativos para o container de especificações
SPEC_SELECTORS = [
    "section#technicalSpecifications",
    "section[data-testid='technical-specifications']",
    "section[id*='spec']",
    "div[data-testid='product-specifications']",
    "div[data-testid='spec-container']",
    "div#specifications",
    "section.product-specifications",
]

BASE_URL = "https://www.zoom.com.br/"
PAGES_TO_SCRAPE = 3
WAIT_TIMEOUT = 45  # um pouco maior para páginas lentas
RETRY_ATTEMPTS = 3
