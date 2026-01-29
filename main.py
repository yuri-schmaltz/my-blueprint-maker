#!/usr/bin/env python3
"""
Sprite Extractor - Aplicação para extrair sprites individuais de sprite sheets
Autor: Antigravity
Data: 2026-01-29
"""
import sys
from PyQt6.QtWidgets import QApplication
from main_window import MainWindow


def main():
    """Função principal"""
    app = QApplication(sys.argv)
    
    # Configurar estilo da aplicação
    app.setStyle("Fusion")
    
    # Criar e exibir janela principal
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
