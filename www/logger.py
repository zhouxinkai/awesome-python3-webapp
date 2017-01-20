# import logging; logging.basicConfig(level=logging.INFO, filename='server_info.log')
import logging  
import logging.handlers  
  
LOG_FILE = '../log/server_info.log'  
  
handler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes = 1024*1024) # 实例化handler    
fmt = '%(asctime)s - %(filename)s:%(lineno)s - %(name)s - %(message)s'  
  
formatter = logging.Formatter(fmt)   # 实例化formatter   
handler.setFormatter(formatter)      # 为handler添加formatter   
  
logger = logging.getLogger('server_info')    # 获取名为server_info的logger   
logger.addHandler(handler)           # 为logger添加handler   
logger.setLevel(logging.INFO)