# celery 入口
from celery import Celery


celery_app = Celery('xiaoy')

# 加载配置
celery_app.config_from_object('celery_tasks.config')

# 注册任务
celery_app.autodiscover_tasks(['celery_tasks.sms'])
