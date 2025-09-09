# config.py
SELECTORS = {
    'SEARCH_INPUT': "input#searchInput",
    'PRODUCT_CARD_CONTAINER': "div[data-testid='product-card']",
    # novo seletor para o elemento <select> de ordenação
    'SORT_SELECT': "select[data-testid='select-order-by'], select#orderBy",
    # NEXT_PAGE e SPEC_CONTAINER continuam iguais
    'NEXT_PAGE': "//a[@aria-label='Página {page_num}']",
    'SPEC_CONTAINER': "section#technicalSpecifications",

}

BASE_URL = "https://www.zoom.com.br/"
PAGES_TO_SCRAPE = 3
WAIT_TIMEOUT = 30 
RETRY_ATTEMPTS = 3