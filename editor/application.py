
from functools import partial
from PySide2 import QtWidgets

from . import templates
from .editarea import ShapeEditArea
from .menu import MenuWidget
from .attributes import AttributeEditor
from hotbox_designer.managers import CopyManager, UndoManager, copy_hotbox_data
from hotbox_designer.interactive import Shape
from hotbox_designer.geometry import get_combined_rects
from hotbox_designer.utils import (
    move_elements_to_array_end, move_elements_to_array_begin,
    move_up_array_elements, move_down_array_elements)


class HotboxEditor(QtWidgets.QWidget):
    def __init__(self, options, parent=None):
        super(HotboxEditor, self).__init__(parent)
        self.options = options

        self.shape_editor = ShapeEditArea(options)
        self.shape_editor.selectedShapesChanged.connect(self.selection_changed)
        self.shape_editor.centerMoved.connect(self.move_center)

        self.undo_manager = UndoManager(self.hotbox_data(), copy_hotbox_data)

        self.menu = MenuWidget()
        self.menu.deleteRequested.connect(self.delete_selection)
        self.menu.sizeChanged.connect(self.editor_size_changed)
        self.menu.editCenterToggled.connect(self.edit_center_mode_changed)
        self.menu.useSnapToggled.connect(self.use_snap)
        self.menu.snapValuesChanged.connect(self.snap_value_changed)
        self.menu.centerValuesChanged.connect(self.move_center)
        self.menu.set_size_values(options['width'], options['height'])
        self.menu.set_center_values(options['centerx'], options['centery'])
        self.menu.undoRequested.connect(self.undo)
        self.menu.redoRequested.connect(self.redo)
        method = partial(self.create_shape, templates.SQUARE_BUTTON)
        self.menu.addButtonRequested.connect(method)
        method = partial(self.create_shape, templates.TEXT)
        self.menu.addTextRequested.connect(method)
        method = partial(self.create_shape, templates.BACKGROUND, before=True)
        self.menu.addBackgroundRequested.connect(method)
        method = self.set_selection_move_down
        self.menu.moveDownRequested.connect(method)
        method = self.set_selection_move_up
        self.menu.moveUpRequested.connect(method)
        method = self.set_selection_on_top
        self.menu.onTopRequested.connect(method)
        method = self.set_selection_on_bottom
        self.menu.onBottomRequested.connect(method)

        self.attribute_editor = AttributeEditor()
        self.attribute_editor.optionSet.connect(self.option_set)
        self.attribute_editor.rectModified.connect(self.rect_modified)
        self.attribute_editor.imageModified.connect(self.image_modified)

        self.hlayout = QtWidgets.QHBoxLayout()
        self.hlayout.setContentsMargins(0, 0, 0, 0)
        self.hlayout.addStretch(1)
        self.hlayout.addWidget(self.shape_editor)
        self.hlayout.addStretch(1)
        self.hlayout.addWidget(self.attribute_editor)

        self.vlayout = QtWidgets.QVBoxLayout(self)
        self.vlayout.setContentsMargins(0, 0, 0, 0)
        self.vlayout.setSpacing(0)
        self.vlayout.addWidget(self.menu)
        self.vlayout.addLayout(self.hlayout)

    def undo(self):
        self.undo_manager.undo()
        data = self.undo_manager.data
        print(data)
        self.set_hotbox_data(data)

    def redo(self):
        self.undo_manager.redo()
        data = self.undo_manager.data
        print(data)
        self.set_hotbox_data(data)

    def use_snap(self, state):
        snap = self.menu.snap_values() if state else None
        self.shape_editor.transform.snap = snap
        self.shape_editor.repaint()

    def snap_value_changed(self):
        self.shape_editor.transform.snap = self.menu.snap_values()
        self.undo_manager.set_data_modified(self.hotbox_data())
        self.shape_editor.repaint()

    def edit_center_mode_changed(self, state):
        self.shape_editor.edit_center_mode = state
        self.shape_editor.repaint()

    def option_set(self, option, value):
        for shape in self.shape_editor.selection:
            shape.options[option] = value
        self.shape_editor.repaint()
        self.undo_manager.set_data_modified(self.hotbox_data())

    def editor_size_changed(self):
        size = self.menu.get_size()
        self.shape_editor.setFixedSize(size)
        self.undo_manager.set_data_modified(self.hotbox_data())

    def move_center(self, x, y):
        self.options['centerx'] = x
        self.options['centery'] = y
        self.menu.set_center_values(x, y)
        self.shape_editor.repaint()

    def rect_modified(self, option, value):
        shapes = self.shape_editor.selection
        for shape in shapes:
            shape.options[option] = value
            if option == 'shape.height':
                shape.rect.setHeight(value)
                continue
            elif option == 'shape.width':
                shape.rect.setWidth(value)
                continue

            width = shape.rect.width()
            height = shape.rect.height()
            if option == 'shape.left':
                shape.rect.setLeft(value)
            else:
                shape.rect.setTop(value)
            shape.rect.setWidth(width)
            shape.rect.setHeight(height)

        rects = [shape.rect for shape in self.shape_editor.selection]
        rect = get_combined_rects(rects)
        self.shape_editor.manipulator.set_rect(rect)
        self.shape_editor.repaint()

    def selection_changed(self):
        shapes = self.shape_editor.selection
        options = [shape.options for shape in shapes]
        self.attribute_editor.set_options(options)

    def create_shape(self, template, before=False):
        options = template.copy()
        shape = Shape(options)
        shape.rect.moveCenter(self.shape_editor.rect().center())
        shape.synchronize_rect()
        if before is True:
            self.shape_editor.shapes.insert(0, shape)
        else:
            self.shape_editor.shapes.append(shape)
        self.shape_editor.repaint()
        self.undo_manager.set_data_modified(self.hotbox_data())

    def image_modified(self):
        for shape in self.shape_editor.selection:
            shape.synchronize_image()
        self.shape_editor.repaint()

    def set_selection_move_down(self):
        array = self.shape_editor.shapes
        elements = self.shape_editor.selection
        move_down_array_elements(array, elements)
        self.shape_editor.repaint()
        self.undo_manager.set_data_modified(self.hotbox_data())

    def set_selection_move_up(self):
        array = self.shape_editor.shapes
        elements = self.shape_editor.selection
        move_up_array_elements(array, elements)
        self.shape_editor.repaint()
        self.undo_manager.set_data_modified(self.hotbox_data())

    def set_selection_on_top(self):
        array = self.shape_editor.shapes
        elements = self.shape_editor.selection
        self.shape_editor.shapes = move_elements_to_array_end(array, elements)
        self.shape_editor.repaint()
        self.undo_manager.set_data_modified(self.hotbox_data())

    def set_selection_on_bottom(self):
        array = self.shape_editor.shapes
        elements = self.shape_editor.selection
        shapes = move_elements_to_array_begin(array, elements)
        self.shape_editor.shapes = shapes
        self.shape_editor.repaint()
        self.undo_manager.set_data_modified(self.hotbox_data())

    def delete_selection(self):
        for shape in self.shape_editor.selection:
            self.shape_editor.shapes.remove(shape)
            self.shape_editor.selection.remove(shape)
        rects = [shape.rect for shape in self.shape_editor.selection]
        rect = get_combined_rects(rects)
        self.shape_editor.manipulator.set_rect(rect)
        self.shape_editor.repaint()
        self.undo_manager.set_data_modified(self.hotbox_data())

    def hotbox_data(self):
        return {
            'general': self.options,
            'shapes': [shape.options for shape in self.shape_editor.shapes]}

    def set_hotbox_data(self, hotbox_data):
        self.shape_editor.options = hotbox_data['general']
        shapes = []
        for options in hotbox_data['shapes']:
            shape = Shape(options)
            shape.rect.moveCenter(self.shape_editor.rect().center())
            shape.synchronize_rect()
            shapes.append(shape)
        self.shape_editor.shapes = shapes
        self.shape_editor.manipulator.rect = None
        self.shape_editor.repaint()


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    widget = HotboxEditor(templates.HOTBOX.copy())
    widget.show()
    app.exec_()