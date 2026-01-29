"""
Sprite Extractor - Core processing module
Detecta e extrai sprites individuais de uma sprite sheet
"""
import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Sprite:
    """Representa um sprite detectado"""
    bbox: Tuple[int, int, int, int]  # x, y, largura, altura
    image: np.ndarray
    index: int
    view_type: str = "unknown"  # front, back, left, right, top, bottom, etc.


class SpriteExtractor:
    """Classe principal para detecção e extração de sprites"""
    
    def __init__(self):
        self.original_image: Optional[np.ndarray] = None
        self.sprites: List[Sprite] = []
        self.image_path: Optional[Path] = None
        self._last_binary_mask: Optional[np.ndarray] = None
        
    def load_image(self, path: str) -> bool:
        """
        Carrega uma imagem do disco
        
        Args:
            path: Caminho para a imagem
            
        Returns:
            True se carregada com sucesso, False caso contrário
        """
        try:
            self.image_path = Path(path)
            # Carrega com canal alpha se disponível
            self.original_image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
            
            if self.original_image is None:
                return False
                
            return True
        except Exception as e:
            print(f"Erro ao carregar imagem: {e}")
            return False
    
    def detect_sprites(self, threshold: int = 10, min_area: int = 100, layout_hint: str = None) -> List[Sprite]:
        """
        Detecta sprites individuais na imagem
        """
        if self.original_image is None:
            return []
        
        self.sprites = []
        image = self.original_image.copy()
        
        # Converter para escala de cinza se a imagem tiver 3 canais (BGR)
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image # Já é grayscale ou tem 1 canal
        
        # Se a imagem tiver canal alpha, verificar se é útil (não totalmente sólido)
        has_useful_alpha = False
        if self.original_image.shape[2] == 4: # BGRA
            alpha_channel = self.original_image[:, :, 3]
            # Se houver qualquer pixel transparente (alpha < 255), consideramos o alpha útil
            if not np.all(alpha_channel == 255):
                has_useful_alpha = True
                # Binarizar o canal alpha: pixels com alguma opacidade são considerados parte do sprite
                _, binary = cv2.threshold(alpha_channel, 0, 255, cv2.THRESH_BINARY)
        
        if not has_useful_alpha:
            # Caso contrário, usar thresholding na imagem em escala de cinza
            # Detectar se o fundo é claro ou escuro baseando-se nos cantos
            # Amostrar pequenas áreas nos cantos, com uma margem para ignorar molduras
            h, w = gray.shape
            margin_h = min(20, h // 50)
            margin_w = min(20, w // 50)
            corner_size = 10
            
            # Amostras nos 4 cantos, levemente para dentro
            samples = [
                gray[margin_h:margin_h+corner_size, margin_w:margin_w+corner_size],
                gray[margin_h:margin_h+corner_size, -margin_w-corner_size:-margin_w],
                gray[-margin_h-corner_size:-margin_h, margin_w:margin_w+corner_size],
                gray[-margin_h-corner_size:-margin_h, -margin_w-corner_size:-margin_w]
            ]
            avg_corner_val = np.mean([np.mean(s) for s in samples])
            is_light_bg = avg_corner_val > 127
            
            if is_light_bg:
                # Fundo claro: inverter threshold para que sprites fiquem brancos
                # Usamos o threshold como uma margem de "quão diferente deve ser do fundo"
                # Se o fundo é 255 e threshold é 10, pegamos tudo < 245
                _, binary = cv2.threshold(gray, 255 - threshold, 255, cv2.THRESH_BINARY_INV)
            else:
                # Fundo escuro: threshold normal
                _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
        
        # Limpar ruído e separar sprites próximos
        # 1. Opening para remover ruído pequeno
        kernel_small = np.ones((3, 3), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_small, iterations=1)
        
        # 2. Erode para quebrar pontes finas entre sprites
        binary = cv2.erode(binary, kernel_small, iterations=2)
        
        # 3. Dilate para restaurar o corpo do sprite (menos que a erosão para manter separação)
        binary = cv2.dilate(binary, kernel_small, iterations=1)
        
        self._last_binary_mask = binary.copy() # Salvar para preview no UI
        
        # Limpar bordas agressivamente (garantir que molduras ou sombras de borda não junte tudo)
        border = 20 # Aumentado para 20px para ignorar molduras comuns em JPEGs
        binary[0:border, :] = 0
        binary[-border:, :] = 0
        binary[:, 0:border] = 0
        binary[:, -border:] = 0
        
        # Encontrar contornos
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Extrair bounding boxes
        bboxes = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            if area >= min_area:
                bboxes.append((x, y, w, h))
        
        # Ordenar bounding boxes: primeiro por Y (linha), depois por X (coluna)
        bboxes.sort(key=lambda b: (round(b[1] / 50) * 50, b[0]))
        
        # Criar objetos Sprite
        for idx, (x, y, w, h) in enumerate(bboxes):
            sprite_img = image[y:y+h, x:x+w]
            sprite = Sprite(bbox=(x, y, w, h), image=sprite_img, index=idx)
            self.sprites.append(sprite)
        
        # Classificar vistas
        if len(self.sprites) > 0:
            self._classify_views(layout_hint)
        
        return self.sprites
    
    def _classify_views(self, layout_hint: str = None):
        """
        Classifica o tipo de vista baseado na posição no grid ou hint de layout.
        """
        num_sprites = len(self.sprites)
        if num_sprites == 0: return

        # Usar hint se fornecido
        if layout_hint == "3x2" and num_sprites >= 6:
            views = ["front", "top", "side_a", "bottom", "side_b", "back"]
            for i, s in enumerate(self.sprites[:6]): s.view_type = views[i]
            return
        elif layout_hint == "2x3" and num_sprites >= 6:
            views = ["front", "top", "back", "left", "right", "bottom"]
            for i, s in enumerate(self.sprites[:6]): s.view_type = views[i]
            return
        elif layout_hint == "2x2" and num_sprites >= 4:
            views = ["front", "back", "left", "right"]
            for i, s in enumerate(self.sprites[:4]): s.view_type = views[i]
            return

        # Fallback para detecção automática
        rows, cols = self._detect_grid_structure()
        
        # Padrões de nomenclatura baseados no número total de sprites e grid
        if num_sprites == 1:
            self.sprites[0].view_type = "front"
        
        elif num_sprites == 2:
            if rows == 1:
                self.sprites[0].view_type = "left"
                self.sprites[1].view_type = "right"
            else:
                self.sprites[0].view_type = "front"
                self.sprites[1].view_type = "back"
        
        elif num_sprites == 4:
            if rows == 2 and cols == 2:
                # Comum em 2x2
                self.sprites[0].view_type = "front"
                self.sprites[1].view_type = "back"
                self.sprites[2].view_type = "left"
                self.sprites[3].view_type = "right"
            else:
                views = ["front", "back", "left", "right"]
                for i, s in enumerate(self.sprites):
                    if i < 4: s.view_type = views[i]
        
        elif num_sprites == 6:
            # Layout 3x2 (Muito comum para 6 vistas: Front/Top, Mid, Bottom/Back)
            if rows == 3 and cols == 2:
                views = ["front", "top", "side_a", "bottom", "side_b", "back"]
            # Layout 2x3
            elif rows == 2 and cols == 3:
                views = ["front", "top", "back", "left", "right", "bottom"]
            else:
                views = ["front", "back", "left", "right", "top", "bottom"]
            
            for i, sprite in enumerate(self.sprites):
                if i < len(views): sprite.view_type = views[i]
        
        else:
            # Para outros casos, usar row/col
            for sprite in self.sprites:
                r, c = self._get_sprite_grid_position(sprite, rows, cols)
                sprite.view_type = f"row{r+1}_col{c+1}"

    def _detect_grid_structure(self) -> Tuple[int, int]:
        """
        Detecta a estrutura do grid baseado nas posições centrais dos sprites
        """
        if not self.sprites:
            return (0, 0)
        
        # Usar o centro do sprite para agrupar, pois as alturas variam muito (ex: antena)
        y_centers = sorted([s.bbox[1] + s.bbox[3]//2 for s in self.sprites])
        x_centers = sorted([s.bbox[0] + s.bbox[2]//2 for s in self.sprites])
        
        # Agrupar posições por proximidade
        def count_clusters(positions, tolerance=100):
            if not positions: return 0
            clusters = 1
            for i in range(1, len(positions)):
                if positions[i] - positions[i-1] > tolerance:
                    clusters += 1
            return clusters
        
        num_rows = count_clusters(y_centers)
        num_cols = count_clusters(x_centers)
        
        return (num_rows, num_cols)
    
    def _get_sprite_grid_position(self, sprite: Sprite, rows: int, cols: int) -> Tuple[int, int]:
        """
        Retorna a posição no grid (índice da linha, índice da coluna) usando centros
        """
        y_centers = sorted([s.bbox[1] + s.bbox[3]//2 for s in self.sprites])
        x_centers = sorted([s.bbox[0] + s.bbox[2]//2 for s in self.sprites])
        
        def get_cluster_index(val, positions, tolerance=100):
            unique_clusters = []
            for p in positions:
                if not any(abs(p - c) < tolerance for c in unique_clusters):
                    unique_clusters.append(p)
            unique_clusters.sort()
            center = val
            for i, c in enumerate(unique_clusters):
                if abs(center - c) < tolerance:
                    return i
            return 0
        
        sprite_y_center = sprite.bbox[1] + sprite.bbox[3]//2
        sprite_x_center = sprite.bbox[0] + sprite.bbox[2]//2
        
        r = get_cluster_index(sprite_y_center, y_centers)
        c = get_cluster_index(sprite_x_center, x_centers)
        return (r, c)
    
    def get_sprite(self, index: int) -> Optional[Sprite]:
        """
        Retorna um sprite específico pelo índice
        
        Args:
            index: Índice do sprite
            
        Returns:
            Sprite ou None se índice inválido
        """
        if 0 <= index < len(self.sprites):
            return self.sprites[index]
        return None
    
    def export_sprites(self, output_dir: str, prefix: str = "sprite", 
                      format: str = "png", use_view_names: bool = True,
                      padding: int = 0, uniform_size: bool = False) -> List[Path]:
        """
        Exporta todos os sprites detectados
        
        Args:
            output_dir: Diretório de saída
            prefix: Prefixo para nomes dos arquivos
            format: Formato da imagem (png, jpg, etc)
            use_view_names: Se True, usa o tipo de vista no nome do arquivo
            padding: Margem extra em pixels ao redor do sprite
            uniform_size: Se True, todas as imagens terão o mesmo tamanho (do maior sprite)
            
        Returns:
            Lista de caminhos dos arquivos exportados
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        exported_files = []
        
        # Calcular tamanho uniforme se necessário
        target_w, target_h = 0, 0
        if uniform_size and self.sprites:
            max_w = max(s.bbox[2] for s in self.sprites)
            max_h = max(s.bbox[3] for s in self.sprites)
            target_w = max_w + (2 * padding)
            target_h = max_h + (2 * padding)
        
        for sprite in self.sprites:
            # Gerar nome do arquivo
            if use_view_names and sprite.view_type != "unknown":
                filename = f"{prefix}_{sprite.view_type}.{format}"
            else:
                filename = f"{prefix}_{sprite.index + 1:02d}.{format}"
            
            filepath = output_path / filename
            
            # Processar imagem do sprite com padding e redimensionamento
            sprite_img = sprite.image
            
            if padding > 0 or uniform_size:
                h, w = sprite_img.shape[:2]
                
                # Se não for uniforme, o tamanho é apenas o sprite + padding
                if not uniform_size:
                    curr_target_w = w + (2 * padding)
                    curr_target_h = h + (2 * padding)
                else:
                    curr_target_w = target_w
                    curr_target_h = target_h
                
                # Criar novo canvas (com alpha se o original tiver)
                if sprite_img.shape[2] == 4:
                    new_img = np.zeros((curr_target_h, curr_target_w, 4), dtype=np.uint8)
                else:
                    # Se não tiver alpha, preencher com a cor do fundo (assumindo branco ou preto)
                    # Usamos a lógica de detecção de fundo para decidir a cor do preenchimento
                    # Aqui, como padrão para exportação "limpa", o branco (255) é comum em blueprints
                    fill_val = 255 if self.original_image.mean() > 127 else 0
                    new_img = np.full((curr_target_h, curr_target_w, 3), fill_val, dtype=np.uint8)
                
                # Calcular posição central
                x_offset = (curr_target_w - w) // 2
                y_offset = (curr_target_h - h) // 2
                
                # Colar sprite no centro
                new_img[y_offset:y_offset+h, x_offset:x_offset+w] = sprite_img
                sprite_img = new_img
            
            # Salvar imagem
            cv2.imwrite(str(filepath), sprite_img)
            exported_files.append(filepath)
        
        return exported_files
    
    
    def get_preview_image(self, draw_boxes: bool = True) -> Optional[np.ndarray]:
        """
        Retorna uma imagem de preview com bounding boxes opcionais
        
        Args:
            draw_boxes: Se True, desenha retângulos ao redor dos sprites
            
        Returns:
            Imagem de preview ou None
        """
        if self.original_image is None:
            return None
        
        preview = self.original_image.copy()
        
        # Converter para BGR se necessário para desenhar
        if len(preview.shape) == 2:
            preview = cv2.cvtColor(preview, cv2.COLOR_GRAY2BGR)
        elif preview.shape[2] == 4:
            preview = cv2.cvtColor(preview, cv2.COLOR_BGRA2BGR)
        
        if draw_boxes:
            for sprite in self.sprites:
                x, y, w, h = sprite.bbox
                # Desenhar retângulo verde ao redor do sprite
                cv2.rectangle(preview, (x, y), (x + w, y + h), (0, 255, 0), 2)
                # Desenhar número do sprite
                cv2.putText(preview, str(sprite.index + 1), (x, y - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return preview

    def get_binary_mask_preview(self) -> Optional[np.ndarray]:
        """Retorna a última máscara binária gerada"""
        return self._last_binary_mask
