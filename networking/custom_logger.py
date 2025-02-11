import logging
import os
NOTICE_LEVEL = 25
logging.addLevelName(NOTICE_LEVEL, "NOTICE")

# Create a custom logger class
class MyLogger(logging.Logger):
    def notice(self, message, *args, **kwargs):
        if self.isEnabledFor(NOTICE_LEVEL):
            self._log(NOTICE_LEVEL, message, args, **kwargs)
def setup_logger(log_file_path, notes:str, overwrite = False,file_level:int = logging.INFO,stream_level:int=NOTICE_LEVEL,**func_kwargs)->MyLogger:
    logging.setLoggerClass(MyLogger)

    # Create the logger instance once
    logger:MyLogger = logging.getLogger(__name__) #type:ignore
    logger.setLevel(logging.INFO)
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.propagate = False

    # Stream handler for NOTICE and above (console)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(stream_level)
    stream_format = logging.Formatter('%(levelname)s - %(message)s')
    stream_handler.setFormatter(stream_format)

    # File handler for INFO and above (temp file)

    if not os.path.exists(log_file_path) or overwrite:
        os.makedirs(os.path.dirname(log_file_path),exist_ok=True)
        with open(log_file_path,'w') as f:
            f.write('')
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(file_level)
    file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)

    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.log(min(stream_level,file_level),"INITIATING NEW RUN -%s with parameters: %s",notes,func_kwargs)
    return logger