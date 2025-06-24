import random

import numpy as np

from deadlock_prevent_monitor import DeadlockPreventerMonitor
from logger import MatrixFileLogger, logger
from thread import WorkerThread

if __name__ == "__main__":
    NUM_PROCESSES = 4
    RESOURCE_NAMES = ["CPU", "RAM", "Disk"]
    TOTAL_RESOURCES = [10, 7, 12]
    LOG_FILE_NAME = "deadlock_log.txt"

    file_logger = MatrixFileLogger(LOG_FILE_NAME, num_processes=NUM_PROCESSES, resource_names=RESOURCE_NAMES)

    monitor = DeadlockPreventerMonitor(TOTAL_RESOURCES, NUM_PROCESSES, matrix_logger=file_logger)

    threads = []
    for i in range(NUM_PROCESSES):
        max_claim = [random.randint(2, TOTAL_RESOURCES[j]) for j in range(len(TOTAL_RESOURCES))]
        thread = WorkerThread(i, monitor, max_claim)
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    print("\n" + "=" * 50)
    logger.system("Все потоки завершили свою работу.")
    logger.system(f"Подробный лог состояния сохранен в файле: {LOG_FILE_NAME}")
    logger.system(f"Итоговое состояние ресурсов: {monitor.available}")
    logger.system(f"Ожидаемое состояние:          {TOTAL_RESOURCES}")
    assert np.all(monitor.available == np.array(TOTAL_RESOURCES)), "Ошибка: не все ресурсы были возвращены!"
    logger.system("Проверка успешна: все ресурсы возвращены в систему.")
    print("=" * 50)

    file_logger.close()
