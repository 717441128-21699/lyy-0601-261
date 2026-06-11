import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QIcon
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    font = QFont('Microsoft YaHei', 9)
    app.setFont(font)
    
    window = MainWindow()
    window.setWindowTitle('记账理财桌面自动化工具')
    window.resize(1400, 900)
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
