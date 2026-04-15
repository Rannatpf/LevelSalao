"""
CONFIG MODULE - CONFIGURAÇÕES SIMPLIFICADAS
Projeto: Level Salão Dashboard
Suporta: Desenvolvimento Local + Streamlit Cloud
"""

import os
import json
from pathlib import Path

# Carregar variáveis de ambiente do .env (opcional - pode não estar disponível em produção)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ============================================
# CONFIGURAÇÕES GERAIS
# ============================================

APP_ENV = os.getenv('APP_ENV', 'production')
APP_DEBUG = os.getenv('APP_DEBUG', 'false').lower() == 'true'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'app.log')


# ============================================
# GOOGLE SHEETS - DESENVOLVIMENTO + PRODUÇÃO
# ============================================

# Prioridade: 
# 1. Streamlit secrets (Streamlit Cloud)
# 2. Variável de ambiente GOOGLE_SHEETS_CREDENTIALS_JSON (string JSON)
# 3. Arquivo local (credentials.json)

GOOGLE_SHEETS_CREDENTIALS_PATH = os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH', 'credentials.json')
GOOGLE_SHEETS_CREDENTIALS_JSON = os.getenv('GOOGLE_SHEETS_CREDENTIALS_JSON')
GOOGLE_SHEETS_ID = os.getenv('GOOGLE_SHEETS_ID', '1YR4uxDsNf-WlODmtUUJDliGETr9LGBqgcTm74YjL-7E')

# ============================================
# STREAMLIT
# ============================================

STREAMLIT_PORT = 8501
STREAMLIT_ADDRESS = 'localhost'
STREAMLIT_LOGGER_LEVEL = 'info'


# ============================================
# CACHE
# ============================================

CACHE_TTL = 600


# ============================================
# FEATURES
# ============================================

ENABLE_MACHINE_LEARNING = True
ENABLE_ALERTS = True
ENABLE_RECOMMENDATIONS = True


# ============================================
# RESUMO DE CONFIGURAÇÃO (para logging)
# ============================================

CONFIGURACOES_RESUMO = {
    'ambiente': APP_ENV,
    'debug': APP_DEBUG,
    'nivel_log': LOG_LEVEL,
    'arquivo_log': LOG_FILE,
    'porta_streamlit': STREAMLIT_PORT,
    'endereco_streamlit': STREAMLIT_ADDRESS,
    'cache_ttl': CACHE_TTL,
    'features': {
        'machine_learning': ENABLE_MACHINE_LEARNING,
        'alertas': ENABLE_ALERTS,
        'recomendacoes': ENABLE_RECOMMENDATIONS
    }
}

