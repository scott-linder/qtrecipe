#!/usr/bin/python3

import sys
import os
from os import listdir, chdir
from os.path import isdir, isfile, join
from shutil import move
from PyQt4 import QtCore, QtGui, uic

class Catagory(QtGui.QTreeWidgetItem):

    """Thin wrappers around directories which "contain" recipes."""

    def __init__(self, name):
        self.name = name
        super().__init__([self.name])

    def path(self):
        return self.name + os.sep


class Recipe(QtGui.QTreeWidgetItem):

    # File extension for recipe files
    EXT = '.recipe'
    BACKUP_EXT = '.backup'
    INGREDIENT_LENGTH = 3

    def __init__(self, catagory, title):
        self.catagory = catagory

        self.title = title
        self.author = ''
        self.directions = ''
        self.details = {
                'oven_temp' : '',
                'bake_time' : '',
                'yields'    : '',
                'prep_time' : '',
                }
        self.picture = ''
        self.ingredients = []
        super().__init__([self.title])

    def path(self):
        return join(self.catagory.path(), self.title + self.EXT)

    def parse_file(self):

        """Read form file and parse."""

        print("Parsing: " + self.path())

        sections = { 
                '<Title>'       : 'title',
                '<Ingredients>' : 'ingredients',
                '<directions>'  : 'directions',
                '<details>'     : 'details',
                '<author>'      : 'author',
                '<pic>'         : 'pic'
                }
        detail_order = ['oven_temp', 'bake_time', 'yields', 'prep_time']
        current_detail = 0
        current_ingredient_part = 0

        with open(self.path(), mode='rt') as f:
            for line in f:
                # Newlines mess up our UI when displayed in most widgets
                line = line.rstrip('\n\r')
                if line in sections:
                    # Note what we are looking for with the next line
                    section = sections[line]
                else:
                    if line == '<end>':
                        continue

                    if section == 'title':
                        self.title = line;
                    elif section == 'ingredients':
                        # If current ingredient is full, start on a new one
                        if len(self.ingredients) == 0 or current_ingredient_part == self.INGREDIENT_LENGTH:
                            self.ingredients.append(['','',''])
                            current_ingredient_part = 0
                        self.ingredients[-1][current_ingredient_part] = line
                        current_ingredient_part += 1
                    elif section == 'directions':
                        self.directions += line + '\n'
                    elif section == 'details':
                        if current_detail < len(self.details):
                            self.details[detail_order[current_detail]] = line
                            current_detail += 1
                    elif section == 'author':
                        self.author = line
                    elif section == 'pic':
                        self.pic = line
        self.setText(0, self.title)

    def encode_file(self):

        """Encode and write to file."""

        # Dont't allow duplicates (filesystem will overwrite the other recipe)
        for i in range(self.catagory.childCount()):
            recipe = self.catagory.child(i)
            if recipe != self and recipe.text(0) == self.title:
                return False

        # Make a backup just in case
        if isfile(self.path()):
            print("Backup: " + self.path() + self.BACKUP_EXT)
            move(self.path(), self.path() + self.BACKUP_EXT)

        print("Encoding: " + self.path())
        with open(self.path(), mode='w') as f:
            f.write("<Title>\n")
            f.write(self.title)
            f.write("\n<Ingredients>\n")
            for ingredient in self.ingredients:
                print(ingredient)
                for part in ingredient:
                    print("\t" + part)
                    f.write(part + "\n")
            f.write("\n<end>\n")
            f.write("<directions>\n")
            f.write(self.directions)
            f.write("\n<end>\n")
            f.write("<author>\n")
            f.write(self.author)
            f.write("\n<details>\n")
            f.write(self.details['oven_temp'] + "\n")
            f.write(self.details['bake_time'] + "\n")
            f.write(self.details['yields'] + "\n")
            f.write(self.details['prep_time'] + "\n")
            f.write("\n<pic>\n")
            f.write("foobar")
            f.write("\n<notes>\n")
        self.setText(0, self.title)
        return True

class RecipeWindow(QtGui.QMainWindow):

    ROOT = './recipes'

    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        ui = uic.loadUi("recipe.ui", self)
        chdir(self.ROOT)
        self._populate_recipes()

        # Variables
        self.editing = False

        # Recipe list
        self.recipes.sortItems(0, QtCore.Qt.AscendingOrder)
        self.recipes.setSortingEnabled(True)
        self.recipes.itemClicked.connect(self.toggle_catagory_expand)
        self.recipes.currentItemChanged.connect(self.item_selected)

        # All the buttons and their handlers
        self.edit_button.clicked.connect(self.start_edit)
        self.save_button.clicked.connect(self.save_edit)
        self.cancel_button.clicked.connect(self.cancel_edit)
        self.new_recipe_button.clicked.connect(self.new_recipe)
        self.new_ingredient_button.clicked.connect(self.new_ingredient)
        self.delete_ingredient_button.clicked.connect(self.delete_ingredient)

        self._set_editing(False)


    def _populate_recipes(self):
        for catagory_fname in [fname for fname in listdir() if isdir(fname)]:
            catagory = Catagory(catagory_fname.strip(os.sep))
            self.recipes.addTopLevelItem(catagory)
            for recipe_fname in [fname for fname in listdir(catagory_fname)
                        if isfile(join(catagory_fname, fname))]:
                if recipe_fname.endswith(Recipe.EXT):
                    title = recipe_fname[:-len(Recipe.EXT)]
                    recipe = Recipe(catagory, title)
                    recipe.parse_file()
                    catagory.addChild(recipe)

    def _ui_to_recipe(self, recipe):
        """Populates instance of Recipe from UI elements."""
        if self.editing:
            raise Exception("Cannot create a Recipe, user is editing.")
        if not isinstance(recipe, Recipe):
            raise Exception("Cannot create a Recipe, catagory is selected.")
        # Copy all UI data into Recipe object
        recipe.title = self.title.text()
        recipe.author = self.author.text()
        recipe.details['oven_temp'] = self.oven_temp.text()
        recipe.details['bake_time'] = self.bake_time.text()
        recipe.details['yields']    = self.yields.text()
        recipe.details['prep_time'] = self.prep_time.text()
        recipe.directions = self.directions.toPlainText()
        recipe.ingredients[:] = []
        for row in range(self.ingredients.topLevelItemCount()):
            ingredient = self.ingredients.topLevelItem(row)
            ingredient_list = []
            for column in range(ingredient.columnCount()):
                ingredient_list.append(ingredient.text(column))
            recipe.ingredients.append(ingredient_list)
        return recipe

    def _recipe_to_ui(self, recipe):
        """Populates UI elements from an instance of Recipe."""
        if self.editing:
            raise Exception("Cannot load UI from Recipe, user is editing.")
        if not isinstance(recipe, Recipe):
            raise Exception("Cannot load UI from Recipe, must be instance of Recipe.")
        self.title.setText(recipe.title)
        self.author.setText(recipe.author)
        self.oven_temp.setText(recipe.details['oven_temp'])
        self.bake_time.setText(recipe.details['bake_time'])
        self.yields.setText(recipe.details['yields'])
        self.prep_time.setText(recipe.details['prep_time'])
        self.directions.setText(recipe.directions)
        self.ingredients.clear()
        for ingredient in recipe.ingredients:
            ingredient = QtGui.QTreeWidgetItem(ingredient)
            self.ingredients.addTopLevelItem(ingredient)

    def _set_editing(self, editing):
        """Modifies UI to allow/disallow editing."""
        LABELS = [self.title, self.author, self.oven_temp, self.bake_time,
                  self.yields, self.prep_time]
        EDITS = [self.title_edit, self.author_edit, self.oven_temp_edit,
                 self.bake_time_edit, self.yields_edit, self.prep_time_edit]
        self.editing = editing
        # Copy text to/from labels/edits and set visibliy based on new editing
        # state
        for label, edit in zip(LABELS, EDITS):
            if self.editing:
                edit.setText(label.text())
                edit.show()
                label.hide()
            else:
                label.setText(edit.text())
                label.show()
                edit.hide()
        # Same for directions
        self.directions.setReadOnly(not self.editing)
        # Now set whether ingredients are editable
        for i in range(self.ingredients.topLevelItemCount()):
            ingredient = self.ingredients.topLevelItem(i)
            if self.editing:
                ingredient.setFlags(ingredient.flags() 
                                    | QtCore.Qt.ItemIsEditable)
            else:
                ingredient.setFlags(ingredient.flags()
                                    & ~QtCore.Qt.ItemIsEditable)
        # Now set whether recipes can be selected
        self.recipes.setEnabled(not self.editing)
        # Now set which buttons are displayed
        self.edit_button.setVisible(not self.editing)
        self.save_button.setVisible(self.editing)
        self.cancel_button.setVisible(self.editing)
        self.new_ingredient_button.setEnabled(self.editing)
        self.delete_ingredient_button.setEnabled(self.editing)

    def _duplicate_title_dialog(self):
        QtGui.QMessageBox.warning(self, 'Duplicate Recipe Title',
                'A recipe in this category already has the title "' 
                + self.title.text() + '"', None, None)

    #
    # Click Handlers
    #

    def toggle_catagory_expand(self, item):
        if isinstance(item, Catagory):
            item.setExpanded(not item.isExpanded())

    def item_selected(self, item):
        if isinstance(item, Recipe):
            self.new_recipe_button.setEnabled(False)
            self.edit_button.setEnabled(True)
            self._recipe_to_ui(item)
        elif isinstance(item, Catagory):
            self.new_recipe_button.setEnabled(True)
            self.edit_button.setEnabled(False)
            self._recipe_to_ui(Recipe('', ''))
        else:
            raise Exception('Selected item is of invalid type ' + type(item))

    def start_edit(self):
        self._set_editing(True)

    def save_edit(self):
        current = self.recipes.currentItem()
        self._set_editing(False)
        if self.title.text() != current.title:
            # Name changed, forget old file before making the new one
            print("Backup: " + current.path() + Recipe.BACKUP_EXT)
            move(current.path(), current.path() + Recipe.BACKUP_EXT)
        self._ui_to_recipe(self.recipes.currentItem())
        if not self.recipes.currentItem().encode_file():
            # Woops, the user shouldn't stop editing until recipe has unique
            # title
            self._set_editing(True)
            self._duplicate_title_dialog()

    def cancel_edit(self):
        current = self.recipes.currentItem()
        self._set_editing(False)
        self._recipe_to_ui(current)

    def new_recipe(self):
        catagory = self.recipes.currentItem()
        if isinstance(catagory, Catagory):
            recipe = Recipe(catagory, '')
            if recipe.encode_file():
                catagory.addChild(recipe)
                self.recipes.setCurrentItem(recipe)
                self._set_editing(True)
            else:
                self._duplicate_title_dialog()
        else:
            raise Exception('Cannot create new recipe without catagory selected.')

    def new_ingredient(self):
        ingredient = QtGui.QTreeWidgetItem(['','',''])
        ingredient.setFlags(ingredient.flags() | QtCore.Qt.ItemIsEditable)
        selected = self.ingredients.currentItem()
        if selected:
            index = self.ingredients.indexOfTopLevelItem(selected)
            self.ingredients.insertTopLevelItem(index + 1, ingredient)
        else:
            self.ingredients.addTopLevelItem(ingredient)
        self.ingredients.setCurrentItem(ingredient)

    def delete_ingredient(self):
        selected = self.ingredients.currentItem()
        index = self.ingredients.indexOfTopLevelItem(selected)
        self.ingredients.takeTopLevelItem(index)

    # Called whenever the window is asked to close
    def closeEvent(self, event):
        if self.editing:
            option = QtGui.QMessageBox.warning(self, "Warning", 
                    "About to lose changes to current recipe!",
                    QtGui.QMessageBox.Save | QtGui.QMessageBox.Discard |
                    QtGui.QMessageBox.Cancel, QtGui.QMessageBox.Save)
            if option == QtGui.QMessageBox.Save:
                if not self.recipes.currentItem().encode_file():
                    event.ignore()
                    self._duplicate_title_dialog()
            elif option == QtGui.QMessageBox.Cancel:
                event.ignore()
            elif option == QtGui.QMessageBox.Discard:
                event.accept()
        else:
            event.accept()


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    win = RecipeWindow()
    win.show()
    app.exec()

