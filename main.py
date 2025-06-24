import argparse
import random
import sys

import numpy as np

from deadlock_prevent_monitor import DeadlockPreventerMonitor
from logger import MatrixFileLogger, logger
from thread import WorkerThread

if __name__ == "__main__":
    RESOURCE_NAMES = ["CPU", "RAM", "Disk"]
    LOG_FILE_NAME = "deadlock_log.txt"

    parser = argparse.ArgumentParser(
        description="A monitor to control resources and prevent deadlocks in a multi-process simulation.",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument("-p", "--processes", type=int, required=True, help="The total number of processes to simulate.")

    parser.add_argument(
        "-r",
        "--resources",
        type=int,
        nargs="+",  # '+' means 1 or more arguments will be collected into a list
        required=True,
        help=f"A space-separated list of total available units for each resource.\n"
        f"Must provide {len(RESOURCE_NAMES)} values for: {' '.join(RESOURCE_NAMES)}",
    )

    args = parser.parse_args()

    NUM_PROCESSES = args.processes
    TOTAL_RESOURCES = args.resources

    if len(TOTAL_RESOURCES) != len(RESOURCE_NAMES):
        print(f"Error: Expected {len(RESOURCE_NAMES)} resource values, but got {len(TOTAL_RESOURCES)}.")
        print(f"Please provide values for: {' '.join(RESOURCE_NAMES)}")
        sys.exit(1)

    print("--- Simulation Configuration ---")
    print(f"Number of Processes: {NUM_PROCESSES}")
    print(f"Resource Names:      {RESOURCE_NAMES}")
    print(f"Total Resources:     {TOTAL_RESOURCES}")
    print(f"Log File:            {LOG_FILE_NAME}")
    print("------------------------------\n")

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
