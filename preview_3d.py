"""
3D Preview Widget - Visualização 3D de sprites em um cubo
"""
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtGui import QImage
import OpenGL.GL as gl
import OpenGL.GLU as glu
import numpy as np
import cv2

class SpritePreview3D(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.textures = {}
        self.rotation_x = 0
        self.rotation_y = 0
        self.last_pos = None
        self.sprite_map = {} # view_type -> np.ndarray
        self.bg_color = (0.2, 0.2, 0.2)

    def set_bg_color(self, r, g, b):
        """Define a cor de fundo do preview 3D"""
        self.bg_color = (r, g, b)
        self.makeCurrent()
        gl.glClearColor(r, g, b, 1.0)
        self.update()

    def set_sprites(self, sprites):
        """Atualiza os sprites para o cubo"""
        self.sprite_map = {s.view_type: s for s in sprites}
        self.update()

    def initializeGL(self):
        gl.glClearColor(*self.bg_color, 1.0)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glEnable(gl.GL_TEXTURE_2D)

    def resizeGL(self, w, h):
        gl.glViewport(0, 0, w, h)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        glu.gluPerspective(45, w / h, 0.1, 100.0)
        gl.glMatrixMode(gl.GL_MODELVIEW)

    def paintGL(self):
        try:
            gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
            gl.glLoadIdentity()
            gl.glTranslatef(0.0, 0.0, -5.0)
            gl.glRotatef(self.rotation_x, 1, 0, 0)
            gl.glRotatef(self.rotation_y, 0, 1, 0)

            self._draw_cube()
        except Exception as e:
            # Log error but don't crash - OpenGL errors can be transient
            print(f"[3D Preview] OpenGL error: {e}")

    def _draw_cube(self):
        # Mapeamento do cubo: faces (Front, Back, Left, Right, Top, Bottom)
        # Ordem dos vértices: Bottom-Left, Bottom-Right, Top-Right, Top-Left (visto de fora)
        faces = [
            ('front',  [(-1, -1,  1), ( 1, -1,  1), ( 1,  1,  1), (-1,  1,  1)]),
            ('back',   [( 1, -1, -1), (-1, -1, -1), (-1,  1, -1), ( 1,  1, -1)]),
            ('left',   [(-1, -1, -1), (-1, -1,  1), (-1,  1,  1), (-1,  1, -1)]),
            ('right',  [( 1, -1,  1), ( 1, -1, -1), ( 1,  1, -1), ( 1,  1,  1)]),
            ('top',    [(-1,  1,  1), ( 1,  1,  1), ( 1,  1, -1), (-1,  1, -1)]),
            ('bottom', [(-1, -1, -1), ( 1, -1, -1), ( 1, -1,  1), (-1, -1,  1)]),
        ]

        for view_type, coords in faces:
            self._update_texture(view_type)
            gl.glBegin(gl.GL_QUADS)
            gl.glTexCoord2f(0, 1); gl.glVertex3fv(coords[0])
            gl.glTexCoord2f(1, 1); gl.glVertex3fv(coords[1])
            gl.glTexCoord2f(1, 0); gl.glVertex3fv(coords[2])
            gl.glTexCoord2f(0, 0); gl.glVertex3fv(coords[3])
            gl.glEnd()

    def _update_texture(self, view_type):
        """Carrega ou atualiza textura para uma face"""
        if view_type in self.sprite_map:
            sprite = self.sprite_map[view_type]
            img = sprite.image.copy()
            
            # Aplicar rotação se houver
            if sprite.rotation != 0:
                if sprite.rotation == 90:
                    img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
                elif sprite.rotation == 180:
                    img = cv2.rotate(img, cv2.ROTATE_180)
                elif sprite.rotation == 270:
                    img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
            
            # Converter para RGBA se necessário
            if img.shape[2] == 3:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)
            elif img.shape[2] == 4:
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA)
            
            h, w = img.shape[:2]
            
            # Gerar ID de textura se não existir
            if view_type not in self.textures:
                self.textures[view_type] = gl.glGenTextures(1)
            
            gl.glBindTexture(gl.GL_TEXTURE_2D, self.textures[view_type])
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, w, h, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, img)
        else:
            # Bind textura vazia (cinza)
            gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

    def mousePressEvent(self, event):
        self.last_pos = event.position()

    def mouseMoveEvent(self, event):
        if self.last_pos:
            diff = event.position() - self.last_pos
            self.rotation_y += diff.x()
            self.rotation_x += diff.y()
            self.last_pos = event.position()
            self.update()
