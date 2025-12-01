#!/usr/bin/env python3
"""
Cliente de Chat P2P - Ponto de Entrada Principal
"""
import sys
import json
import logging
import argparse
from pathlib import Path

from p2p_client import P2PClient


def setup_logging(config: dict):
    """Configura o sistema de logging"""
    log_level = config.get('logging', {}).get('level', 'INFO')
    log_file = config.get('logging', {}).get('file')
    
    # Cria formatador
    formatter = logging.Formatter(
        '%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configura logger raiz
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Handler de console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Handler de arquivo (se configurado)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def load_config(config_path: str) -> dict:
    """Carrega configuração de arquivo JSON"""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file: {e}")
        sys.exit(1)


def main():
    """Ponto de entrada principal"""
    parser = argparse.ArgumentParser(description='P2P Chat Client')
    parser.add_argument(
        '--config',
        default='config.json',
        help='Path to configuration file (default: config.json)'
    )
    parser.add_argument(
        '--namespace',
        help='Override namespace from config'
    )
    parser.add_argument(
        '--name',
        help='Override peer name from config'
    )
    parser.add_argument(
        '--port',
        type=int,
        help='Override port from config'
    )
    parser.add_argument(
        '--rdv-host',
        help='Override rendezvous server host'
    )
    parser.add_argument(
        '--rdv-port',
        type=int,
        help='Override rendezvous server port'
    )
    
    args = parser.parse_args()
    
    # Carrega configuração
    config = load_config(args.config)
    
    # Sobrescreve com argumentos de linha de comando
    if args.namespace:
        config['peer']['namespace'] = args.namespace
    if args.name:
        config['peer']['name'] = args.name
    if args.port:
        config['peer']['port'] = args.port
    
    # Configura logging
    setup_logging(config)
    
    logger = logging.getLogger(__name__)
    logger.info("="*60)
    logger.info("P2P Chat Client Starting")
    logger.info("="*60)
    logger.info(f"Peer ID: {config['peer']['name']}@{config['peer']['namespace']}")
    logger.info(f"Port: {config['peer']['port']}")
    logger.info(f"Rendezvous: {config['rendezvous']['host']}:{config['rendezvous']['port']}")
    logger.info("="*60)
    
    # Cria e inicia cliente
    client = P2PClient(config)
    
    try:
        if not client.start():
            logger.error("Failed to start P2P client")
            sys.exit(1)
        
        # Mantém thread principal viva
        while True:
            import time
            time.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("\nReceived interrupt signal")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
    finally:
        client.stop()


if __name__ == '__main__':
    main()
