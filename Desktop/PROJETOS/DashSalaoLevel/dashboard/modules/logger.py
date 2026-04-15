"""
LOGGING MODULE
Sistema de logging estruturado para monitoramento
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from datetime import datetime
import json

from .config import LOG_LEVEL, LOG_FILE, APP_ENV


def configurar_logging():
    """
    Configura logger estruturado com output para console e arquivo
    
    Returns:
        logging.Logger: Logger configurado
    """
    
    # Criar logger
    logger = logging.getLogger('level_salao')
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    
    # Remover handlers anteriores (evitar duplicação)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # ====== FORMATTER ESTRUTURADO ======
    class JSONFormatter(logging.Formatter):
        """Formata logs em JSON para melhor parsing"""
        
        def format(self, record):
            log_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno,
            }
            
            # Adicionar exceção se houver
            if record.exc_info:
                log_data['exception'] = self.formatException(record.exc_info)
            
            return json.dumps(log_data, ensure_ascii=False)
    
    class SimpleFormatter(logging.Formatter):
        """Formata logs simples para console"""
        
        def format(self, record):
            if record.levelno == logging.WARNING:
                emoji = "⚠️"
            elif record.levelno == logging.ERROR:
                emoji = "❌"
            elif record.levelno == logging.INFO:
                emoji = "ℹ️"
            else:
                emoji = "🔧"
            
            return f"{emoji} [{record.levelname}] {record.getMessage()}"
    
    # ====== HANDLER: CONSOLE ======
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    console_formatter = SimpleFormatter()
    console_handler.setFormatter(console_formatter)
    # Forçar UTF-8 no console (compatibilidade Windows)
    if hasattr(console_handler.stream, 'reconfigure'):
        try:
            console_handler.stream.reconfigure(encoding='utf-8')
        except:
            pass
    logger.addHandler(console_handler)
    
    # ====== HANDLER: ARQUIVO (com rotação) ======
    try:
        # Criar handler com rotação de 5 arquivos de 5MB cada
        file_handler = RotatingFileHandler(
            filename=LOG_FILE,
            maxBytes=5_242_880,  # 5MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        json_formatter = JSONFormatter()
        file_handler.setFormatter(json_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"Não foi possível criar handler de arquivo: {e}")
    
    return logger


# Criar logger global
logger = configurar_logging()


# ============================================
# FUNÇÕES AUXILIARES DE LOGGING
# ============================================

def log_info(mensagem, **kwargs):
    """Log info com contexto adicional"""
    if kwargs:
        logger.info(f"{mensagem} | {json.dumps(kwargs, ensure_ascii=False)}")
    else:
        logger.info(mensagem)


def log_erro(mensagem, exc_info=None, **kwargs):
    """Log de erro com contexto adicional"""
    if kwargs:
        logger.error(f"{mensagem} | {json.dumps(kwargs, ensure_ascii=False)}", exc_info=exc_info)
    else:
        logger.error(mensagem, exc_info=exc_info)


def log_aviso(mensagem, **kwargs):
    """Log de aviso com contexto adicional"""
    if kwargs:
        logger.warning(f"{mensagem} | {json.dumps(kwargs, ensure_ascii=False)}")
    else:
        logger.warning(mensagem)


def log_debug(mensagem, **kwargs):
    """Log de debug com contexto adicional"""
    if kwargs:
        logger.debug(f"{mensagem} | {json.dumps(kwargs, ensure_ascii=False)}")
    else:
        logger.debug(mensagem)


# ============================================
# CONTEXTO DE OPERAÇÕES
# ============================================

class LogContext:
    """Context manager para logging de operações"""
    
    def __init__(self, operacao, **contexto):
        self.operacao = operacao
        self.contexto = contexto
    
    def __enter__(self):
        log_info(f"Iniciando: {self.operacao}", **self.contexto)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            log_info(f"Sucesso: {self.operacao} concluída")
        else:
            log_erro(
                f"Erro em {self.operacao}",
                exc_info=(exc_type, exc_val, exc_tb),
                **self.contexto
            )
        return False


# Log inicial de startup
def log_startup():
    """Log de inicialização da aplicação"""
    from .config import CONFIGURACOES_RESUMO, APP_ENV
    
    logger.info("=" * 60)
    logger.info(f"🚀 Level Salão Dashboard inicializado")
    logger.info(f"   Ambiente: {APP_ENV}")
    logger.info(f"   Versão: 1.0.0 (Modularizado)")
    logger.info(f"   Logging JSON: Habilitado")
    logger.info("=" * 60)
    
    if APP_ENV == 'production':
        logger.info("⚠️ MODO PRODUÇÃO ATIVO - Monitore logs.json")
