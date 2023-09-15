from os import getlogin, makedirs, environ, remove
from sys import argv, exit
from re import compile
from shutil import move, rmtree, copy
from datetime import datetime
from pathlib import Path
from requests import get
from subprocess import check_output
from webbrowser import open as webopen
from yaml import safe_load as yaml_safe_load
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QRadioButton,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QTextEdit,
    QScrollArea,
    QMessageBox,
    QLineEdit,
    QFileDialog,
    QButtonGroup,
)


class ModdingHelperApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setGeometry(100, 100, 940, 800)  # x, y, width, height
        self.setFixedSize(self.size())

        self.nvidia_radio_yes = QRadioButton(
            'Yes, I have an active NVIDIA graphics card.'
        )
        self.nvidia_radio_no = QRadioButton(
            'No, I have a different graphics card or integrated graphics.'
        )

        self.nvidia_radio_group = QButtonGroup()
        self.nvidia_radio_group.addButton(self.nvidia_radio_yes)
        self.nvidia_radio_group.addButton(self.nvidia_radio_no)

        try:
            check_output('nvidia-smi')
            self.nvidia_radio_yes.setChecked(True)
        except Exception:
            self.nvidia_radio_no.setChecked(True)
        self.nvidia_radio_yes.toggled.connect(self.on_nvidia_radio_yes)
        self.nvidia_radio_no.toggled.connect(self.on_nvidia_radio_no)

        self.mod_checkboxes = list()
        for mod in modlist_data['ui']:
            fancy_name = mod['name']
            checkbox = QtWidgets.QCheckBox(fancy_name)
            checkbox.setToolTip(
                f'Description: {mod["description"]}\nWebsite: {mod["website_url"]}'
            )
            checkbox.installEventFilter(self)
            self.mod_checkboxes.append(checkbox)
        revert_button = QPushButton('Revert to last backup')
        install_button = QPushButton('Install mods')
        backup_checkbox = self.backup_checkbox = QtWidgets.QCheckBox(
            'Backup current mods before installing'
        )
        backup_checkbox.setChecked(True)

        self.minecraft_dir_label = QLabel('Minecraft Directory:')
        default_minecraft_dir = f'C:\\Users\\{getlogin()}\\AppData\\Roaming\\.minecraft'
        self.minecraft_dir_text = QLineEdit(default_minecraft_dir)
        self.minecraft_dir_browse_button = QPushButton('Browse')

        button_layout = QHBoxLayout()
        button_layout.addWidget(revert_button)
        button_layout.addWidget(install_button)
        button_layout.addWidget(self.backup_checkbox)

        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.minecraft_dir_label)
        dir_layout.addWidget(self.minecraft_dir_text)
        dir_layout.addWidget(self.minecraft_dir_browse_button)

        checkbox_layout = QVBoxLayout()
        for i in range(0, len(self.mod_checkboxes), 5):
            row_layout = QHBoxLayout()
            for j in range(5):
                if i + j < len(self.mod_checkboxes):
                    row_layout.addWidget(self.mod_checkboxes[i + j])
            checkbox_layout.addLayout(row_layout)
        checkbox_container_layout = QVBoxLayout()
        checkbox_container_layout.addLayout(checkbox_layout)
        checkbox_container_layout.addSpacing(20)

        select_deselect_layout = QHBoxLayout()
        deselect_all_button = QPushButton('Deselect all')
        select_all_button = QPushButton('Select all')
        select_deselect_layout.addWidget(deselect_all_button)
        select_deselect_layout.addWidget(select_all_button)

        vbox = QVBoxLayout()
        vbox.addWidget(QLabel('<b>Modding Helper</b>'))
        vbox.addSpacing(10)
        vbox.addWidget(
            QLabel('Does your computer have an active NVIDIA graphics card?')
        )
        vbox.addWidget(self.nvidia_radio_yes)
        vbox.addWidget(self.nvidia_radio_no)
        vbox.addSpacing(20)
        vbox.addWidget(
            QLabel(
                'Select the extra mods you want to install (optimization mods will be installed automatically):'
            )
        )
        vbox.addLayout(select_deselect_layout)
        vbox.addLayout(checkbox_container_layout)
        vbox.addLayout(dir_layout)
        vbox.addSpacing(20)
        vbox.addLayout(button_layout)

        self.console_textedit = QTextEdit()
        self.console_textedit.setReadOnly(True)
        self.console_textedit.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)

        console_scrollarea = QScrollArea()
        console_scrollarea.setWidgetResizable(True)
        console_scrollarea.setWidget(self.console_textedit)
        console_scrollarea.setMaximumHeight(150)

        vbox.addWidget(console_scrollarea)

        central_widget = QWidget()
        central_widget.setLayout(vbox)
        self.setCentralWidget(central_widget)

        revert_button.clicked.connect(self.show_revert_popup)
        install_button.clicked.connect(self.install_mods)
        deselect_all_button.clicked.connect(self.deselect_all)
        select_all_button.clicked.connect(self.select_all)
        self.minecraft_dir_browse_button.clicked.connect(self.browse_minecraft_dir)

        # Initial terminal message
        print('Modding Helper [v1.0.0] by @henrique-coder (GitHub)')
        print('Modding Helper is not affiliated with any mod or modding community.')
        print(
            'Modding Helper is not responsible for any damage caused to your computer or Minecraft installation.'
        )
        print(
            'The mods are downloaded from Modrinth, all from version 1.20.1 (Fabric) and are always up to date.'
        )
        print(
            'Backup your current mods before installing new mods (highly recommended).'
        )
        print(
            'If you have any problems, please contact the mod author by opening a issue in GitHub, have a nice modding!'
        )
        self.update_console('Modding Helper [v1.0.0] by @henrique-coder (GitHub)')
        self.update_console(
            'Modding Helper is not affiliated with any mod or modding community.'
        )
        self.update_console(
            'Modding Helper is not responsible for any damage caused to your computer or Minecraft installation.'
        )
        self.update_console(
            'The mods are downloaded from Modrinth, all from version 1.20.1 (Fabric) and are always up to date.'
        )
        self.update_console(
            'Backup your current mods before installing new mods (highly recommended).'
        )
        self.update_console(
            'If you have any problems, please contact the mod author, have a nice modding!'
        )

    def get_modrinth_project_info(self, modrinth_slug_name: str):
        mod_loader = 'fabric'
        mod_version = '1.20.1'
        project_call = f'https://api.modrinth.com/v2/project/{modrinth_slug_name}/version?loaders=["{mod_loader}"]&game_versions=["{mod_version}"]'
        project_resp = get(project_call, allow_redirects=True)
        project_data = project_resp.json()

        if not project_data:
            return None
        mod_filename = project_data[0]['files'][0]['filename']
        mod_download_url = project_data[0]['files'][0]['url']
        return mod_filename, mod_download_url

    def show_revert_popup(self):
        makedirs('.backups', exist_ok=True)
        backup_folder_regex = compile(r'\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}\.\d{6}')
        backup_folders = [
            folder
            for folder in Path('.backups').iterdir()
            if backup_folder_regex.match(folder.name)
        ]
        if not backup_folders:
            print('No backups found!')
            self.update_console('No backups found!')
            QMessageBox.critical(
                self,
                'Error',
                'No backups found!',
                QMessageBox.Ok,
                QMessageBox.Ok,
            )
            return
        reply = QMessageBox.question(
            self,
            'Warning',
            'Are you sure you want to revert mods to last backup?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            minecraft_dir = self.minecraft_dir_text.text()
            latest_backup = sorted(backup_folders)[-1]
            for file in Path(minecraft_dir, 'mods').iterdir():
                remove(file)
            for file in latest_backup.iterdir():
                move(file, Path(minecraft_dir, 'mods'))
            rmtree(latest_backup)
            print(f'Mods reverted to the lastest backup! ({latest_backup.name})')
            self.update_console(
                f'Mods reverted to the lastest backup! ({latest_backup.name})'
            )

    def install_mods(self):
        selected_mods = [
            checkbox.text() for checkbox in self.mod_checkboxes if checkbox.isChecked()
        ]
        backup_selected = self.backup_checkbox.isChecked()
        minecraft_dir = self.minecraft_dir_text.text()

        # TODO: asyncronous install
        # self.nvidia_radio_yes.setEnabled(False)
        # self.nvidia_radio_no.setEnabled(False)
        # self.deselect_all_button.setEnabled(False)
        # self.select_all_button.setEnabled(False)
        # for checkbox in self.mod_checkboxes:
        #     checkbox.setEnabled(False)
        # self.minecraft_dir_text.setEnabled(False)
        # self.minecraft_dir_browse_button.setEnabled(False)
        # self.revert_button.setEnabled(False)
        # self.install_button.setEnabled(False)
        # self.backup_checkbox.setEnabled(False)

        print('Downloading mods...')
        self.update_console('Downloading mods...')

        if backup_selected:
            now_time_formatted = datetime.now().strftime("%Y.%m.%d-%H.%M.%S.%f")
            makedirs(Path(f'.backups/{now_time_formatted}'), exist_ok=True)
            for file in Path(minecraft_dir, 'mods').iterdir():
                copy(file, Path('.backups', now_time_formatted))
        these_mod_filenames = list()

        for mod in modlist_data['mod_libs']:
            mod_filename, mod_download_url = self.get_modrinth_project_info(mod['slug'])
            these_mod_filenames.append(mod_filename)
            if Path(minecraft_dir, 'mods', mod_filename).exists():
                print(f'Mod {mod["name"]} is already installed!')
                self.update_console(f'Mod {mod["name"]} is already installed!')
                continue
            if not mod_filename or not mod_download_url:
                print(f'Error downloading mod: {mod["name"]}')
                self.update_console(f'Error downloading mod: {mod["name"]}')
                continue
            with open(Path(minecraft_dir, 'mods', mod_filename), 'wb') as mod_file:
                mod_file.write(get(mod_download_url, allow_redirects=True).content)
            print(f'Mod {mod["name"]} was successfully installed!')
            self.update_console(f'Mod {mod["name"]} was successfully installed!')
        if self.nvidia_radio_yes.isChecked():
            for mod in modlist_data['nvidia_gpu']:
                mod_filename, mod_download_url = self.get_modrinth_project_info(
                    mod['slug']
                )
                these_mod_filenames.append(mod_filename)
                if Path(minecraft_dir, 'mods', mod_filename).exists():
                    print(f'Mod {mod["name"]} is already installed!')
                    self.update_console(f'Mod {mod["name"]} is already installed!')
                    continue
                if not mod_filename or not mod_download_url:
                    print(f'Error downloading mod: {mod["name"]}')
                    self.update_console(f'Error downloading mod: {mod["name"]}')
                    continue
                with open(Path(minecraft_dir, 'mods', mod_filename), 'wb') as mod_file:
                    mod_file.write(get(mod_download_url, allow_redirects=True).content)
                print(f'Mod {mod["name"]} was successfully installed!')
                self.update_console(f'Mod {mod["name"]} was successfully installed!')
        for mod in modlist_data['optimization']:
            mod_filename, mod_download_url = self.get_modrinth_project_info(mod['slug'])
            these_mod_filenames.append(mod_filename)
            if Path(minecraft_dir, 'mods', mod_filename).exists():
                print(f'Mod {mod["name"]} is already installed!')
                self.update_console(f'Mod {mod["name"]} is already installed!')
                continue
            if not mod_filename or not mod_download_url:
                print(f'Error downloading mod: {mod["name"]}')
                self.update_console(f'Error downloading mod: {mod["name"]}')
                continue
            with open(Path(minecraft_dir, 'mods', mod_filename), 'wb') as mod_file:
                mod_file.write(get(mod_download_url, allow_redirects=True).content)
            print(f'Mod {mod["name"]} was successfully installed!')
            self.update_console(f'Mod {mod["name"]} was successfully installed!')
        for mod in modlist_data['ui']:
            if mod['name'] in selected_mods:
                mod_filename, mod_download_url = self.get_modrinth_project_info(
                    mod['slug']
                )
                these_mod_filenames.append(mod_filename)
                if Path(minecraft_dir, 'mods', mod_filename).exists():
                    print(f'Mod {mod["name"]} is already installed!')
                    self.update_console(f'Mod {mod["name"]} is already installed!')
                    continue
                if not mod_filename or not mod_download_url:
                    print(f'Error downloading mod: {mod["name"]}')
                    self.update_console(f'Error downloading mod: {mod["name"]}')
                    continue
                with open(Path(minecraft_dir, 'mods', mod_filename), 'wb') as mod_file:
                    mod_file.write(get(mod_download_url, allow_redirects=True).content)
                print(f'Mod {mod["name"]} was successfully installed!')
                self.update_console(f'Mod {mod["name"]} was successfully installed!')
        for file in Path(minecraft_dir, 'mods').iterdir():
            if file.name.endswith('.jar') and file.name not in these_mod_filenames:
                remove(file)
                print(f'Old mod {file.name} was successfully removed!')
                self.update_console(f'Old mod {file.name} was successfully removed!')
        # TODO: asyncronous install
        # self.nvidia_radio_yes.setEnabled(True)
        # self.nvidia_radio_no.setEnabled(True)
        # self.deselect_all_button.setEnabled(True)
        # self.select_all_button.setEnabled(True)
        # for checkbox in self.mod_checkboxes:
        #     checkbox.setEnabled(True)
        # self.minecraft_dir_text.setEnabled(True)
        # self.minecraft_dir_browse_button.setEnabled(True)
        # self.revert_button.setEnabled(True)
        # self.install_button.setEnabled(True)
        # self.backup_checkbox.setEnabled(True)

        print('All mods were successfully installed!')
        self.update_console('All mods were successfully installed!')

    def deselect_all(self):
        for checkbox in self.mod_checkboxes:
            checkbox.setChecked(False)

    def select_all(self):
        for checkbox in self.mod_checkboxes:
            checkbox.setChecked(True)

    def update_console(self, message):
        timestamp = QtCore.QDateTime.currentDateTime().toString(
            '[yyyy.MM.dd-hh:mm:ss.zzz]'
        )
        new_text = f'{timestamp} {message}'
        self.console_textedit.append(new_text)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.ContextMenu and obj in self.mod_checkboxes:
            menu = QtWidgets.QMenu(self)
            open_action = menu.addAction(f'Open {obj.text()} website')
            action = menu.exec_(event.globalPos())
            if action == open_action:
                QtGui.QDesktopServices.openUrl(
                    QtCore.QUrl(self.get_website_url_by_name(obj.text()))
                )
            return True
        return False

    def get_website_url_by_name(self, name):
        for mod in modlist_data['ui']:
            if mod['name'] == name:
                return mod['website_url']
        return None

    def browse_minecraft_dir(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, 'Select your .minecraft directory', self.minecraft_dir_text.text()
        )
        if dir_path:
            self.minecraft_dir_text.setText(dir_path)

    def on_nvidia_radio_yes(self):
        if self.nvidia_radio_no.isChecked():
            self.nvidia_radio_no.setChecked(False)
            print('OFF - Mods made for NVIDIA graphics cards will not be installed.')
            self.update_console(
                'OFF - Mods made for NVIDIA graphics cards will not be installed.'
            )

    def on_nvidia_radio_no(self):
        if self.nvidia_radio_yes.isChecked():
            self.nvidia_radio_yes.setChecked(False)
            print('ON - Mods made for NVIDIA graphics cards will be installed.')
            self.update_console(
                'ON - Mods made for NVIDIA graphics cards will be installed.'
            )


if __name__ == '__main__':
    app_version = '1.0.1'
    favicon_path = Path(environ['TEMP'], 'moddinghelper_favicon.ico')
    updater_api_base_url = 'https://raw.githubusercontent.com/Henrique-Coder/modding-helper/main/updater_api'

    if not favicon_path.exists():
        with open(favicon_path, 'wb') as favicon_file:
            favicon_file.write(
                get(
                    f'{updater_api_base_url}/favicon.ico',
                    allow_redirects=True,
                ).content
            )
    modlist_path = Path(environ['TEMP'], 'moddinghelper_modlist.yaml')
    if modlist_path.exists():
        latest_modlist_version = str(
            get(
                f'{updater_api_base_url}/modlist_version.txt',
                allow_redirects=True,
            ).text
        )
        with open(modlist_path, 'r') as modlist_file:
            modlist_data = yaml_safe_load(modlist_file)
        if str(modlist_data['version']) != latest_modlist_version:
            with open(modlist_path, 'wb') as modlist_file:
                modlist_file.write(
                    get(
                        f'{updater_api_base_url}/modlist.yaml',
                        allow_redirects=True,
                    ).content
                )
            with open(modlist_path, 'r') as modlist_file:
                modlist_data = yaml_safe_load(modlist_file)
    else:
        with open(modlist_path, 'wb') as modlist_file:
            modlist_file.write(
                get(
                    f'{updater_api_base_url}/modlist.yaml',
                    allow_redirects=True,
                ).content
            )
        with open(modlist_path, 'r') as modlist_file:
            modlist_data = yaml_safe_load(modlist_file)
    latest_app_version = str(
        get(f'{updater_api_base_url}/app_version.txt', allow_redirects=True).text
    )
    if app_version != latest_app_version:
        is_app_updated = False
    else:
        is_app_updated = True
    app = QApplication(argv)
    app.setWindowIcon(QtGui.QIcon(str(favicon_path)))
    window = ModdingHelperApp()
    window.setWindowTitle(
        f'Modding Helper {app_version} [Modlist: {modlist_data["version"]}]'
    )
    window.show()

    download_url = f'https://github.com/Henrique-Coder/modding-helper/releases/download/v{latest_app_version}/ModdingHelper-v{latest_app_version}-fabric-mc1.20.1.exe'
    if not is_app_updated:
        message_box = QMessageBox(window)
        message_box.setWindowTitle(f'New version available ({latest_app_version})')
        message_box.setText(
            'A new version of Modding Helper is available, please download it by clicking on the button below.'
        )

        exit_button = QPushButton('Exit')
        download_button = QPushButton('Download')

        message_box.addButton(exit_button, QMessageBox.RejectRole)
        message_box.addButton(download_button, QMessageBox.AcceptRole)
        message_box.setDefaultButton(download_button)

        exit_button.clicked.connect(lambda: exit())
        download_button.clicked.connect(lambda: webopen(download_url))

        if message_box.exec_() == QMessageBox.RejectRole:
            exit()
        exit()
    exit(app.exec_())
