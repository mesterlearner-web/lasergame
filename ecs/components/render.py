from ecs.component import Component


class Render(Component):
    """اطلاعات لازم برای رسم -- خودِ رسم را RenderSystem انجام می‌دهد،
    این کامپوننت فقط داده نگه می‌دارد."""
    __slots__ = ('texture', 'color', 'scale', 'rotation', 'opacity', 'shape', 'size')

    def __init__(self, texture=None, color=(1.0, 1.0, 1.0, 1.0), scale=1.0,
                 rotation=0.0, opacity=1.0, shape='circle', size=(20.0, 20.0)):
        self.texture = texture
        self.color = color
        self.scale = scale
        self.rotation = rotation
        self.opacity = opacity
        self.shape = shape  # 'circle' | 'rect' | 'line'
        self.size = size
