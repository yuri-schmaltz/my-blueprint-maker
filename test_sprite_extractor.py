#!/usr/bin/env python3
"""
Teste de Verificação Final - Sprite Extractor
"""
from pathlib import Path
from sprite_extractor import SpriteExtractor
import cv2


def test_new_logic():
    print("🧪 Verificando Nova Lógica de Detecção e Classificação\n")
    
    test_cases = [
        {
            "path": "/home/yurix/.gemini/antigravity/brain/3b786021-6530-4bcc-886d-613b9f4d6314/uploaded_media_0_1769720213582.jpg",
            "name": "Robô Azul (3x2)",
            "threshold": 15,
            "min_area": 5000
        },
        {
            "path": "/home/yurix/.gemini/antigravity/brain/3b786021-6530-4bcc-886d-613b9f4d6314/uploaded_media_1_1769720213582.png",
            "name": "Mecha Amarelo (White BG)",
            "threshold": 50,
            "min_area": 2000
        }
    ]
    
    extractor = SpriteExtractor()
    
    for test in test_cases:
        print(f"\n📂 Testando: {test['name']}")
        if not extractor.load_image(test['path']):
            print("   ❌ Erro ao carregar")
            continue
            
        sprites = extractor.detect_sprites(threshold=test['threshold'], min_area=test['min_area'])
        print(f"   📊 Background Claro: {extractor.original_image.mean() > 127}")
        print(f"   🔍 Sprites Detectados: {len(sprites)}")
        
        for s in sprites:
            print(f"      - {s.view_type:10s} | Area: {s.bbox[2]*s.bbox[3]:7d} | Pos: {s.bbox[0:2]}")
            
    print("\n✅ Verificação concluída.")


if __name__ == "__main__":
    test_new_logic()
