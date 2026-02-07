#!/usr/bin/env python3
"""
Sprite Extractor - Aplicação para extrair sprites individuais de sprite sheets
Autor: Antigravity
Data: 2026-01-29
"""
import sys
import argparse
from PyQt6.QtWidgets import QApplication
from main_window import MainWindow


def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description="Sprite Extractor - Extrator de Sprites")
    parser.add_argument("path", nargs="?", help="Caminho para o sprite sheet")
    parser.add_argument("--version", action="version", version="Sprite Extractor 1.0.0")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    
    # Configurar estilo da aplicação
    app.setStyle("Fusion")
    
    # Criar e exibir janela principal
    window = MainWindow(initial_path=args.path)
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
