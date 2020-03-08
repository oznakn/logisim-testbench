import os
import re
import sys
import subprocess

from PyQt5 import QtCore, QtGui, QtWidgets, uic

qtcreator_file  = "mainwindow.ui"
Ui_MainWindow, QtBaseClass = uic.loadUiType(qtcreator_file)

class MyWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)

        self.truth_table_generated = False

        self.circ_path_input.setText("")
        self.test_file_input.setText("")
        self.console_logs_tb.setText("")

        self.truth_table_model = QtGui.QStandardItemModel(self)
        self.truth_table_tab.setModel(self.truth_table_model)

        self.run_tests_btn.clicked.connect(self.run_tests)
        self.circ_select_btn.clicked.connect(self.select_circ_file)
        self.test_select_btn.clicked.connect(self.select_test_config_file)
        self.clear_tester_btn.clicked.connect(self.clear_test_config)
        self.clear_logs_btn.clicked.connect(self.clear_logs)
        self.save_tt_btn.clicked.connect(self.save_truth_table)

        self.statusbar.showMessage("TestBench is ready.")

    def run_tests(self):
        self.statusbar.showMessage("Running tests...")

        if self.circ_path_input.text() == "":
            error_dialog = QtWidgets.QErrorMessage()
            error_dialog.showMessage('Please select a circuit file!')
            error_dialog.exec_()

            self.statusbar.showMessage("TestBench is ready.")

            return

        if self.test_file_input.text() == "":
            error_dialog = QtWidgets.QErrorMessage()
            error_dialog.showMessage('Please select a test config file!')
            error_dialog.exec_()
            
            self.statusbar.showMessage("TestBench is ready.")

            return

        p = subprocess.Popen(["python3", "convert_to_logisim_evolution.py",
            self.circ_path_input.text()], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        process_out = p.communicate()

        self.console_logs_tb.setText(process_out[0].decode())

        if process_out[1] is not None:
            if not os.access(self.circ_path_input.text() + '.conv.circ', os.R_OK):
                error_dialog = QtWidgets.QErrorMessage()
                error_dialog.showMessage('An error occured during test process: ' + process_out[1].decode())
                error_dialog.exec_()

                return

        p = subprocess.Popen(["java", "-jar", "logisim-evolution.jar",
            self.circ_path_input.text() + ".conv.circ", "-test", "main",
            "_tt.txt"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.clear_logs()

        process_out = p.communicate()
        process_stdout = process_out[0].decode()

        if "-- AUTO-UPDATE ABORTED --\n" in process_stdout:
            self.console_logs_tb.setText(process_stdout.partition("-- AUTO-UPDATE ABORTED --\n")[-1])
        else:
            self.console_logs_tb.setText(process_stdout)
            
        if process_out[1] is not None:
            error_dialog = QtWidgets.QErrorMessage()
            error_dialog.showMessage('An error occured during test process: ' + process_out[1].decode())
            error_dialog.exec_()

        tester_pf = re.findall(r"Passed: (\d+), Failed: (\d)+\n", process_stdout)

        if len(tester_pf) != 0:        
            info_dialog = QtWidgets.QMessageBox()
            info_dialog.setIcon(QtWidgets.QMessageBox.Information)
            info_dialog.setText(f"Passed: {tester_pf[0][0]}\nFailed: {tester_pf[0][1]}")
            info_dialog.setInformativeText("Detailed output can be found in console output section.")
            info_dialog.setWindowTitle("Tester output")
            info_dialog.setStandardButtons(QtWidgets.QMessageBox.Ok)
            info_dialog.exec_()
        else:
            self.console_logs_tb.setText(self.console_logs_tb.toPlainText() + process_out[1].decode())

        self.statusbar.showMessage("TestBench is ready.")
        os.remove(self.circ_path_input.text() + '.conv.circ')

    def select_circ_file(self):
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select circuit file",
            "","Logisim Circuit Files (*.circ);;All Files (*)", options=options)

        if fileName:
            self.circ_path_input.setText(fileName)
            self.statusbar.showMessage("Selected circuit file.")

    def select_test_config_file(self):
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select test configuration file",
            "","JSON Files (*.json);;All Files (*)", options=options)

        if fileName:
            self.test_file_input.setText(fileName)
            self.statusbar.showMessage("Selected test configuration file.")
            self.generate_truth_table(fileName)

    def generate_truth_table(self, fileName):
        self.statusbar.showMessage("Generating truth table...")

        p = subprocess.Popen(["python3", "test_vector_gen.py", fileName, "-o", "_tt.txt"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.communicate()

        try:
            with open("_tt.txt", "r") as fp:
                self.truth_table_model.setRowCount(0)

                for line in fp.readlines():
                    row = [QtGui.QStandardItem(x) for x in line.replace("\n", "").split(" ")]
                    self.truth_table_model.appendRow(row)
        except Exception as e:
            error_dialog = QtWidgets.QErrorMessage()
            error_dialog.showMessage('Error reading test vector: ' + str(e))
            error_dialog.exec_()

            return
            
        self.truth_table_tab.resizeColumnsToContents()
        self.statusbar.showMessage("Truth table is OK.")

        self.truth_table_generated = True

    def clear_test_config(self):
        self.test_file_input.setText("")
        self.truth_table_model.setRowCount(0)

        self.statusbar.showMessage("Cleared test configurations.")

    def clear_logs(self):
        self.console_logs_tb.setText("")

        self.statusbar.showMessage("Cleared logisim console logs.")
        
    def save_truth_table(self):
        if not self.truth_table_generated:
            error_dialog = QtWidgets.QErrorMessage()
            error_dialog.showMessage('Please select a test config file!')
            error_dialog.exec_()
            
            self.statusbar.showMessage("TestBench is ready.")

            return

        with open('_tt.txt') as fp:
            name = QtWidgets.QFileDialog.getSaveFileName(self, 'Save File')
            file = open(name[0], 'w')
            file.write(fp.read())
            file.close()

        self.statusbar.showMessage("TestBench is ready.")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MyWindow()
    window.show()
    window.setWindowTitle("Sazak's Logisim Circuit TestBench")

    sys.exit(app.exec_())