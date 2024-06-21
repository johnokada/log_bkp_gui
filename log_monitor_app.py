
import os
import shutil
import zipfile
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
from threading import Thread
import time

class LogMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Log Monitor")

        self.log_file = ""
        self.backup_dir = ""
        self.max_log_size = tk.IntVar()
        self.max_backup_size = tk.IntVar()
        self.unit = tk.StringVar(value="Bytes")
        self.background_mode = tk.BooleanVar()
        self.monitoring = False

        tk.Label(root, text="Arquivo de Log:").grid(row=0, column=0, padx=10, pady=10)
        self.log_file_entry = tk.Entry(root, width=50)
        self.log_file_entry.grid(row=0, column=1, padx=10, pady=10)
        tk.Button(root, text="Selecionar", command=self.select_log_file).grid(row=0, column=2, padx=10, pady=10)

        tk.Label(root, text="Pasta de Backup:").grid(row=1, column=0, padx=10, pady=10)
        self.backup_dir_entry = tk.Entry(root, width=50)
        self.backup_dir_entry.grid(row=1, column=1, padx=10, pady=10)
        tk.Button(root, text="Selecionar", command=self.select_backup_dir).grid(row=1, column=2, padx=10, pady=10)

        tk.Label(root, text="Tamanho Máximo do Log:").grid(row=2, column=0, padx=10, pady=10)
        tk.Entry(root, textvariable=self.max_log_size).grid(row=2, column=1, padx=10, pady=10)
        tk.OptionMenu(root, self.unit, "Bytes", "Megabytes", "Gigabytes").grid(row=2, column=2, padx=10, pady=10)

        tk.Label(root, text="Tamanho Máximo da Pasta de Backup:").grid(row=3, column=0, padx=10, pady=10)
        tk.Entry(root, textvariable=self.max_backup_size).grid(row=3, column=1, padx=10, pady=10)
        tk.OptionMenu(root, self.unit, "Bytes", "Megabytes", "Gigabytes").grid(row=3, column=2, padx=10, pady=10)

        self.start_button = tk.Button(root, text="Iniciar", command=self.start_monitoring)
        self.start_button.grid(row=4, column=0, padx=10, pady=10)

        self.stop_button = tk.Button(root, text="Parar", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_button.grid(row=4, column=1, padx=10, pady=10)

        self.background_check = tk.Checkbutton(root, text="Executar em segundo plano", variable=self.background_mode)
        self.background_check.grid(row=4, column=2, padx=10, pady=10)

    def select_log_file(self):
        self.log_file = filedialog.askopenfilename()
        self.log_file_entry.insert(0, self.log_file)

    def select_backup_dir(self):
        self.backup_dir = filedialog.askdirectory()
        self.backup_dir_entry.insert(0, self.backup_dir)

    def convert_size_to_bytes(self, size, unit):
        if unit == "Megabytes":
            return size * 1024 * 1024
        elif unit == "Gigabytes":
            return size * 1024 * 1024 * 1024
        else:
            return size

    def start_monitoring(self):
        if not self.log_file or not self.backup_dir:
            messagebox.showerror("Erro", "Selecione o arquivo de log e a pasta de backup.")
            return

        if not self.max_log_size.get() or not self.max_backup_size.get():
            messagebox.showerror("Erro", "Informe os tamanhos máximos para o log e a pasta de backup.")
            return

        self.monitoring = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        if self.background_mode.get():
            self.root.iconify()  # Minimizar para a bandeja do sistema

        self.monitor_thread = Thread(target=self.monitor_log_file)
        self.monitor_thread.start()

    def stop_monitoring(self):
        self.monitoring = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        if self.background_mode.get():
            self.root.deiconify()  # Restaurar a janela do sistema

    def monitor_log_file(self):
        max_log_size_bytes = self.convert_size_to_bytes(self.max_log_size.get(), self.unit.get())
        max_backup_size_bytes = self.convert_size_to_bytes(self.max_backup_size.get(), self.unit.get())

        while self.monitoring:
            if os.path.getsize(self.log_file) > max_log_size_bytes:
                self.zip_and_clear_log()

            self.manage_backup_dir_size(max_backup_size_bytes)

            time.sleep(10)  # Verificar a cada 10 segundos

    def zip_and_clear_log(self):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        zip_filename = f"log_backup_{timestamp}.zip"
        zip_filepath = os.path.join(self.backup_dir, zip_filename)

        with zipfile.ZipFile(zip_filepath, 'w') as zipf:
            zipf.write(self.log_file, os.path.basename(self.log_file))

        with open(self.log_file, 'w'):
            pass  # Limpa o conteúdo do arquivo de log

    def manage_backup_dir_size(self, max_backup_size_bytes):
        total_size = 0
        files = []
        
        for filename in os.listdir(self.backup_dir):
            filepath = os.path.join(self.backup_dir, filename)
            if os.path.isfile(filepath):
                total_size += os.path.getsize(filepath)
                files.append((filepath, os.path.getmtime(filepath)))

        files.sort(key=lambda x: x[1])  # Ordena por data de modificação (mais antigo primeiro)

        while total_size > max_backup_size_bytes and files:
            oldest_file = files.pop(0)
            total_size -= os.path.getsize(oldest_file[0])
            os.remove(oldest_file[0])

if __name__ == "__main__":
    root = tk.Tk()
    app = LogMonitorApp(root)
    root.mainloop()
