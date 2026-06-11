from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QListWidgetItem, QStackedWidget, QLabel, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QFont, QColor

from ui.import_window import ImportWindow
from ui.invoice_window import InvoiceWindow
from ui.category_window import CategoryWindow
from ui.payment_match_window import PaymentMatchWindow
from ui.exception_window import ExceptionWindow
from ui.report_window import ReportWindow
from ui.settings_window import SettingsWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.content_stack = QStackedWidget()
        self._init_pages()
        
        sidebar = self._create_sidebar()
        main_layout.addWidget(sidebar, 0)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setStyleSheet('color: #e0e0e0;')
        main_layout.addWidget(separator)
        
        main_layout.addWidget(self.content_stack, 1)

    def _create_sidebar(self):
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet('''
            QWidget {
                background-color: #f5f7fa;
            }
            QListWidget {
                background-color: #f5f7fa;
                border: none;
                padding: 10px 0;
            }
            QListWidget::item {
                padding: 14px 20px;
                margin: 2px 10px;
                border-radius: 6px;
                color: #333;
                font-size: 14px;
            }
            QListWidget::item:hover {
                background-color: #e8ecf1;
            }
            QListWidget::item:selected {
                background-color: #4a90d9;
                color: white;
            }
        ''')
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        title_label = QLabel('记账理财工具')
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont('Microsoft YaHei', 16, QFont.Weight.Bold))
        title_label.setStyleSheet('color: #2c3e50; padding: 20px 0; background-color: #f5f7fa;')
        layout.addWidget(title_label)
        
        self.nav_list = QListWidget()
        self.nav_list.setIconSize(QSize(20, 20))
        
        menu_items = [
            ('📁 文件导入', 'import'),
            ('📋 票据识别核对', 'invoice'),
            ('🏷️ 报销归类', 'category'),
            ('🔗 流水匹配', 'payment'),
            ('⚠️ 异常清单', 'exception'),
            ('📊 统计报表', 'report'),
            ('⚙️ 规则设置', 'settings')
        ]
        
        for text, key in menu_items:
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.nav_list.addItem(item)
        
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        self.nav_list.setCurrentRow(0)
        
        layout.addWidget(self.nav_list, 1)
        
        version_label = QLabel('v1.0.0')
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet('color: #999; padding: 10px; font-size: 11px;')
        layout.addWidget(version_label)
        
        return sidebar

    def _init_pages(self):
        self.import_window = ImportWindow()
        self.invoice_window = InvoiceWindow()
        self.category_window = CategoryWindow()
        self.payment_match_window = PaymentMatchWindow()
        self.exception_window = ExceptionWindow()
        self.report_window = ReportWindow()
        self.settings_window = SettingsWindow()
        
        self.content_stack.addWidget(self.import_window)
        self.content_stack.addWidget(self.invoice_window)
        self.content_stack.addWidget(self.category_window)
        self.content_stack.addWidget(self.payment_match_window)
        self.content_stack.addWidget(self.exception_window)
        self.content_stack.addWidget(self.report_window)
        self.content_stack.addWidget(self.settings_window)

    def _on_nav_changed(self, row: int):
        self.content_stack.setCurrentIndex(row)
        current_widget = self.content_stack.currentWidget()
        if hasattr(current_widget, 'refresh'):
            current_widget.refresh()
