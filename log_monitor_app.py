import tkinter as tk
from tkinter import filedialog, messagebox
import os
import zipfile
import time
from PIL import Image
import threading

try:
    import pystray
    from pystray import MenuItem as PyMenuItem
    from pystray import Icon as PystrayIcon
except ImportError:
    messagebox.showerror("Erro", "A biblioteca pystray não está instalada. Instale usando 'pip install pystray'.")
    raise

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
        
        current_dir = os.path.dirname(__file__)
        self.icon_path = os.path.join(current_dir, "icon.png")

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
        self.start_button.grid(row=4, column=0, columnspan=3, padx=10, pady=10)

        self.stop_button = tk.Button(root, text="Parar", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_button.grid(row=5, column=0, columnspan=3, padx=10, pady=10)

        self.background_check = tk.Checkbutton(root, text="Executar em segundo plano", variable=self.background_mode)
        self.background_check.grid(row=6, column=0, columnspan=3, padx=10, pady=10)

        # Variáveis para controlar o temporizador de monitoramento
        self.monitor_timer = None

        # Configuração para controlar a estado de minimização
        self.root.protocol("WM_DELETE_WINDOW", self.on_close_window)
        self.root.protocol("WM_ICONIFY", self.on_minimize_window)
        self.root.protocol("WM_DEICONIFY", self.on_restore_window)

        # Inicializa a bandeja do sistema
        self.tray_icon = None
        self.tray_thread = None
        self.stop_tray_event = threading.Event()

    def select_log_file(self):
        self.log_file = filedialog.askopenfilename(initialdir=os.getcwd(), title="Selecionar Arquivo de Log")
        self.log_file_entry.delete(0, tk.END)
        self.log_file_entry.insert(0, self.log_file)

    def select_backup_dir(self):
        self.backup_dir = filedialog.askdirectory(initialdir=os.getcwd(), title="Selecionar Pasta de Backup")
        self.backup_dir_entry.delete(0, tk.END)
        self.backup_dir_entry.insert(0, self.backup_dir)

    def start_monitoring(self):
        if not self.log_file or not self.backup_dir:
            messagebox.showerror("Erro", "Selecione o arquivo de log e a pasta de backup.")
            return

        if not self.max_log_size.get() or not self.max_backup_size.get():
            messagebox.showerror("Erro", "Informe os tamanhos máximos para o log e a pasta de backup.")
            return

        if self.monitoring:
            messagebox.showinfo("Info", "Monitoramento já está em andamento.")
            return

        self.monitoring = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        if self.background_mode.get():
            self.hide_to_tray()  # Oculta a janela principal ao iniciar em segundo plano

        # Inicia o temporizador de monitoramento
        self.monitor_log_periodically()

    def stop_monitoring(self):
        self.monitoring = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        if self.background_mode.get():
            self.show_from_tray()

        # Cancela o temporizador, se estiver ativo
        if self.monitor_timer:
            self.root.after_cancel(self.monitor_timer)
            self.monitor_timer = None

    def monitor_log_periodically(self):
        if self.monitoring:
            self.monitor_log_file()
            self.monitor_timer = self.root.after(10000, self.monitor_log_periodically)  # Verificar a cada 10 segundos

    def monitor_log_file(self):
        max_log_size_bytes = self.convert_size_to_bytes(self.max_log_size.get(), self.unit.get())
        max_backup_size_bytes = self.convert_size_to_bytes(self.max_backup_size.get(), self.unit.get())

        if os.path.exists(self.log_file) and os.path.getsize(self.log_file) > max_log_size_bytes:
            self.zip_and_clear_log()
            print("Backup do log realizado.")

        self.manage_backup_dir_size(max_backup_size_bytes)
        print("Verificação de tamanho da pasta de backup realizada.")

    def zip_and_clear_log(self):
        timestamp = time.strftime("%Y%m%d%H%M%S")
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

    def hide_to_tray(self):
        self.root.withdraw()  # Oculta a janela principal do Tkinter

        icon = self.create_icon()
        menu = self.create_menu()

        self.tray_icon = PystrayIcon("Log Monitor", icon, menu=menu)
        self.stop_tray_event.clear()
        self.tray_thread = threading.Thread(target=self.run_tray_icon)
        self.tray_thread.start()

    def run_tray_icon(self):
        self.tray_icon.run()
        self.stop_tray_event.set()

    def show_from_tray(self):
        if self.tray_icon:
            self.tray_icon.stop()
            self.stop_tray_event.wait()  # Aguarda até que a thread do tray seja finalizada
            self.root.after(0, self.root.deiconify)  # Exibe novamente a janela principal do Tkinter

    def create_icon(self):
        try:
            icon = Image.open(self.icon_path)
            icon = icon.resize((16, 16))
            return icon
        except Exception as e:
            print(f"Erro ao carregar o ícone: {e}")
            return None

    def create_menu(self):
        menu = (PyMenuItem('Abrir', lambda: self.on_tray_icon_click()),
                PyMenuItem('Sair', lambda: self.on_tray_icon_close()))
        return menu

    def on_tray_icon_click(self):
        self.show_from_tray()

    def on_tray_icon_close(self):
        self.root.quit()

    def on_minimize_window(self):
        if self.background_mode.get():
            self.hide_to_tray()

    def on_restore_window(self):
        if self.background_mode.get():
            self.show_from_tray()

    def on_close_window(self):
        self.stop_monitoring()
        self.root.destroy()

    def convert_size_to_bytes(self, size, unit):
        multiplier = 1
        if unit == "Bytes":
            multiplier = 1
        elif unit == "Megabytes":
            multiplier = 1024 ** 2
        elif unit == "Gigabytes":
            multiplier = 1024 ** 3
        return size * multiplier

def main():
    root = tk.Tk()
    app = LogMonitorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
