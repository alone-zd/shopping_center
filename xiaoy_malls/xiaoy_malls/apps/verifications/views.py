from django.shortcuts import render, HttpResponse
from django.views import View
from django_redis import get_redis_connection
from django import http
import random, logging

from . import constants
from xiaoy_malls.utils.response_code import RETCODE
from verifications.libs.captcha.captcha import captcha
from celery_tasks.sms.tasks import send_sms_code


logger = logging.getLogger("django")

class SmsCodeView(View):
    """短信验证码"""
    def get(self, request, mobile):
        image_code_client = request.GET.get("image_code")
        uuid = request.GET.get('uuid')

        if not all([image_code_client, uuid]):
            return http.HttpResponseForbidden('缺少必传参数')

        redis_conn = get_redis_connection('verify_code')
        # 判断用户是否频繁发送短信验证码
        send_flag = redis_conn.get('send_flag_%s' % mobile)
        if send_flag:
            return http.JsonResponse({'code': RETCODE.THROTTLINGERR, 'errmsg': '发送短信过于频繁'})
        
        # 提取图形验证码
        image_code_server = redis_conn.get('img_%s' % uuid)
        if image_code_server is None:
            return http.JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '图形验证码已失效'})
        redis_conn.delete('img_%s' % uuid)
        image_code_server = image_code_server.decode() # 将bytes转字符串进行比较
        if image_code_client.lower() != image_code_server.lower():
            return http.JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '输入图形验证码有误'})
        # 随机生成短信验证码（6位），不足6位前面补0
        sms_code = '%06d' % random.randint(0, 999999)
        logger.info(sms_code)
        # pipline向redis保存发送的短信验证码 和 验证码标记
        pl = redis_conn.pipeline()
        pl.setex('sms_%s' % mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
        pl.setex('send_flag_%s' % mobile, constants.SEND_SMS_CODE_INTERVAL, 1)
        pl.execute()

        # 发送验证码
        send_sms_code.delay(mobile, sms_code)

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '发送短信成功'})


class ImageCodeView(View):

    def get(self, request, uuid):
        """
        返回图形验证码图片，并在redis中保存验证码
        ：params uuid：唯一标识，当前验证码所属用户
        ：return image/jpg
        """
        text, image = captcha.generate_captcha()
        # 连接settings中配置的redis，用来保存图形验证码
        redis_conn = get_redis_connection('verify_code')
        redis_conn.setex("img_%s" % uuid, constants.IMAGE_CODE_REDIS_EXPIRES, text)

        return HttpResponse(image, content_type="image/jpg")
