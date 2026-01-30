#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""
GIMP Plugin: Edit in Sprite Extractor
Integrates GIMP with the Standalone Sprite Extractor tool.
"""

from gimpfu import *
import os
import subprocess
import tempfile

def edit_in_sprite_extractor(image, drawable):
    # 1. Definir caminho temporário
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, "gimp_sprite_sheet.png")
    
    # 2. Exportar imagem atual como PNG
    # pdb.file_png_save_defaults(image, drawable, temp_path, temp_path)
    # Usando a versão mais compatível
    pdb.gimp_file_save(image, drawable, temp_path, temp_path)
    
    # 3. Caminho para o executável (ajuste conforme seu sistema)
    # Por padrão, assumimos que está no diretório onde foi instalado
    app_path = "/home/yurix/Documentos/my-blueprint-maker/main.py"
    python_path = "/home/yurix/Documentos/my-blueprint-maker/.venv/bin/python"
    
    # 4. Executar aplicação standalone
    try:
        subprocess.Popen([python_path, app_path, temp_path])
        gimp.message("Sprite Extractor aberto! Salve no GIMP para atualizar o preview automaticamente.")
    except Exception as e:
        gimp.message("Erro ao abrir Sprite Extractor: " + str(e))

register(
    "python_fu_edit_in_sprite_extractor",
    "Edit in Sprite Extractor",
    "Opens the current image in the Sprite Extractor standalone tool for 3D preview and slicing.",
    "Antigravity",
    "Antigravity",
    "2026",
    "<Image>/Filters/Sprites/Edit in Sprite Extractor...",
    "RGB*, GRAY*",
    [],
    [],
    edit_in_sprite_extractor)

main()
