#!/usr/bin/env python
# coding: utf-8

# In[33]:


import csv
import json
import requests
import psycopg2
import openpyxl
import pandas as pd
from urllib.parse import unquote
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QSizePolicy,
    QTableWidget, QGridLayout, QHeaderView, QTableWidgetItem, QMessageBox, QComboBox,
    QInputDialog, QHBoxLayout, QVBoxLayout, QGridLayout ,QFileDialog, QAbstractItemView
)
from PyQt5.QtGui import QPainter, QPolygon, QPen, QBrush, QColor, QFont,QPixmap  # QPoint 제외
from PyQt5.QtCore import Qt, QPoint  # QPoint를 여기서 임포트

import sys
import xml.etree.ElementTree as ET








# In[34]:


class ApiCall:
    def __init__(self, key, url):
        self.key = key
        self.url = url

    def call(self, **kwargs):
        params = {'dataType': 'XML'}
        params['serviceKey'] = self.key
    
        for key in kwargs.keys():
            params[key] = kwargs[key]
        try:
            response =  requests.get(self.url, params=params)
            return response  #### response임.........
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(None, '에러', f"호출 중 오류 발생: {e}")
            return None


# In[35]:


class ParameterSaver:
    @staticmethod
    def F_connectPostDB():
        host = '127.0.0.1'
        port = '5432'
        user = 'postgres'
        password = 'postgres'
        database = 'postgres'

        try:
            # PostgreSQL 연결
            connection = psycopg2.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database
            )

            cursor = connection.cursor()
            print("PostgreSQL 데이터베이스 연결 성공!")

            return connection, cursor

        except psycopg2.Error as error:
            print("PostgreSQL 오류: ", error)
            return None, None

    @staticmethod
    def F_ConnectionClose(cursor, connection):
        cursor.close()
        connection.close()
        print("데이터 베이스 연결 해제")

    def __init__(self, id, url):
        self.id = id
        self.url = url

    def save_parameters(self):
        connection, cursor = self.F_connectPostDB()  
        if not connection or not cursor:
            return

        try:
            # 중복된 ID인지 확인
            cursor.execute("SELECT COUNT(*) FROM URL_TB WHERE id = %s", (self.id,))
            count = cursor.fetchone()[0]
            if count > 0:
                QMessageBox.warning(None, '중복된 값', '중복된 ID 값입니다.')
                return

            cursor.execute("INSERT INTO URL_TB (id, url) VALUES (%s, %s)", (self.id, self.url))
            connection.commit()
            QMessageBox.information(None, '성공', 'URL이 성공적으로 저장되었습니다.')
        except psycopg2.Error as e:
            print(f"에러 발생: {e}")
            QMessageBox.critical(None, '에러', f"데이터베이스 오류 발생: {e}")
        finally:
            if connection:
                self.F_ConnectionClose(cursor, connection)


# In[36]:


class DataParser:
    @staticmethod
    def parse_xml(api_data): # 데이터 프레임으로 바꿔주는 것
        try:
            root = ET.fromstring(api_data)
            # DataFrame을 만들기 위한 빈 리스트 생성
            data_list = []

            # items 요소가 있는지 확인
            items_element = root.find(".//items")
            if items_element:
                # items 내부의 item 데이터 추출
                for item in root.findall('.//item'):
                    item_data = {}
                    for child in item:
                        item_data[child.tag] = child.text
                    data_list.append(item_data)
            else:
                pass
                # items 요소가 없는 경우
                # sub_data = []
                # result_code = root.find(".//resultCode")
                # if result_code is not None:
                #     columns.append("resultCode")
                #     sub_data.append(result_code.text)

                # result_msg = root.find(".//resultMsg")
                # if result_msg is not None:
                #     columns.append("resultMsg")
                #     sub_data.append(result_msg.text)
                # data.append(sub_data)
            return pd.DataFrame(data_list)
        except ET.ParseError as e:
            print("XML 파싱 오류:", e)
            return None  # XML 파싱 오류인 경우 None을 반환


# In[37]:


class PreviewUpdater:
    @staticmethod
    def show_preview(preview_table, data):
        # 미리보기 테이블 업데이트
        preview_table.setRowCount(data.shape[0])
        preview_table.setColumnCount(data.shape[1])
        preview_table.setHorizontalHeaderLabels(data.columns)

        for row in range(data.shape[0]):
            for col in range(data.shape[1]):
                item = QTableWidgetItem(str(data.iloc[row, col]))
                preview_table.setItem(row, col, item)


# In[38]:


class ParameterViewer(QWidget):
    def __init__(self, my_widget_instance, parent_widget_type, target_url_field="api_url1_edit"):
        super().__init__()
        self.my_widget_instance = my_widget_instance
        self.parent_widget_type = parent_widget_type
        self.target_url_field = target_url_field  # 추가된 인자
        self.setWindowTitle('파라미터 목록')
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # 테이블 위젯 생성
        self.param_table = QTableWidget()
        self.param_table.resizeColumnsToContents()
        self.param_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.param_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.load_parameter_list()
        layout.addWidget(self.param_table)
        # 확인 버튼 추가
        confirm_button = QPushButton('확인')
        confirm_button.clicked.connect(self.on_confirm_button_clicked)
        layout.addWidget(confirm_button)

        self.setLayout(layout)
        self.resize(800, 600)  # 창의 크기를 너비 800px, 높이 600px로 설정
        
    def load_parameter_list(self):
        connection, cursor = ParameterSaver.F_connectPostDB()
        if not connection or not cursor:
            return

        try:
            cursor.execute("SELECT * FROM URL_TB")
            rows = cursor.fetchall()
            num_rows = len(rows)
            num_cols = len(rows[0]) if num_rows > 0 else 0

            # 행과 열 수 설정
            self.param_table.setRowCount(num_rows)
            self.param_table.setColumnCount(num_cols)

            # 헤더 설정
            header_labels = ["ID", "URL"]  # 컬럼 헤더 이름 설정
            self.param_table.setHorizontalHeaderLabels(header_labels)

            # 데이터 추가
            for row_idx, row in enumerate(rows):
                for col_idx, col_value in enumerate(row):
                    item = QTableWidgetItem(str(col_value))
                    self.param_table.setItem(row_idx, col_idx, item)

            self.param_table.resizeColumnsToContents()

        except psycopg2.Error as e:
            QMessageBox.critical(None, '에러', f"데이터베이스 오류 발생: {e}")

        finally:
            ParameterSaver.F_ConnectionClose(cursor, connection)

    def on_confirm_button_clicked(self):
        selected_items = self.param_table.selectedItems()
        if selected_items:
            selected_row = selected_items[0].row()
            url_item = self.param_table.item(selected_row, 1)
            if url_item:
                url = url_item.text()

                if self.parent_widget_type == "MyWidget":

                    id_item = self.param_table.item(selected_row, 0)
                    id = id_item.text()

                    try:
                        # 해당 ID 값을 가진 행의 파라미터 값 출력을 위해 DB에서 해당 값을 가져옴
                        connection, cursor = ParameterSaver.F_connectPostDB()
                        cursor.execute("SELECT param FROM PARAMS_TB WHERE id = %s", (id,))
                        rows = cursor.fetchall()

                        self.my_widget_instance.api_input.setText(rows[0][0].split('=')[0])
                        self.my_widget_instance.key_input.setText(unquote(rows[2][0].split('=')[1]))
                        
                        parameters = {}
                        for row in rows[3:]:
                            parts = row[0].split("=")
                            parameters[parts[0]] = parts[1]
                        self.my_widget_instance.auto_add_parameters(parameters)

                    except psycopg2.Error as e:
                        print(f"에러 발생: {e}")
                    finally:
                        ParameterSaver.F_ConnectionClose(cursor, connection)

                    self.my_widget_instance.origin_data = requests.get(url)
                    self.my_widget_instance.df_data = fetch_data(self.my_widget_instance.origin_data.url)
                    data = self.my_widget_instance.df_data
                    PreviewUpdater.show_preview(self.my_widget_instance.preview_table, data)
                elif self.parent_widget_type == "DataJoinerApp":
                    if self.target_url_field == "api_url1_edit":
                        self.my_widget_instance.api_url1_edit.setText(url)
                    elif self.target_url_field == "api_url2_edit":
                        self.my_widget_instance.api_url2_edit.setText(url)
                self.close()
            else:
                print("선택된 행의 URL이 없습니다.")
        else:
            print("선택된 행이 없습니다.")


# In[39]:


class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.df_data = pd.DataFrame() # 데이터 프레임???
        self.origin_data = None
        self.param_labels = []  # 파라미터 라벨 리스트
        self.param_inputs = []  # 파라미터 입력 필드 리스트
        self.param_grid_row = 0  # 현재 그리드 레이아웃의 행 위치
        self.param_grid_col = 0  # 변경: 첫 번째 파라미터부터 첫 번째 열에 배치
        self.max_cols = 3  # 한 행에 최대 파라미터 개수
        self.setup()  # UI 설정

    def setup(self):
        self.setWindowTitle('API 다운로더')
        self.setGeometry(600, 600, 600, 600)
        font = QFont()
        font.setPointSize(10)
        self.setFont(font)

        main_layout = QVBoxLayout()

        self.fixed_layout = QVBoxLayout()
        main_layout.addLayout(self.fixed_layout)

        self.api_label = QLabel('API URL:')
        self.api_input = QLineEdit(self)
        self.default_param(self.fixed_layout, self.api_label, self.api_input)

        self.key_label = QLabel('serviceKey:')
        self.key_input = QLineEdit(self)
        self.default_param(self.fixed_layout, self.key_label, self.key_input)

        self.param_grid_layout = QGridLayout()
        main_layout.addLayout(self.param_grid_layout)
        self.param_grid_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.add_param_button = QPushButton('파라미터 추가', self)
        self.add_param_button.clicked.connect(self.add_parameter)

        self.remove_param_button = QPushButton('파라미터 삭제', self)
        self.remove_param_button.clicked.connect(self.remove_parameter)

        self.download_params_button = QPushButton('파라미터 저장', self)
        self.download_params_button.clicked.connect(self.download_parameters)

        self.show_params_button = QPushButton('파라미터 목록', self)
        self.show_params_button.clicked.connect(self.show_parameters)

        self.call_button = QPushButton('OpenAPI 호출', self)
        self.call_button.clicked.connect(self.api_call)

        self.download_button = QPushButton('API 호출정보 저장', self)
        self.download_button.clicked.connect(self.download_data)

        button_layout1 = QHBoxLayout()
        button_layout1.addWidget(self.show_params_button)
        button_layout1.addWidget(self.add_param_button)
        button_layout1.addWidget(self.remove_param_button)
        button_layout1.addWidget(self.download_params_button)

        button_layout2 = QHBoxLayout()
        button_layout2.addWidget(self.call_button)
        button_layout2.addWidget(self.download_button)

        main_layout.addLayout(button_layout1)
        main_layout.addLayout(button_layout2)

        self.preview_label = QLabel('미리보기')
        main_layout.addWidget(self.preview_label)
        self.preview_table = QTableWidget(self)
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.preview_table.verticalHeader().setVisible(False)
        main_layout.addWidget(self.preview_table)

        self.setLayout(main_layout)

    def default_param(self, layout, label_widget, edit_widget):
        h_layout = QHBoxLayout()
        label_widget.setMinimumWidth(100)  # 라벨의 최소 너비 설정
        label_widget.setMaximumWidth(100)
        h_layout.addWidget(label_widget)
        h_layout.addWidget(edit_widget)
        h_layout.setSpacing(10)  # 라벨과 입력칸 사이의 간격 설정
        h_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # 왼쪽 정렬 및 수직 가운데 정렬
        layout.addLayout(h_layout)

    def add_param_to_grid(self, label_widget, edit_widget):
        layout = QHBoxLayout()
        layout.addWidget(label_widget)
        layout.addWidget(edit_widget)
        self.param_grid_layout.addLayout(layout, self.param_grid_row, self.param_grid_col)

        self.param_grid_col += 1
        if self.param_grid_col >= self.max_cols:
            self.param_grid_col = 0
            self.param_grid_row += 1

    def add_parameter(self):
        param_name, ok = QInputDialog.getText(self, '파라미터 추가', '파라미터명:')
        if ok and param_name:
            param_label = QLabel(f'{param_name}')
            param_label.setMinimumWidth(100)  # 라벨의 최소 너비 설정
            param_label.setMaximumWidth(100)
            param_input = QLineEdit(self)
            param_input.setMaximumWidth(200)
            param_input.setMinimumWidth(200)
            self.param_labels.append(param_label)
            self.param_inputs.append(param_input)
            self.add_param_to_grid(param_label, param_input)

            param_input.setFocus()
            
    def auto_add_parameters(self, parameters):
        while self.param_labels:
            param_label = self.param_labels.pop()
            param_input = self.param_inputs.pop()
            param_label.deleteLater()
            param_input.deleteLater()
            self.param_grid_layout.removeWidget(param_label)
            self.param_grid_layout.removeWidget(param_input)
            param_label.setParent(None)
            param_input.setParent(None)

        self.param_grid_row = 0
        self.param_grid_col = 0

        # 새로운 파라미터들 추가
        for key, value in parameters.items():
            param_label = QLabel(key)
            param_label.setMinimumWidth(100)
            param_label.setMaximumWidth(100)
            param_input = QLineEdit(self)
            param_input.setMaximumWidth(200)
            param_input.setMinimumWidth(200)
            param_input.setText(value)
            self.param_labels.append(param_label)
            self.param_inputs.append(param_input)
            self.add_param_to_grid(param_label, param_input)

    def remove_parameter(self):
        if self.param_labels:
            param_label = self.param_labels.pop()
            param_input = self.param_inputs.pop()
            param_label.deleteLater()
            param_input.deleteLater()
            v_layout = self.layout()
            v_layout.removeWidget(param_label)
            v_layout.removeWidget(param_input)
            param_label.setParent(None)
            param_input.setParent(None)

    def get_parameters(self):
        # 입력된 파라미터 수집
        params = {}
        for label, input_field in zip(self.param_labels, self.param_inputs):
            param_name = label.text()
            param_value = input_field.text()
            if param_name and param_value:
                params[param_name] = param_value
        return params

    def api_call(self):
        url = self.api_input.text()
        service_key = self.key_input.text()

        if not service_key:
            QMessageBox.critical(None, '에러', '서비스 키를 입력하세요.')
            return

        # ApiCall 객체 생성
        api_caller = ApiCall(key=service_key, url=url) 

        # 파라미터 설정
        params = self.get_parameters()

        # API 호출
        self.origin_data = api_caller.call(serviceKey=service_key, **params)
        self.df_data = fetch_data(self.origin_data.url)
        if not self.df_data.empty:
            PreviewUpdater.show_preview(self.preview_table, self.df_data)
        else:
            print('호출 실패')

    def download_parameters(self):

        if self.origin_data:
            id, ok = QInputDialog.getText(self, '저장명 입력', '저장할 ID를 입력하세요:')
            if ok:
                parameter_saver = ParameterSaver(id, self.origin_data.url)
                parameter_saver.save_parameters()
        else:
            QMessageBox.critical(None, '에러', '먼저 API를 호출하세요.')
            return
        
    def show_parameters(self):
        # 'MyWidget'를 parent_widget_type 인자로 전달
        self.parameter_viewer = ParameterViewer(self, "MyWidget")
        self.parameter_viewer.show()

    def download_data(self):
        if not self.df_data.empty:
            file_types = "CSV files (*.csv);;XML files (*.xml);;JSON files (*.json);;Excel files (*.xlsx)"
            file_path, file_type = QFileDialog.getSaveFileName(self, "Save File", "", file_types)
            if file_path:
                downloader = DataDownload(self.df_data)
                if file_type == "XML files (*.xml)":
                    downloader.save_xml(file_path)
                elif file_type == "JSON files (*.json)":
                    downloader.save_json(file_path)
                elif file_type == "CSV files (*.csv)":
                    downloader.save_csv(file_path)
                elif file_type == "Excel files (*.xlsx)":
                    downloader.save_xlsx(file_path)
        else:
            QMessageBox.critical(None, '에러', 'API 데이터를 가져오지 못했습니다.')


# In[40]:


class DataDownload:
    def __init__(self, api_data):
        self.api_data = api_data # 데이터 프레임임!!!

    def save_xml(self, file_path):
        data = self.api_data.to_xml(index=False)
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(data)
            print("XML 파일 저장 성공")
        except Exception as e:
            print("XML 파일 저장 실패:", e)

    def save_csv(self, file_path):
        try:
            # UTF-8 인코딩으로 CSV 파일 저장, 인덱스는 제외하고, 각 레코드는 '\n'으로 종료
            self.api_data.to_csv(file_path, index=False, encoding='utf-8-sig')
            print("csv 파일 저장 성공")
        except Exception as e:
            print(f"csv 파일 저장 실패: {e}")

    def save_json(self, file_path):
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(self.api_data.to_dict(orient='records'), file, ensure_ascii=False, indent=4)
            print("JSON 파일 저장 성공")
        except Exception as e:
            print("JSON 파일 저장 실패:", e)
            
    def save_xlsx(self, file_path):
        try:
        # 엑셀 파일로 저장할 때는 ExcelWriter 객체를 생성하여 사용합니다.
            with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
                self.api_data.to_excel(writer, index=False)
            print("엑셀 파일 저장 성공")
        except Exception as e:
            print("엑셀 파일 저장 실패:", e)


# In[41]:


def fetch_data(api_url):
    response = requests.get(api_url)
    if 'application/json' in response.headers['Content-Type']:
        data = response.json()  # JSON 데이터 구조에 따라 수정 필요
        df = pd.DataFrame(data)  # 적절한 키를 사용하여 DataFrame 생성
    else:
        data = parse_xml_to_dict(response.text)
        df = pd.DataFrame(data)
    return df

def parse_xml_to_dict(xml_data): 
    data_list = []
    try:
        root = ET.fromstring(xml_data)
        if root.findall('.//item'):
            for item in root.findall('.//item'):
                data = {child.tag: child.text for child in item}
                data_list.append(data)
        else: # item이 없는 경우에도 처리해야함!!
            pass
    except ET.ParseError as e:
        print("XML 파싱 오류:", e)
    return data_list


# In[42]:


class DataJoinerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.joined_data = None

    def initUI(self):
        self.setWindowTitle('API Data Joiner')
        self.setGeometry(100, 100, 600, 400)
        
        layout = QVBoxLayout()

        self.api_url1_edit = QLineEdit(self)
        self.select_button1 = QPushButton('URL1 선택', self)
        # URL1 선택 버튼에 대한 클릭 이벤트 처리
        self.select_button1.clicked.connect(lambda: self.show_parameters('api_url1_edit'))
        
        self.api_url2_edit = QLineEdit(self)
        self.select_button2 = QPushButton('URL2 선택', self)
        # URL2 선택 버튼에 대한 클릭 이벤트 처리
        self.select_button2.clicked.connect(lambda: self.show_parameters('api_url2_edit'))

        # UI 구성
        layout.addWidget(QLabel('첫 번째 API 주소:'))
        layout.addWidget(self.api_url1_edit)
        layout.addWidget(self.select_button1)  # 올바른 버튼 변수명 사용
        
        layout.addWidget(QLabel('두 번째 API 주소:'))
        layout.addWidget(self.api_url2_edit)
        layout.addWidget(self.select_button2)  # 올바른 버튼 변수명 사용

        self.join_column_edit = QLineEdit(self)
        layout.addWidget(QLabel('조인할 컬럼 이름:'))
        layout.addWidget(self.join_column_edit)

        self.join_button = QPushButton('데이터 조인', self)
        self.join_button.clicked.connect(self.join_data)
        layout.addWidget(self.join_button)

        self.result_table = QTableWidget(self)
        layout.addWidget(self.result_table)

        self.save_btn = QPushButton('파일 저장', self)
        self.save_btn.clicked.connect(self.download)
        layout.addWidget(self.save_btn)

        self.setLayout(layout)

    def show_parameters(self, target_field):
        self.parameter_viewer = ParameterViewer(self, "DataJoinerApp", target_url_field=target_field)
        self.parameter_viewer.show()


    def join_data(self):
        api_url_1 = self.api_url1_edit.text()
        api_url_2 = self.api_url2_edit.text()
        join_column = self.join_column_edit.text()

        if not api_url_1 or not api_url_2 or not join_column:
            QMessageBox.warning(self, '경고', 'API URL과 조인할 컬럼 이름을 입력해야 합니다!')
            return
        
        df1 = fetch_data(api_url_1)
        df2 = fetch_data(api_url_2)

        if df1 is None or df2 is None:
            QMessageBox.critical(self, '오류', '데이터를 가져오는 데 실패했습니다. API URL을 확인해주세요.')
            return

        if join_column in df1.columns and join_column in df2.columns:
            self.joined_data = pd.merge(df1, df2, on=join_column, how='inner')
            self.show_data_in_table(self.joined_data)
        else:
            QMessageBox.warning(self, '오류', '조인할 컬럼이 누락되었거나 잘못되었습니다.')
            self.result_table.clear()  # 테이블 초기화
            self.result_table.setRowCount(0)
            self.result_table.setColumnCount(0)        

    def show_data_in_table(self, data):
        self.result_table.setRowCount(data.shape[0])
        self.result_table.setColumnCount(data.shape[1])
        self.result_table.setHorizontalHeaderLabels(data.columns)

        for row in range(data.shape[0]):
            for col in range(data.shape[1]):
                item = QTableWidgetItem(str(data.iloc[row, col]))
                self.result_table.setItem(row, col, item)

    def download(self):
        data = self.joined_data

        if not data.empty:
            file_types = "CSV files (*.csv);;XML files (*.xml);;JSON files (*.json);;Excel files (*.xlsx)"
            file_path, file_type = QFileDialog.getSaveFileName(self, "Save File", "", file_types)
            if file_path:
                downloader = DataDownload(data)
                if file_type == "XML files (*.xml)":
                    downloader.save_xml(file_path)
                elif file_type == "JSON files (*.json)":
                    downloader.save_json(file_path)
                elif file_type == "CSV files (*.csv)":
                    downloader.save_csv(file_path)
                elif file_type == "Excel files (*.xlsx)":
                    downloader.save_xlsx(file_path)
        else:
            QMessageBox.critical(None, '에러', 'API 데이터를 가져오지 못했습니다.')


# In[43]:


class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        self.myWidgetApp = None  # MyWidget 인스턴스를 저장할 변수
        self.dataJoiner = None  # DataJoinerApp 인스턴스를 저장할 변수 추가
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle('코딩의 신 정 인 영')
        self.setGeometry(500,500,500,500)

        # 이미지를 QLabel에 삽입
        image_label = QLabel(self)
        pixmap = QPixmap(r'C:\Users\Kwate\OneDrive\바탕 화면\qwe.png')  # 이미지 경로를 여기에 넣으세요
        image_label.setPixmap(pixmap)
        image_label.setAlignment(Qt.AlignCenter)

        # 버튼 두 개가 있는 수평 레이아웃 생성
        hbox = QHBoxLayout()
        btn1 = QPushButton('API 조회', self)
        btn2 = QPushButton('조인', self)
        
        btn1.clicked.connect(self.showMyWidgetApp)  # 버튼 1 클릭 시 showMyWidgetApp 메서드 호출
        btn2.clicked.connect(self.showDataJoinerApp)  # 버튼 2 클릭 시 showDataJoinerApp 메서드 호출
        
        hbox.addWidget(btn1)
        hbox.addWidget(btn2)

        # 버튼 레이아웃과 이미지를 메인 레이아웃에 추가
        vbox = QVBoxLayout()
        vbox.addWidget(image_label)
        vbox.addLayout(hbox)
        self.setLayout(vbox)

    def showMyWidgetApp(self):
        if self.myWidgetApp is None:  # MyWidget 인스턴스가 없으면 생성
            self.myWidgetApp = MyWidget()
        self.myWidgetApp.show()

    def showDataJoinerApp(self):
        if self.dataJoiner is None:  # DataJoinerApp 인스턴스가 없으면 생성
            self.dataJoiner = DataJoinerApp()
        self.dataJoiner.show()


# In[49]:


if __name__ == '__main__':
    app = QApplication.instance()  # 기존 인스턴스 확인
    if not app:  # 인스턴스가 없을 경우 새로 생성
        app = QApplication(sys.argv)
    mainApp = MainApp()  # MainApp 인스턴스 생성
    mainApp.show()
    sys.exit(app.exec_())


# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:




