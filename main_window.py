"""
Main Window - Interface gráfica principal do Sprite Extractor
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QSlider, QLineEdit, QFileDialog,
    QGraphicsView, QGraphicsScene, QListWidget, QListWidgetItem,
    QSpinBox, QMessageBox, QGroupBox, QFormLayout, QTabWidget,
    QCheckBox, QComboBox
)
from PyQt6.QtCore import Qt, QRectF, QFileSystemWatcher, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QPen, QColor, QKeySequence, QShortcut, QIcon
from pathlib import Path
import cv2
import numpy as np

from sprite_extractor import SpriteExtractor
from preview_3d import SpritePreview3D


class ClickableGraphicsView(QGraphicsView):
    """QGraphicsView customizado que detecta cliques na imagem"""
    clicked = pyqtSignal(int, int) # Sinal que emite x, y

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Obter coordenadas na cena
            scene_pos = self.mapToScene(event.pos())
            self.clicked.emit(int(scene_pos.x()), int(scene_pos.y()))
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    """Janela principal da aplicação"""
    
    def __init__(self, initial_path=None):
        super().__init__()
        self.extractor = SpriteExtractor()
        self.selected_sprite_index = -1
        self.watcher = QFileSystemWatcher()
        self.watcher.fileChanged.connect(self.on_file_updated)
        self.init_ui()
        
        if initial_path:
            self.load_image(initial_path)
        
    def init_ui(self):
        """Inicializa a interface do usuário"""
        self.setWindowTitle("Sprite Extractor - Extrator de Sprites")
        self.setGeometry(100, 100, 1200, 800)
        
        # Definir ícone da janela
        icon_path = Path(__file__).parent / "resources" / "icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal com abas
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Aba 1: Extrator Individual (Antigo Layout)
        single_tab = QWidget()
        single_layout = QHBoxLayout()
        single_tab.setLayout(single_layout)
        
        # Painel esquerdo - Visualização
        left_panel = self._create_view_panel()
        single_layout.addWidget(left_panel, stretch=2)
        
        # Painel direito - Controles
        right_panel = self._create_control_panel()
        single_layout.addWidget(right_panel, stretch=1)
        
        self.tabs.addTab(single_tab, "Extrator Individual")
        
        # Aba 2: Processamento em Lote
        batch_tab = self._create_batch_panel()
        self.tabs.addTab(batch_tab, "Processamento em Lote")
        
        # Aba 3: Preview 3D (Novo!)
        self.preview_3d_container = QWidget()
        preview_3d_layout = QVBoxLayout()
        self.preview_3d_container.setLayout(preview_3d_layout)
        
        self.preview_3d_tab = SpritePreview3D()
        preview_3d_layout.addWidget(self.preview_3d_tab)
        
        # Controles 3D
        preview_controls = QHBoxLayout()
        preview_controls.addWidget(QLabel("Cor de Fundo:"))
        self.bg_combo = QComboBox()
        self.bg_combo.addItems(["Cinza Escuro", "Preto", "Branco", "Céu"])
        self.bg_combo.currentIndexChanged.connect(self.on_bg_color_changed)
        preview_controls.addWidget(self.bg_combo)
        preview_controls.addStretch()
        preview_3d_layout.addLayout(preview_controls)
        
        self.tabs.addTab(self.preview_3d_container, "Preview 3D")
        
        # Atalhos de teclado
        QShortcut(QKeySequence("Ctrl+D"), self).activated.connect(self.detect_sprites)
        QShortcut(QKeySequence("Ctrl+E"), self).activated.connect(self.export_sprites)
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self.load_image)
        
        # Conectar mudança de aba para atualizar 3D
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
    def _create_batch_panel(self) -> QWidget:
        """Cria o painel de processamento em lote"""
        panel = QWidget()
        layout = QVBoxLayout()
        panel.setLayout(layout)
        
        title = QLabel("Processamento em Lote")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px 0;")
        layout.addWidget(title)
        
        form_group = QGroupBox("Configurações de Lote")
        form_layout = QFormLayout()
        form_group.setLayout(form_layout)
        
        self.batch_input_btn = QPushButton("📂 Selecionar Pasta de Entrada")
        self.batch_input_btn.clicked.connect(self.select_batch_input)
        form_layout.addRow("Entrada:", self.batch_input_btn)
        
        self.batch_output_btn = QPushButton("📂 Selecionar Pasta de Saída")
        self.batch_output_btn.clicked.connect(self.select_batch_output)
        form_layout.addRow("Saída:", self.batch_output_btn)
        
        self.batch_prefix = QLineEdit("batch_sprite")
        form_layout.addRow("Prefixo:", self.batch_prefix)
        
        self.batch_recursive = QCheckBox("Buscar em subpastas (recursivo)")
        self.batch_recursive.setChecked(True)
        form_layout.addRow("", self.batch_recursive)
        
        layout.addWidget(form_group)
        
        # Log de progresso
        self.batch_log = QListWidget()
        layout.addWidget(QLabel("Progresso:"))
        layout.addWidget(self.batch_log)
        
        # Botão Iniciar
        self.start_batch_btn = QPushButton("🚀 Iniciar Processamento em Lote")
        self.start_batch_btn.setStyleSheet("""
            background-color: #673AB7; color: white; padding: 15px; font-weight: bold; border-radius: 5px;
        """)
        self.start_batch_btn.clicked.connect(self.run_batch_processing)
        layout.addWidget(self.start_batch_btn)
        
        return panel

    def select_batch_input(self):
        """Seleciona pasta de entrada para lote"""
        path = QFileDialog.getExistingDirectory(self, "Selecionar Pasta de Entrada")
        if path:
            self.batch_input_path = path
            self.batch_input_btn.setText(f"📁 {Path(path).name}")

    def select_batch_output(self):
        """Seleciona pasta de saída para lote"""
        path = QFileDialog.getExistingDirectory(self, "Selecionar Pasta de Saída")
        if path:
            self.batch_output_path = path
            self.batch_output_btn.setText(f"📁 {Path(path).name}")

    def run_batch_processing(self):
        """Executa o processamento em lote"""
        if not hasattr(self, 'batch_input_path') or not hasattr(self, 'batch_output_path'):
            QMessageBox.warning(self, "Aviso", "Selecione as pastas de entrada e saída.")
            return

        input_path = Path(self.batch_input_path)
        output_path = Path(self.batch_output_path)
        prefix_base = self.batch_prefix.text() or "sprite"
        is_recursive = self.batch_recursive.isChecked()
        
        # Encontrar todas as imagens
        extensions = ['*.png', '*.jpg', '*.jpeg', '*.webp', '*.bmp']
        image_files = []
        
        glob_func = input_path.rglob if is_recursive else input_path.glob
        for ext in extensions:
            image_files.extend(list(glob_func(ext)))
        
        if not image_files:
            QMessageBox.information(self, "Info", f"Nenhuma imagem encontrada na pasta de entrada {' (incluindo subpastas)' if is_recursive else ''}.")
            return
            
        self.batch_log.clear()
        self.batch_log.addItem(f"🚀 Iniciando processamento de {len(image_files)} arquivos...")
        
        processed_count = 0
        for img_file in image_files:
            try:
                # Criar um extrator temporário para o lote
                temp_extractor = SpriteExtractor()
                if temp_extractor.load_image(str(img_file)):
                    # Usar valores atuais da UI para detecção
                    threshold = self.threshold_slider.value()
                    min_area = self.min_area_spinbox.value()
                    
                    sprites = temp_extractor.detect_sprites(threshold=threshold, min_area=min_area)
                    
                    if sprites:
                        # Criar subpasta para este sprite sheet para manter organização
                        sheet_name = img_file.stem
                        sheet_output = output_path / sheet_name
                        
                        # Usar configurações de exportação da aba principal
                        padding = self.padding_spin.value()
                        uniform = self.uniform_check.isChecked()
                        
                        # Prefixo combina a base com o nome do arquivo original para evitar colisões
                        final_prefix = f"{prefix_base}_{sheet_name}"
                        
                        temp_extractor.export_sprites(
                            output_dir=str(sheet_output),
                            prefix=final_prefix,
                            padding=padding,
                            uniform_size=uniform
                        )
                        processed_count += 1
                        self.batch_log.addItem(f"✅ {img_file.name} -> {len(sprites)} sprites em /{sheet_name}")
                    else:
                        self.batch_log.addItem(f"⚠️ {img_file.name}: Nenhum sprite detectado")
                else:
                    self.batch_log.addItem(f"❌ Erro ao carregar: {img_file.name}")
            except Exception as e:
                self.batch_log.addItem(f"❌ Falha em {img_file.name}: {str(e)}")
            
            # Forçar atualização da UI
            self.batch_log.scrollToBottom()
            import PyQt6.QtCore as QtCore
            QtCore.QCoreApplication.processEvents()
            
        QMessageBox.information(self, "Fim", f"Processamento concluído!\n{processed_count} arquivos processados com sucesso.")

    def _create_view_panel(self) -> QWidget:
        """Cria o painel de visualização da imagem"""
        panel = QWidget()
        layout = QVBoxLayout()
        panel.setLayout(layout)
        
        # Label de título
        title = QLabel("Preview da Imagem")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Área de visualização da imagem
        self.graphics_view = ClickableGraphicsView()
        self.graphics_scene = QGraphicsScene()
        self.graphics_view.setScene(self.graphics_scene)
        self.graphics_view.setMinimumSize(600, 500)
        self.graphics_view.clicked.connect(self.on_image_clicked)
        layout.addWidget(self.graphics_view)
        
        return panel
    
    def _create_control_panel(self) -> QWidget:
        """Cria o painel de controles"""
        panel = QWidget()
        layout = QVBoxLayout()
        panel.setLayout(layout)
        
        # Botão carregar imagem
        self.load_btn = QPushButton("📁 Carregar Imagem")
        self.load_btn.setStyleSheet("""
            QPushButton {
                padding: 10px;
                font-size: 14px;
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.load_btn.clicked.connect(self.load_image)
        layout.addWidget(self.load_btn)
        
        # Grupo de parâmetros de detecção
        detection_group = QGroupBox("Parâmetros de Detecção")
        detection_layout = QFormLayout()
        detection_group.setLayout(detection_layout)
        
        # Threshold slider
        threshold_container = QHBoxLayout()
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setMinimum(1)
        self.threshold_slider.setMaximum(255)
        self.threshold_slider.setValue(10)
        self.threshold_slider.valueChanged.connect(self.on_threshold_changed)
        
        self.threshold_value_label = QLabel("10")
        threshold_container.addWidget(self.threshold_slider)
        threshold_container.addWidget(self.threshold_value_label)
        detection_layout.addRow("Threshold:", threshold_container)
        
        # Área mínima
        self.min_area_spinbox = QSpinBox()
        self.min_area_spinbox.setMinimum(10)
        self.min_area_spinbox.setMaximum(1000000)
        self.min_area_spinbox.setValue(100)
        self.min_area_spinbox.setSuffix(" px²")
        self.min_area_spinbox.valueChanged.connect(self.on_detection_params_changed)
        detection_layout.addRow("Área Mínima:", self.min_area_spinbox)
        
        # Layout Preset
        self.layout_combo = QComboBox()
        self.layout_combo.addItems(["Auto", "3x2 (Front/Top/Sides/Back)", "2x3 (Front/Top/Back/Sides)", "2x2 (Basic)"])
        self.layout_combo.currentIndexChanged.connect(self.on_detection_params_changed)
        detection_layout.addRow("Layout:", self.layout_combo)
        
        layout.addWidget(detection_group)
        
        # Checkbox para mostrar máscara
        self.show_mask_check = QCheckBox("Mostrar Máscara Binária")
        self.show_mask_check.stateChanged.connect(lambda: self.display_image(show_boxes=self.detect_btn.isEnabled()))
        layout.addWidget(self.show_mask_check)
        
        # Botão detectar
        self.detect_btn = QPushButton("🔍 Detectar Sprites")
        self.detect_btn.setEnabled(False)
        self.detect_btn.setStyleSheet("""
            QPushButton {
                padding: 10px;
                font-size: 14px;
                background-color: #2196F3;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover:enabled {
                background-color: #0b7dda;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.detect_btn.clicked.connect(self.detect_sprites)
        layout.addWidget(self.detect_btn)
        
        # Lista de sprites detectados
        sprites_label = QLabel("Sprites Detectados:")
        sprites_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(sprites_label)
        
        self.sprites_list = QListWidget()
        self.sprites_list.setMaximumHeight(200)
        self.sprites_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.sprites_list.customContextMenuRequested.connect(self.show_context_menu)
        self.sprites_list.itemSelectionChanged.connect(self.on_sprite_selected)
        layout.addWidget(self.sprites_list)
        
        # Grupo de edição de sprite
        self.edit_group = QGroupBox("Edição de Sprite Selecionado")
        self.edit_group.setEnabled(False)
        edit_layout = QGridLayout() # Usar Grid para alinhar larguras dos botões
        self.edit_group.setLayout(edit_layout)
        
        # Rotação (Linha 0)
        edit_layout.addWidget(QLabel("Rotação:"), 0, 0)
        rotate_container = QHBoxLayout()
        for angle in [0, 90, 180, 270]:
            btn = QPushButton(f"{angle}°")
            btn.clicked.connect(lambda checked, a=angle: self.rotate_selected_sprite(a))
            rotate_container.addWidget(btn)
        edit_layout.addLayout(rotate_container, 0, 1)
        
        # Lateralidade rápida (Linha 1)
        edit_layout.addWidget(QLabel("Vista:"), 1, 0)
        view_container = QHBoxLayout()
        quick_views = [
            ("front", "Front"), ("back", "Rear"), 
            ("left", "Left"), ("right", "Right"), 
            ("top", "Top"), ("bottom", "Down")
        ]
        for v_id, v_name in quick_views:
            btn = QPushButton(v_name)
            btn.clicked.connect(lambda checked, val=v_id: self.set_selected_sprite_view(val))
            view_container.addWidget(btn)
        edit_layout.addLayout(view_container, 1, 1)
        
        # Garantir que a coluna dos botões expanda
        edit_layout.setColumnStretch(1, 1)
        
        layout.addWidget(self.edit_group)
        
        # Grupo de exportação
        export_group = QGroupBox("Exportação")
        export_layout = QFormLayout()
        export_group.setLayout(export_layout)
        
        # Prefixo do nome
        self.prefix_input = QLineEdit()
        self.prefix_input.setText("sprite")
        self.prefix_input.setPlaceholderText("Ex: robot, vehicle")
        export_layout.addRow("Prefixo:", self.prefix_input)
        
        # Margem (Padding)
        self.padding_spin = QSpinBox()
        self.padding_spin.setRange(0, 100)
        self.padding_spin.setValue(10)
        self.padding_spin.setSuffix(" px")
        export_layout.addRow("Padding:", self.padding_spin)
        
        # Tamanho Uniforme
        self.uniform_size_check = QCheckBox("Tamanho Uniforme")
        self.uniform_size_check.setToolTip("Garante que todos os sprites tenham as mesmas dimensões")
        export_layout.addRow("", self.uniform_size_check)
        
        layout.addWidget(export_group)
        
        # Botão exportar
        self.export_btn = QPushButton("💾 Exportar Sprites")
        self.export_btn.setEnabled(False)
        self.export_btn.setStyleSheet("""
            QPushButton {
                padding: 10px;
                font-size: 14px;
                background-color: #FF9800;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover:enabled {
                background-color: #e68900;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.export_btn.clicked.connect(self.export_sprites)
        layout.addWidget(self.export_btn)
        
        # Spacer
        layout.addStretch()
        
        return panel
    
    def load_image(self, file_path=None):
        """Carrega uma imagem do disco"""
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Selecionar Sprite Sheet",
                str(Path.home()),
                "Imagens (*.png *.jpg *.jpeg *.bmp *.webp)"
            )
        
        if file_path:
            if self.extractor.load_image(file_path):
                # Limpar watchers antigos e adicionar o novo
                paths = self.watcher.files()
                if paths:
                    self.watcher.removePaths(paths)
                self.watcher.addPath(str(file_path))
                
                self.display_image()
                self.detect_btn.setEnabled(True)
                # Auto-detectar sprites
                self.detect_sprites()
            else:
                QMessageBox.critical(self, "Erro", "Falha ao carregar a imagem")

    def on_file_updated(self, path):
        """Callback quando o arquivo vigiado é alterado externamente"""
        if self.extractor.load_image(path):
            self.detect_sprites()
            # Se estiver na aba 3D, atualizar
            if self.tabs.currentIndex() == 2:
                self.sync_3d_preview()
    
    def display_image(self, show_boxes: bool = False):
        """Exibe a imagem no preview"""
        if self.extractor.original_image is not None:
            if self.show_mask_check.isChecked():
                # Mostrar a máscara binária processada
                image = self.extractor.get_binary_mask_preview()
            else:
                image = self.extractor.get_preview_image(draw_boxes=show_boxes, selected_index=self.selected_sprite_index)
            
            if image is None:
                return
            
            # Converter numpy array para QPixmap
            if len(image.shape) == 2:
                # Escala de cinza ou Máscara
                height, width = image.shape
                q_image = QImage(image.data, width, height, width, QImage.Format.Format_Grayscale8)
            elif image.shape[2] == 3:
                # BGR -> RGB
                height, width, channel = image.shape
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                q_image = QImage(rgb_image.data, width, height, 3 * width, QImage.Format.Format_RGB888)
            elif image.shape[2] == 4:
                # BGRA -> RGBA
                height, width, channel = image.shape
                rgba_image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGBA)
                q_image = QImage(rgba_image.data, width, height, 4 * width, QImage.Format.Format_RGBA8888)
            
            pixmap = QPixmap.fromImage(q_image)
            self.graphics_scene.clear()
            self.graphics_scene.addPixmap(pixmap)
            self.graphics_view.fitInView(self.graphics_scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
    
    def on_threshold_changed(self, value):
        """Callback quando o threshold muda"""
        self.threshold_value_label.setText(str(value))
    
    def on_detection_params_changed(self):
        """Callback quando parâmetros de detecção mudam"""
        if self.extractor.original_image is not None:
            # Auto-detectar novamente
            self.detect_sprites()
    
    def detect_sprites(self):
        """Detecta sprites na imagem"""
        self.selected_sprite_index = -1
        if hasattr(self, 'edit_group'):
            self.edit_group.setEnabled(False)
            
        threshold = self.threshold_slider.value()
        min_area = self.min_area_spinbox.value()
        
        # Salvar tipos de vista manuais antes de re-detectar se necessário
        manual_views = {}
        for i, s in enumerate(self.extractor.sprites):
            if s.view_type != "unknown":
                manual_views[i] = s.view_type

        # Obter layout hint
        layout_text = self.layout_combo.currentText()
        layout_hint = None
        if "3x2" in layout_text: layout_hint = "3x2"
        elif "2x3" in layout_text: layout_hint = "2x3"
        elif "2x2" in layout_text: layout_hint = "2x2"

        sprites = self.extractor.detect_sprites(threshold=threshold, min_area=min_area, layout_hint=layout_hint)
        
        # Restaurar vistas se os índices coincidirem (heurística simples)
        # Em uma implementação real, usaríamos a posição (x,y) para mapear
        
        # Atualizar visualização com bounding boxes
        self.display_image(show_boxes=True)
        self.update_sprite_list()
        
        # Habilitar botão de exportação
        self.export_btn.setEnabled(len(sprites) > 0)

    def update_sprite_list(self):
        """Atualiza a lista de sprites na UI"""
        self.sprites_list.clear()
        selected_item = None
        for sprite in self.extractor.sprites:
            x, y, w, h = sprite.bbox
            
            # Formatar nome da vista para o usuário
            view_name = sprite.view_type.replace("_", " ").title()
            if view_name == "Back": view_name = "Rear"
            if view_name == "Bottom": view_name = "Down"
            
            rot_label = f" ({sprite.rotation}°)" if sprite.rotation != 0 else ""
            item = QListWidgetItem(f"{view_name}{rot_label} - {w}x{h}px")
            item.setData(Qt.ItemDataRole.UserRole, sprite.index)
            self.sprites_list.addItem(item)
            if sprite.index == self.selected_sprite_index:
                selected_item = item
        
        if selected_item:
            self.sprites_list.blockSignals(True)
            self.sprites_list.setCurrentItem(selected_item)
            self.sprites_list.blockSignals(False)

    def show_context_menu(self, position):
        """Mostra menu de contexto para renomear vistas"""
        item = self.sprites_list.itemAt(position)
        if not item:
            return

        idx = item.data(Qt.ItemDataRole.UserRole)
        sprite = self.extractor.get_sprite(idx)
        if not sprite:
            return

        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction
        
        menu = QMenu()
        views = ["front", "back", "left", "right", "top", "bottom"]
        
        for v in views:
            action = menu.addAction(v.title())
            action.triggered.connect(lambda checked, val=v: self.set_sprite_view(idx, val))
        
        menu.addSeparator()
        custom_action = menu.addAction("Custom...")
        custom_action.triggered.connect(lambda: self.set_custom_view(idx))
        
        menu.exec(self.sprites_list.mapToGlobal(position))

    def on_bg_color_changed(self, index):
        """Callback quando a cor de fundo do 3D muda"""
        colors = [
            (0.2, 0.2, 0.2), # Cinza Escuro
            (0.0, 0.0, 0.0), # Preto
            (0.9, 0.9, 0.9), # Branco
            (0.5, 0.7, 1.0)  # Céu
        ]
        if 0 <= index < len(colors):
            r, g, b = colors[index]
            self.preview_3d_tab.set_bg_color(r, g, b)

    def on_tab_changed(self, index):
        """Callback quando as abas mudam"""
        if index == 2: # Aba 3D
            self.sync_3d_preview()

    def sync_3d_preview(self):
        """Sincroniza os sprites atuais com o preview 3D"""
        if self.extractor.sprites:
            self.preview_3d_tab.set_sprites(self.extractor.sprites)

    def set_sprite_view(self, index, view_type):
        """Define o tipo de vista de um sprite manualmente"""
        sprite = self.extractor.get_sprite(index)
        if sprite:
            sprite.view_type = view_type
            self.update_sprite_list()
            self.sync_3d_preview() # Sincronizar se estiver no modo manual

    def set_custom_view(self, index):
        """Abre diálogo para definir vista customizada"""
        from PyQt6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, "Custom View", "Nome da vista:")
        if ok and text:
            self.set_sprite_view(index, text.lower().replace(" ", "_"))

    def on_sprite_selected(self):
        """Callback quando um sprite é selecionado na lista"""
        selected_items = self.sprites_list.selectedItems()
        if selected_items:
            item = selected_items[0]
            self.selected_sprite_index = item.data(Qt.ItemDataRole.UserRole)
            self.edit_group.setEnabled(True)
        else:
            self.selected_sprite_index = -1
            self.edit_group.setEnabled(False)
        
        self.display_image(show_boxes=True)

    def rotate_selected_sprite(self, angle):
        """Rotaciona o sprite selecionado"""
        if self.selected_sprite_index != -1:
            sprite = self.extractor.get_sprite(self.selected_sprite_index)
            if sprite:
                sprite.rotation = angle
                self.update_sprite_list()
                self.sync_3d_preview()

    def set_selected_sprite_view(self, view_type):
        """Define o tipo de vista para o sprite selecionado"""
        if self.selected_sprite_index != -1:
            self.set_sprite_view(self.selected_sprite_index, view_type)
    
    def on_image_clicked(self, x, y):
        """Callback quando a imagem é clicada"""
        # Procurar qual sprite contém as coordenadas (x, y)
        found_index = -1
        for sprite in self.extractor.sprites:
            sx, sy, sw, sh = sprite.bbox
            if sx <= x <= sx + sw and sy <= y <= sy + sh:
                found_index = sprite.index
                break
        
        if found_index != -1:
            # Selecionar na lista (isso disparará on_sprite_selected)
            for i in range(self.sprites_list.count()):
                item = self.sprites_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == found_index:
                    self.sprites_list.setCurrentItem(item)
                    break
        else:
            # Limpar seleção se clicar fora
            self.sprites_list.clearSelection()
            self.selected_sprite_index = -1
            self.edit_group.setEnabled(False)
            self.display_image(show_boxes=True)
    
    def export_sprites(self):
        """Exporta sprites para arquivos individuais"""
        output_dir = QFileDialog.getExistingDirectory(
            self,
            "Selecionar Pasta de Saída",
            str(Path.home())
        )
        
        if output_dir:
            prefix = self.prefix_input.text() or "sprite"
            padding = self.padding_spin.value()
            uniform = self.uniform_size_check.isChecked()
            
            try:
                exported_files = self.extractor.export_sprites(
                    output_dir=output_dir,
                    prefix=prefix,
                    format="png",
                    use_view_names=True,
                    padding=padding,
                    uniform_size=uniform
                )
                
                # Criar mensagem com lista de arquivos
                file_list = "\n".join([f"  • {f.name}" for f in exported_files])
                
                QMessageBox.information(
                    self,
                    "Sucesso",
                    f"✅ {len(exported_files)} sprite(s) exportado(s)!\n\n"
                    f"Arquivos criados:\n{file_list}\n\n"
                    f"Pasta: {output_dir}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao exportar sprites:\n{str(e)}")
