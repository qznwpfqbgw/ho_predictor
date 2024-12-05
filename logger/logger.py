import logging

NOTICE_LEVEL = 25
logging.addLevelName(NOTICE_LEVEL, "NOTICE")

class LogColors:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    BOLD_RED = "\033[1;31m"
    PURPLE = "\033[35m"

class ColoredFormatter(logging.Formatter):
    LEVEL_COLORS = {
        logging.DEBUG: LogColors.CYAN,
        logging.INFO: LogColors.GREEN,
        logging.WARNING: LogColors.YELLOW,
        logging.ERROR: LogColors.RED,
        logging.CRITICAL: LogColors.PURPLE,
        NOTICE_LEVEL: LogColors.BOLD_RED,
    }

    def format(self, record):
        log_color = self.LEVEL_COLORS.get(record.levelno, LogColors.RESET)
        message = super().format(record)
        return f"{log_color}{message}{LogColors.RESET}"
    
def notice_log(self, message, *args, **kwargs):
    if self.isEnabledFor(NOTICE_LEVEL):
        self._log(NOTICE_LEVEL, message, args, **kwargs)
        
logging.Logger.notice = notice_log
handler = logging.StreamHandler()
formatter = ColoredFormatter("%(levelname)s: %(message)s")
handler.setFormatter(formatter)

logger = logging.getLogger('colored_logger')
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

