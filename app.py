from datetime import datetime
from json import load as json_load
from os import getlogin, makedirs, environ, remove
from pathlib import Path
from re import compile
from shutil import move, rmtree, copy
from subprocess import check_output
from sys import argv, exit
from webbrowser import open as web_open
from zipfile import ZipFile

from requests import get
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

        self.nvidia_radio_yes = QRadioButton('Yes, I have an active NVIDIA graphics card.')
        self.nvidia_radio_no = QRadioButton('No, I have a different graphics card or integrated graphics.')

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
            checkbox.setToolTip(f'Description: {mod["description"]}\nWebsite: {mod["website_url"]}')
            checkbox.installEventFilter(self)
            self.mod_checkboxes.append(checkbox)
        revert_button = QPushButton('Revert to last backup')
        install_button = QPushButton('Install mods')
        backup_checkbox = self.backup_checkbox = QtWidgets.QCheckBox('Backup current mods before installing')
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
        vbox.addWidget(QLabel('Does your computer have an active NVIDIA graphics card?'))
        vbox.addWidget(self.nvidia_radio_yes)
        vbox.addWidget(self.nvidia_radio_no)
        vbox.addSpacing(20)
        vbox.addWidget(QLabel('Select the extra mods you want to install (optimization mods will be installed automatically):'))
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

        all_mods_filenames = list(Path(self.minecraft_dir_text.text(), 'mods').iterdir())
        all_user_mods_slug = list()
        for filename in all_mods_filenames:
            try:
                with ZipFile(filename, 'r') as jar, jar.open('fabric.mod.json') as json_file:
                    jar_data = json_load(json_file)
                all_user_mods_slug.extend([jar_data['name'], jar_data['id']])
            except Exception:
                continue

        all_user_mods_slug = list(dict.fromkeys(all_user_mods_slug))
        [checkbox.setChecked(True) for checkbox in self.mod_checkboxes if checkbox.text() in all_user_mods_slug]

        msg = (
            f'Modding Helper [{app_version}] by @henrique-coder (GitHub)\n'
            'Modding Helper is not affiliated with any mod or modding community.\n'
            'Modding Helper is not responsible for any damage caused to your computer or Minecraft installation.\n'
            'The mods are downloaded from Modrinth, all from version 1.20.1 (Fabric) and are always up to date.\n'
            'Backup your current mods before installing new mods (recommended).\n'
            'If you have any problems, feel free to open Issues in the GitHub repository. Have a nice modding!'
        )
        [print(line) for line in msg.strip().splitlines()]
        [self.update_console(line) for line in msg.strip().splitlines()]

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
        backup_folders = [folder for folder in Path('.backups').iterdir() if backup_folder_regex.match(folder.name)]

        if not backup_folders:
            msg = 'No backups found!'
            print(msg)
            self.update_console(msg)
            QMessageBox.critical(self, 'Error', 'No backups found!', QMessageBox.Ok, QMessageBox.Ok)
            return

        reply = QMessageBox.question(self, 'Warning', 'Are you sure you want to revert mods to the last backup?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            minecraft_dir = self.minecraft_dir_text.text()
            latest_backup = sorted(backup_folders)[-1]

            [remove(file) for file in Path(minecraft_dir, 'mods').iterdir()]
            [move(file, Path(minecraft_dir, 'mods')) for file in latest_backup.iterdir()]
            rmtree(latest_backup)

            msg = f'Mods reverted to the latest backup! ({latest_backup.name})'
            print(msg)
            self.update_console(msg)

    def install_mods(self):
        selected_mods = [checkbox.text() for checkbox in self.mod_checkboxes if checkbox.isChecked()]
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

        if backup_selected:
            now_time_formatted = datetime.now().strftime("%Y.%m.%d-%H.%M.%S.%f")
            Path(f'.backups/{now_time_formatted}').mkdir(parents=True, exist_ok=True)
            [copy(file, Path('.backups', now_time_formatted)) for file in Path(minecraft_dir, 'mods').iterdir()]
            msg = 'Backup completed!'
            print(msg)
            self.update_console(msg)

        these_mod_filenames = list()

        msg = 'Downloading mods...'
        print(msg)
        self.update_console(msg)

        for mod in modlist_data['mod_libs']:
            mod_filename, mod_download_url = self.get_modrinth_project_info(mod['slug'])
            these_mod_filenames.append(mod_filename)
            if Path(minecraft_dir, 'mods', mod_filename).exists():
                msg = f'Mod {mod["name"]} is already installed!'
                print(msg)
                self.update_console(msg)
                continue
            if not mod_filename or not mod_download_url:
                msg = f'Error downloading mod: {mod["name"]}'
                print(msg)
                self.update_console(msg)
                continue
            with open(Path(minecraft_dir, 'mods', mod_filename), 'wb') as mod_file:
                mod_file.write(get(mod_download_url, allow_redirects=True).content)
            msg = f'Mod {mod["name"]} was successfully installed!'
            print(msg)
            self.update_console(msg)
        if self.nvidia_radio_yes.isChecked():
            for mod in modlist_data['nvidia_gpu']:
                mod_filename, mod_download_url = self.get_modrinth_project_info(mod['slug'])
                these_mod_filenames.append(mod_filename)
                if Path(minecraft_dir, 'mods', mod_filename).exists():
                    msg = f'Mod {mod["name"]} is already installed!'
                    print(msg)
                    self.update_console(msg)
                    continue
                if not mod_filename or not mod_download_url:
                    msg = f'Error downloading mod: {mod["name"]}'
                    print(msg)
                    self.update_console(msg)
                    continue
                with open(Path(minecraft_dir, 'mods', mod_filename), 'wb') as mod_file:
                    mod_file.write(get(mod_download_url, allow_redirects=True).content)
                msg = f'Mod {mod["name"]} was successfully installed!'
                print(msg)
                self.update_console(msg)
        for mod in modlist_data['optimization']:
            mod_filename, mod_download_url = self.get_modrinth_project_info(mod['slug'])
            these_mod_filenames.append(mod_filename)
            if Path(minecraft_dir, 'mods', mod_filename).exists():
                msg = f'Mod {mod["name"]} is already installed!'
                print(msg)
                self.update_console(msg)
                continue
            if not mod_filename or not mod_download_url:
                msg = f'Error downloading mod: {mod["name"]}'
                print(msg)
                self.update_console(msg)
                continue
            with open(Path(minecraft_dir, 'mods', mod_filename), 'wb') as mod_file:
                mod_file.write(get(mod_download_url, allow_redirects=True).content)
            msg = f'Mod {mod["name"]} was successfully installed!'
            print(msg)
            self.update_console(msg)
        for mod in modlist_data['ui']:
            if mod['name'] in selected_mods:
                mod_filename, mod_download_url = self.get_modrinth_project_info(mod['slug'])
                these_mod_filenames.append(mod_filename)
                if Path(minecraft_dir, 'mods', mod_filename).exists():
                    msg = f'Mod {mod["name"]} is already installed!'
                    print(msg)
                    self.update_console(msg)
                    continue
                if not mod_filename or not mod_download_url:
                    msg = f'Error downloading mod: {mod["name"]}'
                    print(msg)
                    self.update_console(msg)
                    continue
                with open(Path(minecraft_dir, 'mods', mod_filename), 'wb') as mod_file:
                    mod_file.write(get(mod_download_url, allow_redirects=True).content)
                msg = f'Mod {mod["name"]} was successfully installed!'
                print(msg)
                self.update_console(msg)
        for file in Path(minecraft_dir, 'mods').iterdir():
            if file.name.endswith('.jar') and file.name not in these_mod_filenames:
                remove(file)
                msg = f'Old mod {file.name} was successfully removed!'
                print(msg)
                self.update_console(msg)

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

        msg = 'All mods were successfully installed!'
        print(msg)
        self.update_console(msg)

    def deselect_all(self):
        for checkbox in self.mod_checkboxes:
            checkbox.setChecked(False)

    def select_all(self):
        for checkbox in self.mod_checkboxes:
            checkbox.setChecked(True)

    def update_console(self, msg):
        timestamp = QtCore.QDateTime.currentDateTime().toString('[yyyy.MM.dd-hh:mm:ss.zzz]')
        self.console_textedit.append(f'{timestamp} {msg}')

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.ContextMenu and obj in self.mod_checkboxes:
            menu = QtWidgets.QMenu(self)
            action = menu.addAction(f'Open {obj.text()} website')
            if menu.exec_(event.globalPos()) == action:
                QtGui.QDesktopServices.openUrl(QtCore.QUrl(self.get_website_url_by_name(obj.text())))
                return True
        return False

    def get_website_url_by_name(self, name):
        return next((mod['website_url'] for mod in modlist_data['ui'] if mod['name'] == name), None)

    def browse_minecraft_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, 'Select your .minecraft directory', self.minecraft_dir_text.text())
        if dir_path:
            self.minecraft_dir_text.setText(dir_path)

    def on_nvidia_radio_yes(self):
        if self.nvidia_radio_no.isChecked():
            self.nvidia_radio_no.setChecked(False)
            msg = 'OFF - Mods made for NVIDIA graphics cards will not be installed.'
            print(msg)
            self.update_console(msg)

    def on_nvidia_radio_no(self):
        if self.nvidia_radio_yes.isChecked():
            self.nvidia_radio_yes.setChecked(False)
            msg = 'ON - Mods made for NVIDIA graphics cards will be installed.'
            print(msg)
            self.update_console(msg)


if __name__ == '__main__':
    app_version = '1.0.2'
    mc_version = '1.20.1'
    mc_loader = 'fabric'
    favicon_path = Path(environ['TEMP'], 'moddinghelper_favicon.ico')
    updater_api_base_url = 'https://raw.githubusercontent.com/Henrique-Coder/modding-helper/main/updater_api'

    if not favicon_path.exists():
        open(favicon_path, 'wb').write(get(f'{updater_api_base_url}/favicon.ico', allow_redirects=True).content)

    modlist_path = Path(environ['TEMP'], 'moddinghelper_modlist.yaml')
    if modlist_path.exists():
        latest_modlist_version = get(f'{updater_api_base_url}/modlist_version.txt', allow_redirects=True).text
        with open(modlist_path, 'r') as modlist_file:
            modlist_data = yaml_safe_load(modlist_file)
        if str(modlist_data['version']) != latest_modlist_version:
            with open(modlist_path, 'wb') as modlist_file:
                modlist_file.write(
                    get(f'{updater_api_base_url}/modlist.yaml', allow_redirects=True).content)
            with open(modlist_path, 'r') as modlist_file:
                modlist_data = yaml_safe_load(modlist_file)
    else:
        with open(modlist_path, 'wb') as modlist_file:
            modlist_file.write(
                get(f'{updater_api_base_url}/modlist.yaml', allow_redirects=True).content)
        with open(modlist_path, 'r') as modlist_file:
            modlist_data = yaml_safe_load(modlist_file)
    latest_app_version = get(f'{updater_api_base_url}/app_version.txt', allow_redirects=True).text
    is_app_updated = app_version == latest_app_version

    app = QApplication(argv)
    app.setWindowIcon(QtGui.QIcon(str(favicon_path)))
    window = ModdingHelperApp()
    window.setWindowTitle(f'Modding Helper {app_version} (Modlist {modlist_data["version"]}) - Minecraft {mc_version} ({mc_loader.title()})')
    window.show()

    download_url = f'https://github.com/Henrique-Coder/modding-helper/releases/download/v{latest_app_version}/ModdingHelper-v{latest_app_version}-fabric-mc1.20.1.exe'
    if not is_app_updated:
        message_box = QMessageBox(window)
        message_box.setWindowTitle(f'New version available ({latest_app_version})')
        message_box.setText('A new version of Modding Helper is available, please download it by clicking on the button below.')

        exit_button = QPushButton('Exit')
        download_button = QPushButton('Download')

        message_box.addButton(exit_button, QMessageBox.RejectRole)
        message_box.addButton(download_button, QMessageBox.AcceptRole)
        message_box.setDefaultButton(download_button)

        exit_button.clicked.connect(lambda: exit())
        download_button.clicked.connect(lambda: web_open(download_url))

        if message_box.exec_() == QMessageBox.RejectRole:
            exit()
        exit()
    exit(app.exec_())
