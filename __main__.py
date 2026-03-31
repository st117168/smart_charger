#!/usr/bin/env python3
import ctypes
import os
import sys
import json
import time
import logging
import signal
import socket
import threading
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

# ========== ОПРЕДЕЛЕНИЕ ПУТЕЙ ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')
LOG_FILE = os.path.join(DATA_DIR, 'smart-charger.log')

# Пути для виртуального окружения в зависимости от ОС
if sys.platform == 'win32':
    VENV_DIR = os.path.join(BASE_DIR, '.venv')
    VENV_PYTHON = os.path.join(VENV_DIR, 'Scripts', 'python.exe')
    VENV_PYTHONW = os.path.join(VENV_DIR, 'Scripts', 'pythonw.exe')
else:  # Linux/macOS
    VENV_DIR = os.path.join(BASE_DIR, '.venv')
    VENV_PYTHON = os.path.join(VENV_DIR, 'bin', 'python')
    VENV_PYTHONW = VENV_PYTHON


class SmartCharger:
    def __init__(self):
        self.setup_logging()
        self.config = self.load_config()
        self.device = None
        self.running = True
        self.shutdown_lock = threading.Lock()
        self.is_exiting = False

        self.setup_signal_handlers()

        # Импорты будут выполнены после настройки venv
        # Они вызываются в методе setup_imports()

    # --- Конфигурация и Логи ---
    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            template = {
                "tuya": {"device_id": "YOUR_DEVICE_ID", "local_key": "YOUR_LOCAL_KEY", "ip_address": "", "version": 3.5},
                "battery": {"min_level": 30, "max_level": 80, "check_interval": 60}
            }
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(template, f, indent=4)
            print(f"❌ Конфиг создан: {CONFIG_FILE}. Заполните его!")
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)

    def setup_logging(self):

        handlers=[logging.FileHandler(LOG_FILE, encoding='utf-8')]

        if sys.stdout.isatty() and 'JOURNAL_STREAM' not in os.environ:
            handlers.append(logging.StreamHandler())

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=handlers
        )
        self.logger = logging.getLogger(__name__)

    def setup_imports(self):
        """Импортирует модули после установки зависимостей"""
        global psutil, tinytuya

        import psutil
        import tinytuya

        self.psutil = psutil
        self.tinytuya = tinytuya

        if sys.platform == 'win32':
            try:
                import win32api
                import win32con
                import pythoncom
                import wmi
                self.win32api = win32api
                self.win32con = win32con
                self.pythoncom = pythoncom
                self.wmi = wmi
            except ImportError as e:
                self.logger.warning(f"Некоторые Windows-библиотеки не загружены: {e}")

    # --- Подготовка окружения ---
    def setup_venv(self):
        """Создает .venv и устанавливает зависимости для текущей ОС"""

        if not os.path.exists(VENV_DIR):
            self.logger.info("📦 Создаю виртуальное окружение .venv...")
            subprocess.run([sys.executable, "-m", "venv", VENV_DIR], check=True)

        self.logger.info("🛠 Установка зависимостей...")

        # Базовые зависимости для всех ОС
        deps = ["tinytuya", "psutil"]

        # Windows-специфичные зависимости
        if sys.platform == 'win32':
            deps.extend(["pywin32", "wmi"])

        # Обновляем pip и ставим пакеты
        subprocess.run([VENV_PYTHON, "-m", "pip", "install", "--upgrade", "pip"],
                      capture_output=True, check=False)

        for dep in deps:
            self.logger.info(f"  Устанавливаю {dep}...")
            result = subprocess.run([VENV_PYTHON, "-m", "pip", "install", dep],
                                   capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.error(f"  Ошибка установки {dep}: {result.stderr}")
            else:
                self.logger.info(f"  ✓ {dep} установлен")

        self.logger.info("✅ Зависимости установлены")
        return VENV_PYTHON

    # --- Автозапуск ---
    def set_autostart(self, enable=True):
        """Настройка автозапуска для текущей ОС"""

        if sys.platform == 'win32':
            return self._set_autostart_windows(enable)
        else:
            return self._set_autostart_linux(enable)

    def _set_autostart_windows(self, enable=True):
        """Настройка автозапуска на Windows"""

        task_name = "SmartChargerTask"
        script_path = os.path.abspath(sys.argv[0])

        if enable:
            try:
                venv_python = self.setup_venv()
                # Используем pythonw.exe для работы без консольного окна
                pythonw_exe = venv_python.replace("python.exe", "pythonw.exe")

                # Создаем задачу в Планировщике
                create_cmd = (
                    f'schtasks /create /tn "{task_name}" /tr "\'{pythonw_exe}\' \'{script_path}\'" '
                    f'/sc onstart /ru SYSTEM /rl highest /f'
                )

                # Настройка работы от батареи через PowerShell
                ps_fix = (
                    f'powershell -Command "Set-ScheduledTask -TaskName \'{task_name}\' '
                    f'-Settings (New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries)"'
                )

                subprocess.run(create_cmd, shell=True, check=True, capture_output=True)
                subprocess.run(ps_fix, shell=True, check=True, capture_output=True)

                self.logger.info(f"✅ Автозапуск настроен через планировщик задач")
                return True
            except Exception as e:
                self.logger.error(f"❌ Ошибка настройки автозапуска: {e}")
                return False
        else:
            subprocess.run(f'schtasks /delete /tn "{task_name}" /f', shell=True, capture_output=True)
            self.logger.info(f"🗑 Задача '{task_name}' удалена.")
            return True

    def _set_autostart_linux(self, enable=True):
        """Настройка автозапуска на Linux через systemd"""

        service_name = "smart-charger.service"
        service_dir = os.path.expanduser("~/.config/systemd/user")
        service_path = os.path.join(service_dir, service_name)
        script_path = os.path.abspath(sys.argv[0])

        if enable:
            try:
                # Сначала создаем venv и устанавливаем зависимости
                venv_python = self.setup_venv()

                # Создаем директорию для сервисов
                os.makedirs(service_dir, exist_ok=True)

                # Создаем systemd сервис
                service_content = f"""[Unit]
Description=Smart Charger Battery Monitor
After=network.target

[Service]
Type=simple
WorkingDirectory={BASE_DIR}
Environment="PATH={os.path.join(VENV_DIR, 'bin')}:/usr/local/bin:/usr/bin:/bin"
ExecStart={venv_python} {script_path}
Restart=on-failure
RestartSec=10
StandardOutput=append:{LOG_FILE}
StandardError=append:{LOG_FILE}

[Install]
WantedBy=default.target
"""
                with open(service_path, 'w') as f:
                    f.write(service_content)

                # Перезагружаем systemd и включаем сервис
                subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True, capture_output=True)
                subprocess.run(['systemctl', '--user', 'enable', service_name], check=True, capture_output=True)
                subprocess.run(['systemctl', '--user', 'start', service_name], check=True, capture_output=True)

                self.logger.info(f"✅ Автозапуск настроен через systemd")
                self.logger.info(f"   Сервис: {service_name}")
                self.logger.info(f"   Логи: journalctl --user -u {service_name} -f")
                return True

            except subprocess.CalledProcessError as e:
                self.logger.error(f"❌ Ошибка настройки автозапуска: {e}")
                self.logger.error(f"   Вывод: {e.stderr if hasattr(e, 'stderr') else 'N/A'}")
                return False
            except Exception as e:
                self.logger.error(f"❌ Ошибка: {e}")
                return False
        else:
            # Отключаем автозапуск
            try:
                subprocess.run(['systemctl', '--user', 'stop', service_name], capture_output=True)
                subprocess.run(['systemctl', '--user', 'disable', service_name], capture_output=True)
                if os.path.exists(service_path):
                    os.remove(service_path)
                subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True, capture_output=True)
                self.logger.info(f"🗑 Автозапуск отключен, сервис '{service_name}' удален.")
                return True
            except Exception as e:
                self.logger.error(f"❌ Ошибка отключения автозапуска: {e}")
                return False

    # --- Обработка завершения ---
    def setup_signal_handlers(self):
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, self.signal_handler)

    def signal_handler(self, signum, frame):
        self.stop_and_exit()

    def windows_ctrl_handler(self, ctrl_type):
        if sys.platform == 'win32' and hasattr(self, 'win32con'):
            if ctrl_type == self.win32con.CTRL_CLOSE_EVENT:
                self.emergency_shutdown()
                return False
        return False

    def setup_windows_power_monitor(self):
        if sys.platform != 'win32' or not hasattr(self, 'wmi'):
            return

        def monitor():
            try:
                self.pythoncom.CoInitialize()
                c = self.wmi.WMI()
                watcher = c.watch_for(notification_type="Instantiation", wmi_class="Win32_PowerManagementEvent")
                while self.running:
                    event = watcher()
                    if event.EventType == 4:  # Suspend
                        self.logger.info("🌙 Сон: экстренное выключение.")
                        self.emergency_shutdown()
                    elif event.EventType == 7:  # Resume
                        time.sleep(10)
                        self.connect_with_autodiscover()
            except:
                pass
        threading.Thread(target=monitor, daemon=True).start()

    def emergency_shutdown(self):
        with self.shutdown_lock:
            if self.device:
                try:
                    self.device.set_socketTimeout(2)
                    self.device.turn_off()
                    self.logger.info("🔌 Безопасное выключение выполнено.")
                except:
                    pass

    def stop_and_exit(self):
        if self.is_exiting:
            return
        self.is_exiting = True
        self.running = False
        self.emergency_shutdown()
        os._exit(0)

    # --- Сетевая логика ---
    def is_ip_reachable(self, ip):
        try:
            with socket.create_connection((ip, 6668), timeout=0.8):
                return True
        except:
            return False

    def discover_device(self):
        self.logger.info("🔍 Поиск розетки...")
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            network = '.'.join(local_ip.split('.')[:-1])

            def check_ip(ip):
                if self.is_ip_reachable(ip):
                    try:
                        d = self.tinytuya.OutletDevice(self.config['tuya']['device_id'], ip, self.config['tuya']['local_key'])
                        d.set_version(float(self.config['tuya'].get('version', 3.5)))
                        if 'dps' in d.status():
                            return ip
                    except:
                        pass
                return None

            with ThreadPoolExecutor(max_workers=50) as executor:
                futures = [executor.submit(check_ip, f"{network}.{i}") for i in range(1, 255)]
                for future in as_completed(futures):
                    res = future.result()
                    if res:
                        return res
        except:
            pass
        return None

    def connect_with_autodiscover(self):
        t_conf = self.config["tuya"]
        ip = t_conf.get("ip_address")

        if ip and self.is_ip_reachable(ip):
            self.device = self.tinytuya.OutletDevice(t_conf["device_id"], ip, t_conf["local_key"])
            self.device.set_version(float(t_conf.get("version", 3.5)))
            return True

        found_ip = self.discover_device()
        if found_ip:
            self.device = self.tinytuya.OutletDevice(t_conf["device_id"], found_ip, t_conf["local_key"])
            self.device.set_version(float(t_conf.get("version", 3.5)))
            self.config["tuya"]["ip_address"] = found_ip
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
            return True
        return False

    def set_outlet(self, state):
        # Защита от частых переключений (не чаще 1 раза в 30 секунд)
        current_time = time.time()
        if hasattr(self, 'last_toggle_time') and current_time - self.last_toggle_time < 30:
            return True
        
        if not self.device:
            if not self.connect_with_autodiscover():
                return False
        
        try:
            # Проверяем текущее состояние перед переключением
            try:
                status = self.device.status()
                current_state = status.get('dps', {}).get('1')
                if current_state == state:
                    return True
            except:
                # Если не удалось получить состояние, пробуем переключить
                pass
            
            if state:
                self.device.turn_on()
            else:
                self.device.turn_off()
            
            self.logger.info(f"🔌 Реле -> {'ВКЛ' if state else 'ВЫКЛ'}")
            
            # Ждем стабилизации после переключения
            time.sleep(2)
            
            return True
        except Exception as e:
            self.logger.error(f"Ошибка управления розеткой: {e}")
            self.device = None
            return False

    # --- Основной цикл ---
    def run(self):
        # Настраиваем импорты перед запуском
        self.setup_imports()

        # Настраиваем Windows-специфичные функции
        if sys.platform == 'win32' and hasattr(self, 'win32api'):
            try:
                self.setup_windows_power_monitor()
                self.win32api.SetConsoleCtrlHandler(self.windows_ctrl_handler, True)
            except:
                self.logger.warning("Не удалось настроить обработку событий Windows")

        bc = self.config["battery"]
        self.logger.info("🚀 Мониторинг запущен.")

        while self.running:
            try:
                battery = self.psutil.sensors_battery()
                if battery:
                    p, plugged = battery.percent, battery.power_plugged
                    self.logger.info(f"🔋 Заряд: {p}% | Питание: {plugged}")

                    if not plugged and p <= bc["min_level"]:
                        self.set_outlet(True)
                    elif plugged and p >= bc["max_level"]:
                        self.set_outlet(False)

                for _ in range(bc["check_interval"]):
                    if not self.running:
                        break
                    time.sleep(1)
            except Exception as e:
                self.logger.error(f"Ошибка цикла: {e}")
                time.sleep(10)


if __name__ == "__main__":
    # Проверка аргументов для настройки автозапуска
    if "--autostart" in sys.argv or "--no-autostart" in sys.argv:
        # Для Windows требуются права администратора
        if sys.platform == 'win32':
            try:
                is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            except:
                is_admin = False

            if not is_admin:
                print("Запрашиваю права администратора...")
                ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
                sys.exit(0)

        # Создаем экземпляр и настраиваем автозапуск
        app = SmartCharger()

        if "--autostart" in sys.argv:
            app.set_autostart(True)
        else:
            app.set_autostart(False)
        sys.exit(0)

    # Нормальный запуск
    app = SmartCharger()
    app.run()
