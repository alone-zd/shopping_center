from django.shortcuts import render, HttpResponse
from django.views import View
from django_redis import get_redis_connection
from verifications.libs.captcha.captcha import captcha
from django import http
from . import constants
# Create your views here.


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


